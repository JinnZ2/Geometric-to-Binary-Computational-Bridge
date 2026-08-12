#!/usr/bin/env python3
"""
binary_geometric_jepa_llm.py — Bridge Binary Data → Geometric Manifold → LLM

A template for your binary-to-geometric repo.
- Takes binary vectors (e.g., bitstrings) as input.
- Learns a continuous 2D manifold preserving binary structure.
- Predicts future binary states in latent space (JEPA).
- Projects latent states into a frozen LLM to generate narratives.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from torch.func import vmap, jacrev
from transformers import AutoTokenizer, AutoModelForCausalLM

# ============================================================
# 1. DATA — REPLACE THIS WITH YOUR REPO'S DATA LOADER
# ============================================================
# Example: synthetic binary sequences that evolve over time
# (like a phase transition in a spin system)
np.random.seed(42)
n_samples = 50                # number of binary states (e.g., time steps)
binary_dim = 24               # length of each binary vector

# Simulate a regime shift: first half random, second half highly ordered
binary_data = []
for i in range(n_samples):
    prob = 0.3 + 0.6 * (i / n_samples)  # goes from 0.3 to 0.9
    bits = np.random.binomial(1, prob, size=binary_dim)
    binary_data.append(bits)
binary_data = np.array(binary_data, dtype=np.float32)  # (50, 24)

# --- IMPORTANT: Your repo likely loads something like ---
# binary_data = np.load("your_binary_data.npy")  # shape (N, D)
# -----------------------------------------------------------

# Normalize? Binary data is already 0/1, but we can keep it as is.
X = torch.tensor(binary_data, dtype=torch.float32)
N, input_dim = X.shape

# Similarity matrix based on Hamming distance (geometric proximity)
similarity = torch.eye(N)
for i in range(N):
    for j in range(N):
        if i == j:
            similarity[i, j] = 1.0
        else:
            # Hamming distance normalized to [0,1]
            hamming = (binary_data[i] != binary_data[j]).mean()
            similarity[i, j] = 1.0 - hamming  # 1 = identical, 0 = totally different

# (Optional) enforce temporal smoothness for adjacent states
for i in range(N-1):
    similarity[i, i+1] = max(similarity[i, i+1], 0.7)
    similarity[i+1, i] = similarity[i, i+1]

# ============================================================
# 2. JEPA MODULES (same architecture as before)
# ============================================================
class EntryEncoder(nn.Module):
    def __init__(self, input_dim, d=2, hidden=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.Tanh(),
            nn.Linear(hidden, d)
        )
    def forward(self, x): return self.net(x)

class ContinuousManifold(nn.Module):
    def __init__(self, d=2, D=3, hidden=10):
        super().__init__()
        self.embed = nn.Sequential(
            nn.Linear(d, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, D)
        )
    def forward(self, u): return self.embed(u)

class Hypernetwork(nn.Module):
    def __init__(self, d_entry=2, child_d=2, child_hidden=5, child_D=3):
        super().__init__()
        self.child_d=child_d; self.child_hidden=child_hidden; self.child_D=child_D
        n = child_d*child_hidden + child_hidden + child_hidden*child_D + child_D
        self.fc = nn.Sequential(nn.Linear(d_entry, 16), nn.Tanh(), nn.Linear(16, n))
    def forward(self, u_entry):
        B=u_entry.shape[0]; params=self.fc(u_entry); children=[]
        for i in range(B):
            p=params[i]; idx=0
            W1=p[idx:idx+self.child_d*self.child_hidden].reshape(self.child_d, self.child_hidden); idx+=self.child_d*self.child_hidden
            b1=p[idx:idx+self.child_hidden]; idx+=self.child_hidden
            W2=p[idx:idx+self.child_hidden*self.child_D].reshape(self.child_hidden, self.child_D); idx+=self.child_hidden*self.child_D
            b2=p[idx:idx+self.child_D]
            child=nn.Sequential(nn.Linear(self.child_d, self.child_hidden), nn.Tanh(), nn.Linear(self.child_hidden, self.child_D))
            child[0].weight.data=W1.clone(); child[0].bias.data=b1.clone()
            child[2].weight.data=W2.clone(); child[2].bias.data=b2.clone()
            children.append(child)
        return children

class InstrumentField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, hidden), nn.Tanh(), nn.Linear(hidden, 3))
    def forward(self, u):
        raw=self.net(u); L=torch.zeros(u.shape[0],2,2,device=u.device)
        L[:,0,0]=raw[:,0]; L[:,1,0]=raw[:,1]; L[:,1,1]=raw[:,2]
        return L @ L.transpose(1,2) + 0.1 * torch.eye(2, device=u.device).unsqueeze(0)

class CalibrationField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, hidden), nn.Tanh(), nn.Linear(hidden, 1))
    def forward(self, u): return self.net(u).squeeze(-1)

class UnknownField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, hidden), nn.Tanh(), nn.Linear(hidden, 1))
    def forward(self, u): return F.softplus(self.net(u)).squeeze(-1)

class AttunementField(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, hidden), nn.Tanh(), nn.Linear(hidden, 1))
    def forward(self, u): return torch.sigmoid(self.net(u)).squeeze(-1)

class Predictor(nn.Module):
    def __init__(self, d=2, hidden=12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2*d, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, d)
        )
    def forward(self, u_prev, u_curr):
        return self.net(torch.cat([u_prev, u_curr], dim=1))

# ============================================================
# 3. ENERGY TERMS (same as Earth Mandala)
# ============================================================
def stress_loss(u, sim, instrument_field, attunement_field):
    I = instrument_field(u); ω = attunement_field(u)
    I_soft = I * (1 - 0.5 * ω.unsqueeze(-1).unsqueeze(-1))
    I_avg = 0.5 * (I_soft.unsqueeze(1) + I_soft.unsqueeze(0))
    diff = u.unsqueeze(1) - u.unsqueeze(0)
    d = torch.sqrt(torch.einsum('...i,...ij,...j->...', diff, I_avg, diff) + 1e-8)
    return ((d - (1.0 - sim))**2).mean()

def curvature_loss(manifold, u):
    J = vmap(jacrev(manifold))(u); _, S, _ = torch.linalg.svd(J)
    return ((S - 1.0)**2).mean()

def calibration_smoothness(cal_field, u):
    u.requires_grad_(True); mu = cal_field(u)
    grad = torch.autograd.grad(mu.sum(), u, create_graph=True)[0]
    return (grad**2).sum(1).mean()

def unknown_reg(unknown_field, u):
    return unknown_field(u).mean()

def attunement_coherence(attunement_field, unknown_field, u):
    ω = attunement_field(u); unk = unknown_field(u)
    return ((ω - unk / (unk.max()+1e-6))**2).mean()

def prediction_loss(predictor, u):
    if u.shape[0] < 3: return torch.tensor(0.0, device=u.device)
    u_hat = predictor(u[:-2], u[1:-1])
    return F.mse_loss(u_hat, u[2:].detach())

# ============================================================
# 4. BUILD & TRAIN
# ============================================================
encoder = EntryEncoder(input_dim)
manifold = ContinuousManifold()
hypernet = Hypernetwork()
instr_field = InstrumentField()
cal_field = CalibrationField()
unk_field = UnknownField()
attunement_field = AttunementField()
predictor = Predictor()

params = (list(encoder.parameters()) + list(manifold.parameters()) +
          list(hypernet.parameters()) + list(instr_field.parameters()) +
          list(cal_field.parameters()) + list(unk_field.parameters()) +
          list(attunement_field.parameters()) + list(predictor.parameters()))
opt = torch.optim.Adam(params, lr=0.02)

for epoch in range(4000):
    opt.zero_grad()
    u = encoder(X)
    loss = 0.0
    loss += 1.0 * stress_loss(u, similarity, instr_field, attunement_field)
    loss += 0.02 * curvature_loss(manifold, u)
    loss += 0.1 * calibration_smoothness(cal_field, u)
    loss += 0.2 * unknown_reg(unk_field, u)
    loss += 0.15 * attunement_coherence(attunement_field, unk_field, u)
    loss += 0.5 * prediction_loss(predictor, u)
    loss.backward(); opt.step()
    if epoch % 1000 == 0:
        print(f"Epoch {epoch:4d}  Loss {loss.item():.4f}")

u_final = encoder(X).detach()
ω_final = attunement_field(u_final).detach().numpy()
unk_final = unk_field(u_final).detach().numpy()

# ============================================================
# 5. BRIDGE TO LLM (PROJECTOR)
# ============================================================
print("\nLoading LLM (distilgpt2)…")
tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
tokenizer.pad_token = tokenizer.eos_token
llm = AutoModelForCausalLM.from_pretrained("distilgpt2")
llm.eval()
for p in llm.parameters(): p.requires_grad = False

llm_dim = 768
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
llm.to(device); u_final = u_final.to(device)

class Projector(nn.Module):
    def __init__(self, d=2, out_dim=llm_dim):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, 64), nn.ReLU(), nn.Linear(64, out_dim))
    def forward(self, u): return self.net(u)

projector = Projector().to(device)
proj_opt = torch.optim.Adam(projector.parameters(), lr=0.01)

# Generate synthetic descriptions based on binary properties
texts = []
for i, bits in enumerate(binary_data):
    entropy = - (bits.mean() * np.log(bits.mean()+1e-6) + (1-bits.mean())*np.log(1-bits.mean()+1e-6))
    ones = bits.sum()
    texts.append(
        f"State {i}: binary pattern has {ones} ones, entropy {entropy:.2f}. "
        f"The geometric configuration is { 'ordered' if entropy < 0.3 else 'chaotic' }."
    )

# Get target embeddings
target_embs = []
for txt in texts:
    inputs = tokenizer(txt, return_tensors="pt", padding=True, truncation=True, max_length=32)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        emb = llm.transformer.wte(inputs["input_ids"])
        avg_emb = emb.mean(dim=1)
        target_embs.append(avg_emb)
target_embs = torch.cat(target_embs, dim=0)

for epoch in range(1500):
    proj_opt.zero_grad()
    projected = projector(u_final)
    loss = F.mse_loss(projected, target_embs)
    loss.backward(); proj_opt.step()
    if epoch % 500 == 0:
        print(f"  Proj Epoch {epoch:4d}  MSE {loss.item():.4f}")

# ============================================================
# 6. PREDICT NEXT BINARY STATE (in latent space) & GENERATE
# ============================================================
print("\n--- Prophetic Binary-to-Geometry Demo ---")
with torch.no_grad():
    # Predict the next latent state (e.g., state N+1)
    u_next_hat = predictor(u_final[-2], u_final[-1]).unsqueeze(0)  # (1,2)
    llm_embed = projector(u_next_hat)

    prompt = "The next binary state will evolve into a geometric configuration that is"
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=True).to(device)
    base_embeds = llm.transformer.wte(inputs["input_ids"])
    base_embeds[:, 0, :] = llm_embed  # inject latent geometry

    output = llm.generate(
        inputs_embeds=base_embeds,
        max_new_tokens=40,
        temperature=0.8,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id
    )
    print(f"Prompt: '{prompt}'\n")
    print(f"LLM completes:\n{tokenizer.decode(output[0], skip_special_tokens=True)}")

# ============================================================
# 7. VISUALISE THE GEOMETRIC MANIFOLD
# ============================================================
u_np = u_final.cpu().numpy()
u_next_np = u_next_hat.cpu().numpy()

plt.figure(figsize=(12,5))

ax1 = plt.subplot(121)
sc = ax1.scatter(u_np[:,0], u_np[:,1], c=ω_final, cmap='viridis', s=100, edgecolors='black')
for i in range(N):
    ax1.annotate(str(i), (u_np[i,0], u_np[i,1]), fontsize=8, xytext=(3,3), textcoords='offset points')
ax1.plot(u_np[:,0], u_np[:,1], 'k--', alpha=0.3)
ax1.scatter(u_next_np[0,0], u_next_np[0,1], color='red', s=200, marker='*', label='Predicted Next')
ax1.set_title("Geometric Manifold of Binary States\nColor = Attunement ω")
plt.colorbar(sc, ax=ax1)
ax1.legend()

ax2 = plt.subplot(122)
ax2.bar(range(N), unk_final, color='gray', alpha=0.6)
ax2.axvline(N, color='red', linestyle='--', label='Predicted step')
ax2.set_title("Unknown Field κ_unk (per state)")
ax2.set_xlabel("State index"); ax2.set_ylabel("Unknown density")
ax2.legend()

plt.tight_layout()
plt.savefig('binary_geometric_manifold.png', dpi=150)
plt.show()

print("\nBridge complete. Your binary data now flows through a geometric JEPA manifold into an LLM.")
print("To use YOUR repo data: replace the synthetic binary_data generation (lines 30-40)")
print("and adjust the similarity metric (lines 43-50) to match your geometry.")
