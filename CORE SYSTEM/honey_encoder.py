"""
GuardLocker - Honey Encryption Encoder
Implementation of IS-PMTE (Inverse Sampling Probability-Model-Transforming Encoder)

Based on:
- Juels & Ristenpart, "Honey Encryption" (EUROCRYPT 2014)
- Cheng et al., "Probability Model Transforming Encoders" (USENIX Security 2019)
"""

import struct
import secrets
import numpy as np
from typing import List, Tuple, Optional
import torch
from vault_transformer import VaultTransformer, VaultTokenizer


class HoneyEncoder:
    """
    Inverse Sampling Probability-Model-Transforming Encoder
    
    Encodes messages to uniformly random seeds and vice versa,
    enabling honey encryption with plausible decoys.
    """
    
    def __init__(
        self,
        model: VaultTransformer,
        tokenizer: VaultTokenizer,
        seed_bits: int = 256
    ):
        """
        Initialize encoder
        
        Args:
            model: Trained Transformer model for vault distribution
            tokenizer: Tokenizer instance
            seed_bits: Number of bits in seed space
        """
        self.model = model
        self.tokenizer = tokenizer
        self.seed_bits = seed_bits
        self.seed_space_size = 2 ** seed_bits
        
        # For numerical stability
        self.epsilon = 1e-10
    
    def encode_vault(self, passwords: List[str]) -> bytes:
        """
        Encode a vault to a uniformly random seed
        
        Process:
        1. Build vault string: <SEP>pwd1<SEP>pwd2<SEP>...
        2. For each character, map to cumulative probability interval
        3. Use inverse sampling to convert interval to seed bits
        4. Concatenate all seed bits
        
        Args:
            passwords: List of passwords in vault
        
        Returns:
            Seed as bytes
        """
        seed_value = 0
        bits_used = 0
        context = '<SEP>'
        
        for password in passwords:
            # Encode each character in password
            for char in password:
                # Get probability distribution for next character
                probs = self._get_char_probabilities(context)
                
                # Get cumulative probability interval for this character
                char_id = self.tokenizer.char_to_id(char)
                interval_start, interval_end = self._get_cumulative_interval(
                    char_id, probs
                )
                
                # Use inverse sampling: select random point in interval
                # and map to seed space
                seed_chunk, chunk_bits = self._interval_to_seed(
                    interval_start, interval_end
                )
                
                # Accumulate seed bits
                seed_value = (seed_value << chunk_bits) | seed_chunk
                bits_used += chunk_bits
                
                context += char
            
            # Encode separator
            context += '<SEP>'
            sep_id = self.tokenizer.char_to_id('<SEP>')
            probs = self._get_char_probabilities(context[:-5])
            interval_start, interval_end = self._get_cumulative_interval(
                sep_id, probs
            )
            seed_chunk, chunk_bits = self._interval_to_seed(
                interval_start, interval_end
            )
            seed_value = (seed_value << chunk_bits) | seed_chunk
            bits_used += chunk_bits
        
        # Convert to bytes
        num_bytes = (bits_used + 7) // 8
        seed_bytes = seed_value.to_bytes(num_bytes, byteorder='big')
        
        return seed_bytes
    
    def decode_seed(
        self,
        seed: bytes,
        max_passwords: int = 50,
        max_total_length: int = 1000
    ) -> List[str]:
        """
        Decode a seed to a vault
        
        Process:
        1. Convert seed to integer
        2. For each position, extract probability interval from seed bits
        3. Sample character from interval using model
        4. Continue until separator or length limit
        
        Args:
            seed: Seed bytes
            max_passwords: Maximum number of passwords to decode
            max_total_length: Maximum total length to prevent infinite loops
        
        Returns:
            List of decoded passwords
        """
        # Convert seed to integer
        seed_value = int.from_bytes(seed, byteorder='big')
        
        passwords = []
        context = '<SEP>'
        current_password = ''
        chars_decoded = 0
        
        while len(passwords) < max_passwords and chars_decoded < max_total_length:
            # Get probability distribution
            probs = self._get_char_probabilities(context)
            
            # Extract character from seed using inverse sampling
            char_id, bits_consumed = self._seed_to_character(
                seed_value, probs
            )
            
            # Consume bits from seed
            seed_value = seed_value >> bits_consumed
            
            # Decode character
            char = self.tokenizer.id_to_char(char_id)
            
            if char == '<SEP>':
                if current_password:
                    passwords.append(current_password)
                    current_password = ''
                context += '<SEP>'
            else:
                current_password += char
                context += char
            
            chars_decoded += 1
            
            # Safety check for password length
            if len(current_password) > 25:
                # Force separator
                if current_password:
                    passwords.append(current_password)
                    current_password = ''
                context += '<SEP>'
        
        # Add any remaining password
        if current_password:
            passwords.append(current_password)
        
        return passwords
    
    def _get_char_probabilities(self, context: str) -> torch.Tensor:
        """Get probability distribution for next character"""
        return self.model.predict_next_char(context, self.tokenizer)
    
    def _get_cumulative_interval(
        self,
        char_id: int,
        probs: torch.Tensor
    ) -> Tuple[float, float]:
        """
        Get cumulative probability interval for a character
        
        Args:
            char_id: Character token ID
            probs: Probability distribution
        
        Returns:
            (interval_start, interval_end) in [0, 1]
        """
        # Convert to numpy for easier manipulation
        probs_np = probs.cpu().numpy()
        
        # Calculate cumulative probabilities
        cumsum = np.cumsum(probs_np)
        
        # Get interval
        if char_id == 0:
            interval_start = 0.0
        else:
            interval_start = cumsum[char_id - 1]
        
        interval_end = cumsum[char_id]
        
        return float(interval_start), float(interval_end)
    
    def _interval_to_seed(
        self,
        interval_start: float,
        interval_end: float
    ) -> Tuple[int, int]:
        """
        Convert probability interval to seed value using inverse sampling
        
        Args:
            interval_start: Start of interval [0, 1]
            interval_end: End of interval [0, 1]
        
        Returns:
            (seed_chunk, bits_used)
        """
        # Calculate interval size
        interval_size = interval_end - interval_start
        
        # Calculate number of bits needed to represent this interval
        # More probable intervals use fewer bits
        if interval_size <= 0:
            interval_size = self.epsilon
        
        bits_needed = max(1, int(-np.log2(interval_size)) + 1)
        bits_needed = min(bits_needed, 32)  # Cap at 32 bits per chunk
        
        # Map interval to seed space
        seed_space = 2 ** bits_needed
        seed_start = int(interval_start * seed_space)
        seed_end = int(interval_end * seed_space)
        
        # Randomly select a point in the interval
        if seed_end <= seed_start:
            seed_end = seed_start + 1
        
        seed_chunk = secrets.randbelow(seed_end - seed_start) + seed_start
        
        return seed_chunk, bits_needed
    
    def _seed_to_character(
        self,
        seed_value: int,
        probs: torch.Tensor
    ) -> Tuple[int, int]:
        """
        Extract character from seed using inverse sampling
        
        Args:
            seed_value: Current seed value
            probs: Probability distribution
        
        Returns:
            (character_id, bits_consumed)
        """
        # Convert to numpy
        probs_np = probs.cpu().numpy()
        cumsum = np.cumsum(probs_np)
        
        # Estimate bits needed for this position
        max_bits = 32
        
        # Try different bit widths to find best match
        for bits in range(1, max_bits + 1):
            seed_space = 2 ** bits
            # Extract bits from seed
            extracted_bits = seed_value & ((1 << bits) - 1)
            
            # Convert to probability value [0, 1]
            prob_value = extracted_bits / seed_space
            
            # Find character with this cumulative probability
            char_id = np.searchsorted(cumsum, prob_value, side='right')
            
            # Verify this is a valid encoding
            if char_id < len(probs_np):
                interval_start, interval_end = self._get_cumulative_interval(
                    char_id, probs
                )
                
                # Check if our extracted value falls in this interval
                seed_start = int(interval_start * seed_space)
                seed_end = int(interval_end * seed_space)
                
                if seed_start <= extracted_bits < seed_end:
                    return int(char_id), bits
        
        # Fallback: use maximum bits and best guess
        seed_space = 2 ** max_bits
        extracted_bits = seed_value & ((1 << max_bits) - 1)
        prob_value = extracted_bits / seed_space
        char_id = np.searchsorted(cumsum, prob_value, side='right')
        
        return int(min(char_id, len(probs_np) - 1)), max_bits
    
    def encode_incremental(
        self,
        old_seed: bytes,
        new_password: str,
        context: List[str]
    ) -> bytes:
        """
        Incrementally add a password to existing vault
        
        Uses prefix-keeping property for efficiency and security
        
        Args:
            old_seed: Existing vault seed
            new_password: Password to add
            context: Existing passwords for context
        
        Returns:
            New seed with appended password
        """
        # Build context from existing passwords
        context_str = '<SEP>' + '<SEP>'.join(context) + '<SEP>'
        
        # Encode only the new password
        seed_value = 0
        bits_used = 0
        
        for char in new_password:
            probs = self._get_char_probabilities(context_str)
            char_id = self.tokenizer.char_to_id(char)
            interval_start, interval_end = self._get_cumulative_interval(
                char_id, probs
            )
            seed_chunk, chunk_bits = self._interval_to_seed(
                interval_start, interval_end
            )
            seed_value = (seed_value << chunk_bits) | seed_chunk
            bits_used += chunk_bits
            context_str += char
        
        # Encode separator
        context_str += '<SEP>'
        sep_id = self.tokenizer.char_to_id('<SEP>')
        probs = self._get_char_probabilities(context_str[:-5])
        interval_start, interval_end = self._get_cumulative_interval(
            sep_id, probs
        )
        seed_chunk, chunk_bits = self._interval_to_seed(
            interval_start, interval_end
        )
        seed_value = (seed_value << chunk_bits) | seed_chunk
        bits_used += chunk_bits
        
        # Convert to bytes
        num_bytes = (bits_used + 7) // 8
        new_seed_bytes = seed_value.to_bytes(num_bytes, byteorder='big')
        
        # Concatenate with old seed (prefix-keeping)
        return old_seed + new_seed_bytes


