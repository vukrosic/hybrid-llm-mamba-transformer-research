#!/usr/bin/env python3
"""
Simple script to upload a saved model to Hugging Face Hub
Usage: python upload_model.py --model_path path/to/model.pt --repo_name username/repo-name
"""

import os
import json
import torch
import argparse
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_model_to_hf(model_path, repo_name, model_name=None):
    """Upload a saved model to Hugging Face Hub"""
    
    # Check for HF token
    hf_token = os.getenv('HF_TOKEN')
    if not hf_token:
        print("❌ HF_TOKEN not found in .env file")
        print("   Create .env file with: HF_TOKEN=your_token_here")
        return False
    
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"❌ Model file not found: {model_path}")
        return False
    
    # Create temp directory for upload
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"🚀 Preparing upload to: {repo_name}")
        
        # Load model state dict
        try:
            checkpoint = torch.load(model_path, map_location='cpu')
            if 'model_state_dict' in checkpoint:
                model_state = checkpoint['model_state_dict']
                config = checkpoint.get('config', {})
            else:
                model_state = checkpoint
                config = {}
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
        
        # Create model config
        model_config = {
            "architectures": ["HybridModel"],
            "model_type": "hybrid_llm",
            **config
        }
        
        # Save files to temp dir
        config_path = os.path.join(temp_dir, "config.json")
        with open(config_path, 'w') as f:
            json.dump(model_config, f, indent=2)
        
        model_path_hf = os.path.join(temp_dir, "pytorch_model.bin")
        torch.save(model_state, model_path_hf)
        
        # Create README
        readme_content = f"""# Hybrid LLM Model

This is a hybrid transformer-Mamba model uploaded via script.

## Model Details
- **Architecture**: Hybrid Transformer-Mamba
- **Parameters**: {sum(p.numel() for p in model_state.values()):,}
- **Config**: {json.dumps(config, indent=2)}

## Usage
```python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("{repo_name}")
```
"""
        
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        # Clone existing repo
        try:
            subprocess.run([
                "git", "clone", f"https://huggingface.co/{repo_name}", temp_dir + "/repo"
            ], check=True, capture_output=True)
            
            repo_dir = temp_dir + "/repo"
            
            # Copy files to repo
            import shutil
            for file in os.listdir(temp_dir):
                if file != "repo":
                    src = os.path.join(temp_dir, file)
                    dst = os.path.join(repo_dir, file)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
            
            # Commit and push
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run([
                "git", "commit", "-m", f"Add model: {model_name or model_path.name}"
            ], cwd=repo_dir, check=True)
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            
            print(f"✅ Model uploaded successfully to: https://huggingface.co/{repo_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Upload saved model to Hugging Face Hub")
    parser.add_argument("--model_path", required=True, help="Path to saved model (.pt file)")
    parser.add_argument("--repo_name", required=True, help="HF repo name (username/repo-name)")
    parser.add_argument("--model_name", help="Optional name for the model")
    
    args = parser.parse_args()
    
    success = upload_model_to_hf(args.model_path, args.repo_name, args.model_name)
    if success:
        print("🎉 Upload complete!")
    else:
        print("�� Upload failed!")

if __name__ == "__main__":
    main()
