# sensing/processing/llm_bridge.py
"""
LLM bridge: projects JEPA manifold states into language model space.
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForCausalLM
from .jepa_manifold import ManifoldState

class LLMBridge:
    """
    Projects latent manifold states into LLM embedding space.
    Follows the bridge's "reality grounding" pattern[reference:5].
    """
    
    def __init__(self, model_name: str = "distilgpt2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.llm = AutoModelForCausalLM.from_pretrained(model_name)
        self.llm.eval()
        for p in self.llm.parameters():
            p.requires_grad = False
        
        self.llm_dim = 768  # distilgpt2 hidden size
        self.projector = nn.Sequential(
            nn.Linear(2, 64),
            nn.ReLU(),
            nn.Linear(64, self.llm_dim)
        )
        self.optimizer = torch.optim.Adam(self.projector.parameters(), lr=0.01)
        self.training_pairs: List[Tuple[ManifoldState, str]] = []
    
    def add_training_pair(self, state: ManifoldState, description: str):
        """Accumulate (latent state, text description) pairs for alignment."""
        self.training_pairs.append((state, description))
    
    def train(self, epochs: int = 500):
        """Align latent states with text descriptions."""
        if len(self.training_pairs) < 2:
            return
        
        states = torch.tensor([p[0].u for p in self.training_pairs], dtype=torch.float32)
        texts = [p[1] for p in self.training_pairs]
        
        # Get LLM embeddings for texts
        target_embs = []
        for txt in texts:
            inputs = self.tokenizer(txt, return_tensors="pt", padding=True, truncation=True, max_length=32)
            with torch.no_grad():
                emb = self.llm.transformer.wte(inputs["input_ids"])
                target_embs.append(emb.mean(dim=1))
        target_embs = torch.cat(target_embs, dim=0)
        
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            projected = self.projector(states)
            loss = nn.functional.mse_loss(projected, target_embs)
            loss.backward()
            self.optimizer.step()
    
    def generate(self, state: ManifoldState, prompt: str, max_new_tokens: int = 40) -> str:
        """Generate text grounded in a latent manifold state."""
        device = next(self.llm.parameters()).device
        u_t = torch.tensor(state.u, dtype=torch.float32).unsqueeze(0).to(device)
        
        with torch.no_grad():
            llm_embed = self.projector(u_t)
            inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=True).to(device)
            base_embeds = self.llm.transformer.wte(inputs["input_ids"])
            base_embeds[:, 0, :] = llm_embed
            
            output = self.llm.generate(
                inputs_embeds=base_embeds,
                max_new_tokens=max_new_tokens,
                temperature=0.8,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        return self.tokenizer.decode(output[0], skip_special_tokens=True)