# Example usage and testing
if __name__ == "__main__":
    from vault_transformer import VaultTransformer, VaultTokenizer
    
    # Initialize model and tokenizer
    print("Initializing model...")
    model = VaultTransformer()
    tokenizer = VaultTokenizer()
    
    # Initialize encoder
    encoder = HoneyEncoder(model, tokenizer)
    
    # Test encoding and decoding
    print("\n=== Test 1: Basic Encoding/Decoding ===")
    original_vault = ["password123", "MySecret2024"]
    print(f"Original vault: {original_vault}")
    
    # Encode
    seed = encoder.encode_vault(original_vault)
    print(f"Encoded seed length: {len(seed)} bytes")
    print(f"Seed (hex): {seed.hex()[:64]}...")
    
    # Decode
    decoded_vault = encoder.decode_seed(seed, max_passwords=len(original_vault))
    print(f"Decoded vault: {decoded_vault}")
    
    # Test with random seed (generates decoy)
    print("\n=== Test 2: Decoy Generation ===")
    random_seed = secrets.token_bytes(32)
    decoy_vault = encoder.decode_seed(random_seed, max_passwords=5)
    print(f"Decoy vault from random seed: {decoy_vault}")
    
    # Test incremental update
    print("\n=== Test 3: Incremental Update ===")
    new_password = "NewPass456"
    updated_seed = encoder.encode_incremental(seed, new_password, original_vault)
    print(f"Updated seed length: {len(updated_seed)} bytes")
    
    decoded_updated = encoder.decode_seed(
        updated_seed, 
        max_passwords=len(original_vault) + 1
    )
    print(f"Decoded updated vault: {decoded_updated}")