"""
GuardLocker - Transformer-Based Vault Model
Based on USENIX Security 2025 research

This module implements the decoder-only Transformer model for
password vault distribution modeling.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Optional
import math


class PositionalEncoding(nn.Module):
    """Positional encoding for sequence position information"""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        return x + self.pe[:x.size(0)]


class VaultTransformer(nn.Module):
    """
    Decoder-only Transformer for password vault modeling
    
    Architecture:
    - Hidden dimension: 768
    - 12 Transformer layers
    - 12 attention heads
    - ~85M parameters
    """
    
    def __init__(
        self,
        vocab_size: int = 98,  # 95 ASCII + special tokens
        d_model: int = 768,
        nhead: int = 12,
        num_layers: int = 12,
        dim_feedforward: int = 3072,  # 4 * d_model
        dropout: float = 0.1,
        max_seq_length: int = 1000
    ):
        super().__init__()
        
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.max_seq_length = max_seq_length
        
        # Token embedding
        self.embedding = nn.Embedding(vocab_size, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, max_seq_length)
        
        # Transformer decoder layers
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_decoder = nn.TransformerDecoder(
            decoder_layer,
            num_layers=num_layers
        )
        
        # Output projection
        self.fc_out = nn.Linear(d_model, vocab_size)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights with Xavier/Glorot initialization"""
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)
    
    def generate_square_subsequent_mask(self, sz: int) -> torch.Tensor:
        """Generate causal mask for autoregressive generation"""
        mask = torch.triu(torch.ones(sz, sz), diagonal=1)
        mask = mask.masked_fill(mask == 1, float('-inf'))
        return mask
    
    def forward(
        self,
        src: torch.Tensor,
        src_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            src: Input tensor [batch_size, seq_len]
            src_mask: Attention mask
        
        Returns:
            Logits tensor [batch_size, seq_len, vocab_size]
        """
        # Embed tokens
        src = self.embedding(src) * math.sqrt(self.d_model)
        
        # Add positional encoding
        src = self.pos_encoder(src)
        
        # Generate causal mask if not provided
        if src_mask is None:
            src_mask = self.generate_square_subsequent_mask(src.size(1)).to(src.device)
        
        # Pass through transformer
        # For decoder-only, we use the same input as both src and tgt
        output = self.transformer_decoder(src, src, tgt_mask=src_mask)
        
        # Project to vocabulary
        logits = self.fc_out(output)
        
        return logits
    
    def predict_next_char(
        self,
        context: str,
        tokenizer: 'VaultTokenizer',
        temperature: float = 1.0
    ) -> torch.Tensor:
        """
        Predict probability distribution for next character
        
        Args:
            context: Current context string
            tokenizer: Tokenizer instance
            temperature: Sampling temperature
        
        Returns:
            Probability distribution over vocabulary
        """
        self.eval()
        
        with torch.no_grad():
            # Tokenize context
            tokens = tokenizer.encode(context)
            tokens = torch.tensor([tokens], dtype=torch.long)
            
            # Get logits
            logits = self.forward(tokens)
            
            # Get last position logits
            next_char_logits = logits[0, -1, :] / temperature
            
            # Apply softmax
            probs = F.softmax(next_char_logits, dim=-1)
            
            return probs
    
    def generate_password(
        self,
        context: str,
        tokenizer: 'VaultTokenizer',
        max_length: int = 25,
        temperature: float = 1.0,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None
    ) -> str:
        """
        Generate a password given context
        
        Args:
            context: Current vault context
            tokenizer: Tokenizer instance
            max_length: Maximum password length
            temperature: Sampling temperature
            top_k: Top-k sampling parameter
            top_p: Nucleus sampling parameter
        
        Returns:
            Generated password string
        """
        self.eval()
        
        generated = ""
        current_context = context
        
        for _ in range(max_length):
            # Get next character probabilities
            probs = self.predict_next_char(current_context, tokenizer, temperature)
            
            # Apply sampling strategies
            if top_k is not None:
                probs = self._top_k_filtering(probs, top_k)
            
            if top_p is not None:
                probs = self._nucleus_filtering(probs, top_p)
            
            # Sample next character
            next_token_id = torch.multinomial(probs, 1).item()
            next_char = tokenizer.decode([next_token_id])
            
            # Stop at separator or max length
            if next_char == '<SEP>':
                break
            
            generated += next_char
            current_context += next_char
        
        return generated
    
    def _top_k_filtering(self, probs: torch.Tensor, k: int) -> torch.Tensor:
        """Apply top-k sampling"""
        top_k_probs, top_k_indices = torch.topk(probs, k)
        probs_filtered = torch.zeros_like(probs)
        probs_filtered.scatter_(0, top_k_indices, top_k_probs)
        probs_filtered = probs_filtered / probs_filtered.sum()
        return probs_filtered
    
    def _nucleus_filtering(self, probs: torch.Tensor, p: float) -> torch.Tensor:
        """Apply nucleus (top-p) sampling"""
        sorted_probs, sorted_indices = torch.sort(probs, descending=True)
        cumulative_probs = torch.cumsum(sorted_probs, dim=0)
        
        # Remove tokens with cumulative probability above threshold
        sorted_indices_to_remove = cumulative_probs > p
        sorted_indices_to_remove[1:] = sorted_indices_to_remove[:-1].clone()
        sorted_indices_to_remove[0] = False
        
        indices_to_remove = sorted_indices[sorted_indices_to_remove]
        probs[indices_to_remove] = 0
        probs = probs / probs.sum()
        
        return probs
    
    def calculate_vault_probability(
        self,
        vault: List[str],
        tokenizer: 'VaultTokenizer'
    ) -> float:
        """
        Calculate probability of a vault
        
        Args:
            vault: List of passwords
            tokenizer: Tokenizer instance
        
        Returns:
            Log probability of the vault
        """
        self.eval()
        
        context = '<SEP>'
        total_log_prob = 0.0
        
        with torch.no_grad():
            for password in vault:
                for char in password:
                    # Get probability distribution
                    probs = self.predict_next_char(context, tokenizer)
                    
                    # Get probability of actual character
                    char_id = tokenizer.char_to_id(char)
                    char_prob = probs[char_id].item()
                    
                    # Add to log probability
                    total_log_prob += math.log(char_prob + 1e-10)
                    
                    context += char
                
                # Add separator
                context += '<SEP>'
                sep_id = tokenizer.char_to_id('<SEP>')
                sep_prob = self.predict_next_char(context[:-5], tokenizer)[sep_id].item()
                total_log_prob += math.log(sep_prob + 1e-10)
        
        return total_log_prob


class VaultTokenizer:
    """Tokenizer for password vaults"""
    
    def __init__(self):
        # 95 printable ASCII characters (32-126)
        self.chars = [chr(i) for i in range(32, 127)]
        
        # Special tokens
        self.special_tokens = ['<SEP>', '<PAD>', '<UNK>']
        
        # Build vocabulary
        self.vocab = self.special_tokens + self.chars
        self.vocab_size = len(self.vocab)
        
        # Create mappings
        self.char_to_idx = {char: idx for idx, char in enumerate(self.vocab)}
        self.idx_to_char = {idx: char for char, idx in self.char_to_idx.items()}
    
    def char_to_id(self, char: str) -> int:
        """Convert character to token ID"""
        return self.char_to_idx.get(char, self.char_to_idx['<UNK>'])
    
    def id_to_char(self, idx: int) -> str:
        """Convert token ID to character"""
        return self.idx_to_char.get(idx, '<UNK>')
    
    def encode(self, text: str) -> List[int]:
        """Encode text to token IDs"""
        return [self.char_to_id(char) for char in text]
    
    def decode(self, token_ids: List[int]) -> str:
        """Decode token IDs to text"""
        return ''.join([self.id_to_char(idx) for idx in token_ids])
    
    def encode_vault(self, passwords: List[str]) -> List[int]:
        """Encode a vault (list of passwords) to token IDs"""
        vault_str = '<SEP>' + '<SEP>'.join(passwords) + '<SEP>'
        return self.encode(vault_str)
    
    def decode_vault(self, token_ids: List[int]) -> List[str]:
        """Decode token IDs to vault (list of passwords)"""
        vault_str = self.decode(token_ids)
        passwords = vault_str.split('<SEP>')[1:-1]  # Remove first/last empty
        return [pwd for pwd in passwords if pwd]  # Filter empty strings


# Example usage
if __name__ == "__main__":
    # Initialize model and tokenizer
    model = VaultTransformer()
    tokenizer = VaultTokenizer()
    
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"Vocabulary size: {tokenizer.vocab_size}")
    
    # Example vault
    example_vault = ["password123", "mySecret2024", "GuardLocker!"]
    
    # Encode vault
    tokens = tokenizer.encode_vault(example_vault)
    print(f"\nExample vault: {example_vault}")
    print(f"Encoded length: {len(tokens)}")
    
    # Generate a password
    context = "<SEP>password123<SEP>"
    generated = model.generate_password(context, tokenizer, temperature=0.8)
    print(f"\nGenerated password from context: {generated}")