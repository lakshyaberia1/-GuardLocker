"""
GuardLocker - Model Training Pipeline
Train Transformer model on password vault dataset
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path
import json
from tqdm import tqdm
import logging
from dataclasses import dataclass

from vault_transformer import VaultTransformer, VaultTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration"""
    # Model parameters
    d_model: int = 768
    nhead: int = 12
    num_layers: int = 12
    dim_feedforward: int = 3072
    dropout: float = 0.1
    
    # Training parameters
    batch_size: int = 32
    gradient_accumulation_steps: int = 2
    num_epochs: int = 5
    learning_rate: float = 1e-4
    warmup_steps: int = 1000
    max_grad_norm: float = 0.5
    
    # Data parameters
    max_seq_length: int = 1000
    max_passwords_per_vault: int = 50
    
    # Paths
    data_dir: str = "./data"
    checkpoint_dir: str = "./checkpoints"
    log_dir: str = "./logs"
    
    # Device
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


class VaultDataset(Dataset):
    """
    Dataset for password vaults
    
    Loads and preprocesses vault data for training
    """
    
    def __init__(
        self,
        vaults: List[List[str]],
        tokenizer: VaultTokenizer,
        max_seq_length: int = 1000
    ):
        """
        Initialize dataset
        
        Args:
            vaults: List of vaults (each vault is a list of passwords)
            tokenizer: Tokenizer instance
            max_seq_length: Maximum sequence length
        """
        self.vaults = vaults
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length
        
        # Filter vaults that are too long
        self.valid_vaults = []
        for vault in vaults:
            tokens = tokenizer.encode_vault(vault)
            if len(tokens) <= max_seq_length:
                self.valid_vaults.append(vault)
        
        logger.info(f"Loaded {len(self.valid_vaults)} valid vaults")
    
    def __len__(self) -> int:
        return len(self.valid_vaults)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get a single training example
        
        Returns:
            (input_ids, target_ids) where target is shifted by 1
        """
        vault = self.valid_vaults[idx]
        
        # Encode vault
        tokens = self.tokenizer.encode_vault(vault)
        
        # Create input and target sequences
        # Input: tokens[:-1], Target: tokens[1:]
        input_ids = torch.tensor(tokens[:-1], dtype=torch.long)
        target_ids = torch.tensor(tokens[1:], dtype=torch.long)
        
        return input_ids, target_ids


def collate_fn(batch: List[Tuple[torch.Tensor, torch.Tensor]]) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Collate function for DataLoader
    
    Pads sequences to same length in batch
    """
    input_ids = [item[0] for item in batch]
    target_ids = [item[1] for item in batch]
    
    # Pad sequences
    input_ids_padded = nn.utils.rnn.pad_sequence(
        input_ids, batch_first=True, padding_value=0
    )
    target_ids_padded = nn.utils.rnn.pad_sequence(
        target_ids, batch_first=True, padding_value=-100  # Ignore index for loss
    )
    
    return input_ids_padded, target_ids_padded


