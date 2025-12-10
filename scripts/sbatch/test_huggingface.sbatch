#!/bin/bash
#SBATCH --job-name=test_huggingface
#SBATCH --output=logs/slurm/test_huggingface_%j.out
#SBATCH --error=logs/slurm/test_huggingface_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:30:00

set -e

echo "🧪 Testing HuggingFace/Qwen2-VL"
echo "==============================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo ""

# Load necessary modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0
module load CUDA/12.1.1

# Set GPU environment variables
export CUDA_VISIBLE_DEVICES=0

# Verify CUDA
echo "🔍 Verifying GPU..."
python3 -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU Device: {torch.cuda.get_device_name(0)}')
    print(f'GPU Device ID: {torch.cuda.current_device()}')
else:
    print('❌ CUDA not available')
    exit(1)
"
echo "✅ GPU verified"
echo ""

# Activate conda environment
source /home/sdegiorgis/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Run test
echo "🚀 Running HuggingFace test..."
echo ""
python3 test_huggingface.py

echo ""
echo "✅ Test completed"

