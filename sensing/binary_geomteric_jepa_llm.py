#!/usr/bin/env python3
"""
binary_geometric_jepa_llm.py — Bridge Binary Data → Geometric Manifold → LLM

Template:
- Takes binary vectors (bitstrings) as input.
- Learns a continuous 2D latent manifold preserving binary similarity.
- Predicts future binary states in latent space (JEPA-style latent dynamics).
- Projects latent states into a frozen LLM embedding space to generate narratives.

To use your repo's data:
- Replace `load_binary_data()` with your data loader.
- Adjust `build_similarity_matrix()` to match your notion of geometric proximity.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt

from torch.func import vmap, jacrev
from transformers import AutoTokenizer, AutoModelForCausalLM


# ============================================================
# 0. UTILITIES
# ============================================================

def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int = 42):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ============================================================
# 1. DATA — REPLACE WITH YOUR REPO'S LOADER
# ============================================================

def load_binary_data(n_samples: int = 50, binary_dim: int = 24):
    """
    Synthetic demo: regime shift from random to ordered.
    Replace this with your actual repo data loader, e.g.:

        data = np.load("your_binary_data.npy")  # shape (N, D)
        assert data.dtype in (np.float32, np.int8, np.bool_)
        return np.asarray(data, dtype=np.float32)
    """
    set_seed(42)
    binary_data = []
    for i in range(n_samples):
        prob = 0.3 + 0.6 * (i / n_samples)  # goes from 0.3 to 0.9
        bits = np.random.binomial(1, prob, size=binary_dim)
        binary_data.append(bits)
    binary_data = np.array(binary_data, dtype=np.float32)  # (N, D)
    return binary_data


def build_similarity_matrix(binary_data: np.ndarray, temporal_smooth: float = 0.7):
    """
    Similarity based on normalized Hamming distance.
    You should replace/extend this to match your geometry (e.g. graph distances,
    domain-specific metric, causal adjacency, etc.).
    """
    N = binary_data.shape[0]
    similarity = torch.eye(N)
    for i in range(N):
        for j in range(N):
            if i == j:
                similarity[i, j] = 1.0
            else:
                hamming = (binary_data[i] != binary_data[j]).mean()
                similarity[i, j] = 1.0 - hamming  # 1 = identical, 0 = totally different

    # Optional temporal smoothing for adjacent states
    for i in range(N - 1):
        similarity[i, i + 1] = max(similarity[i, i + 1].item(), temporal_smooth)
        similarity[i + 1, i] = similarity[i, i + 1]
    return similarity


# ============================================================
# 2. JEPA MODULES
# ============================================================

class EntryEncoder(nn.Module):
    def __init__(self, input_dim, d=2, hidden=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.Tanh(),
            nn.Linear(hidden, d)
        )

    def forward(self, x):
        return self.net(x)


class InstrumentField(nn.Module):
    """
    Produces a local metric tensor on latent space.
    """
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 3)
        )

    def forward(self, u):
        raw = self.net(u)
        # Build lower-triangular 2x2 per point, then square to get PSD metric
        L = torch.zeros(u.shape[0], 2, 2, device=u.device)
        L[:, 0, 0] = raw[:, 0]
        L[:, 1, 0] = raw[:, 1]
        L[:, 1, 1] = raw[:, 2]
        I = L @ L.transpose(1, 2)
        I = I + 0.1 * torch.eye(2, device=u.device).unsqueeze(0)
        return I


class CalibrationField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1)
        )

    def forward(self, u):
        return self.net(u).squeeze(-1)


class UnknownField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1)
        )

    def forward(self, u):
        return F.softplus(self.net(u)).squeeze(-1)


class AttunementField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1)
        )

    def forward(self, u):
        return torch.sigmoid(self.net(u)).squeeze(-1)


class Predictor(nn.Module):
    """
    Latent dynamics: predicts u_{t+1} from (u_{t-1}, u_t).
    """
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2 * d, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, d)
        )

    def forward(self, u_prev, u_curr):
        return self.net(torch.cat([u_prev, u_curr], dim=-1))


# Optional: continuous manifold for curvature regularization
class ContinuousManifold(nn.Module):
    def __init__(self, d=2, D=3, hidden=10):
        super().__init__()
        self.embed = nn.Sequential(
            nn.Linear(d, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, D)
        )

    def forward(self, u):
        return self.embed(u)


# ============================================================
# 3. ENERGY TERMS
# ============================================================

def stress_loss(u, sim, instrument_field, attunement_field):
    """
    Stress: latent metric-induced distances should track similarity matrix.
    """
    I = instrument_field(u)
    ω = attunement_field(u)  # [N]
    I_soft = I * (1 - 0.5 * ω.unsqueeze(-1).unsqueeze(-1))
    I_avg = 0.5 * (I_soft.unsqueeze(1) + I_soft.unsqueeze(0))
    diff = u.unsqueeze(1) - u.unsqueeze(0)
    d = torch.sqrt(torch.einsum("...i,...ij,...j->...", diff, I_avg, diff) + 1e-8)
    return ((d - (1.0 - sim)) ** 2).mean()


def curvature_loss(manifold, u):
    """
    Approximate isometry: singular values of Jacobian near 1.
    """
    J = vmap(jacrev(manifold))(u)          # [N, D, d]
    _, S, _ = torch.linalg.svd(J)          # singular values per sample
    return ((S - 1.0) ** 2).mean()


def calibration_smoothness(cal_field, u):
    """
    Spatial smoothness of calibration field.
    """
    u.requires_grad_(True)
    mu = cal_field(u)
    grad = torch.autograd.grad(mu.sum(), u, create_graph=True)[0]
    return (grad ** 2).sum(-1).mean()


def unknown_reg(unknown_field, u):
    """
    Keeps unknown field bounded / encourages non-trivial mass.
    """
    return unknown_field(u).mean()


def attunement_coherence(attunement_field, unknown_field, u):
    """
    Align attunement (0-1) with normalized unknown mass.
    """
    ω = attunement_field(u)
    unk = unknown_field(u)
    unk_norm = unk / (unk.max() + 1e-6)
    return ((ω - unk_norm) ** 2).mean()


def prediction_loss(predictor, u):
    """
    Latent dynamics consistency: predictor(u_{t-1}, u_t) ~ u_{t+1}.
    """
    if u.shape[0] < 3:
        return torch.tensor(0.0, device=u.device)
    u_prev = u[:-2]
    u_curr = u[1:-1]
    u_target = u[2:].detach()
    u_hat = predictor(u_prev, u_curr)
    return F.mse_loss(u_hat, u_target)


# ============================================================
# 4. TRAIN LATENT MANIFOLD
# ============================================================

def train_latent_geometry(X, similarity, num_epochs=4000, lr=0.02, device=None):
    device = device or get_device()

    encoder = EntryEncoder(X.shape[-1]).to(device)
    manifold = ContinuousManifold().to(device)
    instr_field = InstrumentField().to(device)
    cal_field = CalibrationField().to(device)
    unk_field = UnknownField().to(device)
    attunement_field = AttunementField().to(device)
    predictor = Predictor().to(device)

    params = (
        list(encoder.parameters()) +
        list(manifold.parameters()) +
        list(instr_field.parameters()) +
        list(cal_field.parameters()) +
        list(unk_field.parameters()) +
        list(attunement_field.parameters()) +
        list(predictor.parameters())
    )

    opt = torch.optim.Adam(params, lr=lr)

    X = X.to(device)
    similarity = similarity.to(device)

    for epoch in range(num_epochs):
        opt.zero_grad()
        u = encoder(X)

        loss = 0.0
        loss = loss + 1.0 * stress_loss(u, similarity, instr_field, attunement_field)
        loss = loss + 0.02 * curvature_loss(manifold, u)
        loss = loss + 0.1 * calibration_smoothness(cal_field, u)
        loss = loss + 0.2 * unknown_reg(unk_field, u)
        loss = loss + 0.15 * attunement_coherence(attunement_field, unk_field, u)
        loss = loss + 0.5 * prediction_loss(predictor, u)

        loss.backward()
        opt.step()

        if epoch % 1000 == 0:
            print(f"[Geometry] Epoch {epoch:4d}  Loss {loss.item():.4f}")

    with torch.no_grad():
        u_final = encoder(X)
        ω_final = attunement_field(u_final).cpu().numpy()
        unk_final = unk_field(u_final).cpu().numpy()

    return {
        "encoder": encoder,
        "manifold": manifold,
        "instr_field": instr_field,
        "cal_field": cal_field,
        "unk_field": unk_field,
        "attunement_field": attunement_field,
        "predictor": predictor,
        "u_final": u_final.detach(),
        "ω_final": ω_final,
        "unk_final": unk_final,
    }


# ============================================================
# 5. BRIDGE TO LLM (PROJECTOR)
# ============================================================

class Projector(nn.Module):
    def __init__(self, d=2, out_dim=768):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 64),
            nn.ReLU(),
            nn.Linear(64, out_dim)
        )

    def forward(self, u):
        return self.net(u)


def build_descriptions(binary_data: np.ndarray):
    """
    Turn binary patterns into simple textual descriptions to align latent
    geometry with natural language embedding space.
    """
    texts = []
    for i, bits in enumerate(binary_data):
        p = bits.mean()
        entropy = float(
            - (p * np.log(p + 1e-6) + (1 - p) * np.log(1 - p + 1e-6))
        )
        ones = int(bits.sum())
        regime = "ordered" if entropy < 0.3 else "chaotic"
        texts.append(
            f"State {i}: binary pattern has {ones} ones, entropy {entropy:.2f}. "
            f"The geometric configuration is {regime}."
        )
    return texts


def train_projector(u_final, binary_data, llm, tokenizer, num_epochs=1500, lr=0.01, device=None):
    device = device or get_device()
    llm_dim = llm.transformer.wte.weight.shape[-1]

    projector = Projector(d=u_final.shape[-1], out_dim=llm_dim).to(device)
    proj_opt = torch.optim.Adam(projector.parameters(), lr=lr)

    texts = build_descriptions(binary_data)
    target_embs = []

    with torch.no_grad():
        for txt in texts:
            inputs = tokenizer(
                txt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=32,
            ).to(device)
            emb = llm.transformer.wte(inputs["input_ids"])
            avg_emb = emb.mean(dim=1)
            target_embs.append(avg_emb)

    target_embs = torch.cat(target_embs, dim=0)  # [N, d_llm]

    u_final = u_final.to(device)

    for epoch in range(num_epochs):
        proj_opt.zero_grad()
        projected = projector(u_final)  # [N, d_llm]
        loss = F.mse_loss(projected, target_embs)
        loss.backward()
        proj_opt.step()
        if epoch % 500 == 0:
            print(f"[Projector] Epoch {epoch:4d}  MSE {loss.item():.4f}")

    return projector


def load_frozen_llm(model_name: str = "distilgpt2"):
    print(f"\nLoading LLM ({model_name})…")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    llm = AutoModelForCausalLM.from_pretrained(model_name)
    llm.eval()
    for p in llm.parameters():
        p.requires_grad = False
    llm.to(get_device())
    return llm, tokenizer


# ============================================================
# 6. PREDICT NEXT STATE & GENERATE TEXT
# ============================================================

def generate_future_narrative(u_final, predictor, projector, llm, tokenizer, prompt=None, device=None):
    device = device or get_device()
    u_final = u_final.to(device)
    predictor = predictor.to(device)
    projector = projector.to(device)

    if prompt is None:
        prompt = "The next binary state will evolve into a geometric configuration that is"

    with torch.no_grad():
        if u_final.shape[0] < 2:
            raise ValueError("Need at least 2 latent states to predict the next one.")

        u_prev = u_final[-2].unsqueeze(0)  # [1, d]
        u_curr = u_final[-1].unsqueeze(0)  # [1, d]
        u_next_hat = predictor(u_prev, u_curr)  # [1, d]
        llm_embed = projector(u_next_hat)       # [1, d_llm]

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            add_special_tokens=True,
        ).to(device)

        base_embeds = llm.transformer.wte(inputs["input_ids"])
        # Inject latent geometry into the first token embedding
        base_embeds[:, 0, :] = llm_embed

        output = llm.generate(
            inputs_embeds=base_embeds,
            max_new_tokens=40,
            temperature=0.8,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

        text = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"\n--- Prophetic Binary-to-Geometry Demo ---")
        print(f"Prompt: '{prompt}'\n")
        print(f"LLM completes:\n{text}")

        return u_next_hat.cpu(), text


# ============================================================
# 7. VISUALISE GEOMETRIC MANIFOLD
# ============================================================

def visualize(u_final, u_next_hat, ω_final, unk_final, save_path="binary_geometric_manifold.png"):
    u_np = u_final.cpu().numpy()
    u_next_np = u_next_hat.cpu().numpy()

    N = u_np.shape[0]

    plt.figure(figsize=(12, 5))

    ax1 = plt.subplot(121)
    sc = ax1.scatter(
        u_np[:, 0], u_np[:, 1],
        c=ω_final, cmap="viridis",
        s=100, edgecolors="black"
    )
    for i in range(N):
        ax1.annotate(
            str(i),
            (u_np[i, 0], u_np[i, 1]),
            fontsize=8,
            xytext=(3, 3),
            textcoords="offset points",
        )
    ax1.plot(u_np[:, 0], u_np[:, 1], "k--", alpha=0.3)
    ax1.scatter(
        u_next_np[0, 0],
        u_next_np[0, 1],
        color="red",
        s=200,
        marker="*",
        label="Predicted Next",
    )
    ax1.set_title("Geometric Manifold of Binary States\nColor = Attunement ω")
    plt.colorbar(sc, ax=ax1)
    ax1.legend()

    ax2 = plt.subplot(122)
    ax2.bar(range(N), unk_final, color="gray", alpha=0.6)
    ax2.axvline(N, color="red", linestyle="--", label="Predicted step")
    ax2.set_title("Unknown Field κ_unk (per state)")
    ax2.set_xlabel("State index")
    ax2.set_ylabel("Unknown density")
    ax2.legend()

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()

    print(f"\nSaved manifold figure to: {os.path.abspath(save_path)}")


# ============================================================
# 8. MAIN ENTRY POINT
# ============================================================

def main():
    device = get_device()
    print(f"Using device: {device}")

    # 1. Load/construct data
    binary_data = load_binary_data(n_samples=50, binary_dim=24)
    X = torch.tensor(binary_data, dtype=torch.float32)
    similarity = build_similarity_matrix(binary_data)

    # 2. Train latent geometry
    geo = train_latent_geometry(X, similarity, num_epochs=4000, lr=0.02, device=device)
    u_final = geo["u_final"]
    ω_final = geo["ω_final"]
    unk_final = geo["unk_final"]
    predictor = geo["predictor"]

    # 3. Load frozen LLM + train projector
    llm, tokenizer = load_frozen_llm("distilgpt2")
    projector = train_projector(u_final, binary_data, llm, tokenizer, num_epochs=1500, lr=0.01, device=device)

    # 4. Predict next latent state & generate text
    u_next_hat, _ = generate_future_narrative(u_final, predictor, projector, llm, tokenizer, device=device)

    # 5. Visualize geometry + unknown field
    visualize(u_final, u_next_hat, ω_final, unk_final)


if __name__ == "__main__":
    main()