class VaultTrainer:
    """Trainer for vault Transformer model"""
    
    def __init__(
        self,
        model: VaultTransformer,
        config: TrainingConfig,
        train_dataset: VaultDataset,
        val_dataset: Optional[VaultDataset] = None
    ):
        """
        Initialize trainer
        
        Args:
            model: Transformer model to train
            config: Training configuration
            train_dataset: Training dataset
            val_dataset: Optional validation dataset
        """
        self.model = model.to(config.device)
        self.config = config
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        
        # Create data loaders
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=config.batch_size,
            shuffle=True,
            collate_fn=collate_fn,
            num_workers=4,
            pin_memory=True
        )
        
        if val_dataset:
            self.val_loader = DataLoader(
                val_dataset,
                batch_size=config.batch_size,
                shuffle=False,
                collate_fn=collate_fn,
                num_workers=4,
                pin_memory=True
            )
        
        # Optimizer and scheduler
        self.optimizer = AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=0.01
        )
        
        total_steps = len(self.train_loader) * config.num_epochs
        self.scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=total_steps,
            eta_min=1e-6
        )
        
        # Loss function
        self.criterion = nn.CrossEntropyLoss(ignore_index=-100)
        
        # Training state
        self.current_epoch = 0
        self.global_step = 0
        self.best_val_loss = float('inf')
        
        # Create directories
        Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)
        Path(config.log_dir).mkdir(parents=True, exist_ok=True)
    
    def train(self):
        """Train the model"""
        logger.info("Starting training...")
        logger.info(f"Device: {self.config.device}")
        logger.info(f"Epochs: {self.config.num_epochs}")
        logger.info(f"Batch size: {self.config.batch_size}")
        logger.info(f"Gradient accumulation: {self.config.gradient_accumulation_steps}")
        
        for epoch in range(self.config.num_epochs):
            self.current_epoch = epoch
            
            # Train epoch
            train_loss = self._train_epoch()
            logger.info(f"Epoch {epoch+1}/{self.config.num_epochs} - Train Loss: {train_loss:.4f}")
            
            # Validate
            if self.val_dataset:
                val_loss = self._validate()
                logger.info(f"Epoch {epoch+1}/{self.config.num_epochs} - Val Loss: {val_loss:.4f}")
                
                # Save best model
                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self._save_checkpoint('best_model.pt')
                    logger.info(f"New best model saved (val_loss: {val_loss:.4f})")
            
            # Save checkpoint
            self._save_checkpoint(f'checkpoint_epoch_{epoch+1}.pt')
        
        logger.info("Training complete!")
    
    def _train_epoch(self) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        progress_bar = tqdm(self.train_loader, desc=f"Epoch {self.current_epoch+1}")
        
        for batch_idx, (input_ids, target_ids) in enumerate(progress_bar):
            # Move to device
            input_ids = input_ids.to(self.config.device)
            target_ids = target_ids.to(self.config.device)
            
            # Forward pass
            logits = self.model(input_ids)
            
            # Calculate loss
            loss = self.criterion(
                logits.reshape(-1, logits.size(-1)),
                target_ids.reshape(-1)
            )
            
            # Scale loss for gradient accumulation
            loss = loss / self.config.gradient_accumulation_steps
            
            # Backward pass
            loss.backward()
            
            # Gradient accumulation
            if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                # Clip gradients
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.max_grad_norm
                )
                
                # Update weights
                self.optimizer.step()
                self.scheduler.step()
                self.optimizer.zero_grad()
                
                self.global_step += 1
            
            # Track loss
            total_loss += loss.item() * self.config.gradient_accumulation_steps
            num_batches += 1
            
            # Update progress bar
            progress_bar.set_postfix({
                'loss': f"{loss.item() * self.config.gradient_accumulation_steps:.4f}",
                'lr': f"{self.scheduler.get_last_lr()[0]:.2e}"
            })
        
        return total_loss / num_batches
    
    def _validate(self) -> float:
        """Validate the model"""
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        with torch.no_grad():
            for input_ids, target_ids in tqdm(self.val_loader, desc="Validation"):
                # Move to device
                input_ids = input_ids.to(self.config.device)
                target_ids = target_ids.to(self.config.device)
                
                # Forward pass
                logits = self.model(input_ids)
                
                # Calculate loss
                loss = self.criterion(
                    logits.reshape(-1, logits.size(-1)),
                    target_ids.reshape(-1)
                )
                
                total_loss += loss.item()
                num_batches += 1
        
        return total_loss / num_batches
    
    def _save_checkpoint(self, filename: str):
        """Save model checkpoint"""
        checkpoint_path = Path(self.config.checkpoint_dir) / filename
        
        torch.save({
            'epoch': self.current_epoch,
            'global_step': self.global_step,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'config': self.config
        }, checkpoint_path)
    
    def load_checkpoint(self, checkpoint_path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(checkpoint_path, map_location=self.config.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.current_epoch = checkpoint['epoch']
        self.global_step = checkpoint['global_step']
        self.best_val_loss = checkpoint['best_val_loss']
        
        logger.info(f"Loaded checkpoint from epoch {self.current_epoch}")


def load_vault_data(data_path: str, max_vaults: Optional[int] = None) -> List[List[str]]:
    """
    Load vault data from file
    
    Expected format: JSON file with list of vaults
    Each vault is a list of passwords
    
    Args:
        data_path: Path to data file
        max_vaults: Maximum number of vaults to load
    
    Returns:
        List of vaults
    """
    logger.info(f"Loading vault data from {data_path}")
    
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    vaults = data['vaults'] if 'vaults' in data else data
    
    if max_vaults:
        vaults = vaults[:max_vaults]
    
    logger.info(f"Loaded {len(vaults)} vaults")
    
    return vaults


def export_to_onnx(
    model: VaultTransformer,
    output_path: str,
    opset_version: int = 14
):
    """
    Export model to ONNX format for efficient inference
    
    Args:
        model: Trained model
        output_path: Path to save ONNX model
        opset_version: ONNX opset version
    """
    model.eval()
    
    # Dummy input
    dummy_input = torch.randint(0, model.vocab_size, (1, 50))
    
    # Export
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        opset_version=opset_version,
        input_names=['input_ids'],
        output_names=['logits'],
        dynamic_axes={
            'input_ids': {0: 'batch_size', 1: 'sequence_length'},
            'logits': {0: 'batch_size', 1: 'sequence_length'}
        }
    )
    
    logger.info(f"Model exported to ONNX: {output_path}")


# Example usage
if __name__ == "__main__":
    # Configuration
    config = TrainingConfig(
        batch_size=32,
        gradient_accumulation_steps=2,
        num_epochs=5,
        learning_rate=1e-4,
        warmup_steps=1000,
        max_grad_norm=0.5
    )
    
    # Load or create synthetic data
    # In production, use real vault dataset
    logger.info("Creating synthetic training data...")
    synthetic_vaults = []
    for i in range(10000):
        vault_size = np.random.randint(2, 10)
        vault = [f"password{j}_{i}" for j in range(vault_size)]
        synthetic_vaults.append(vault)
    
    # Split into train/val
    split_idx = int(len(synthetic_vaults) * 0.9)
    train_vaults = synthetic_vaults[:split_idx]
    val_vaults = synthetic_vaults[split_idx:]
    
    # Initialize tokenizer and model
    tokenizer = VaultTokenizer()
    model = VaultTransformer(vocab_size=tokenizer.vocab_size)
    
    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Create datasets
    train_dataset = VaultDataset(train_vaults, tokenizer, config.max_seq_length)
    val_dataset = VaultDataset(val_vaults, tokenizer, config.max_seq_length)
    
    # Initialize trainer
    trainer = VaultTrainer(model, config, train_dataset, val_dataset)
    
    # Train
    trainer.train()
    
    # Export to ONNX
    export_to_onnx(model, "vault_model.onnx")
    
    logger.info("Training pipeline complete!")
    