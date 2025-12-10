#!/bin/bash

# Setup script to install required packages in the conda environment
# This ensures transformers and other dependencies are available

set -e

CONDA_ENV="meme-qa-pipeline-env"
HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"

echo "🔧 Setting up conda environment: $CONDA_ENV"
echo "=========================================="

# Activate conda environment
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f /opt/miniconda3/etc/profile.d/conda.sh ]; then
    source /opt/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
fi

conda activate "$CONDA_ENV"

if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
    echo "❌ Error: Failed to activate $CONDA_ENV environment"
    exit 1
fi

echo "✅ Environment activated: $CONDA_DEFAULT_ENV"
echo ""

# Verify Python and pip
PYTHON_CMD=$(which python)
PIP_CMD=$(which pip)
echo "📍 Using Python: $PYTHON_CMD"
echo "📍 Using pip: $PIP_CMD"
echo ""

# Check if torch is already installed
echo "🔍 Checking existing packages..."
if python -c "import torch" 2>/dev/null; then
    TORCH_VERSION=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
    echo "  ✅ Torch is already installed (version: $TORCH_VERSION)"
else
    echo "📦 Installing torch..."
    python -m pip install torch || {
        echo "❌ Error: Failed to install torch"
        exit 1
    }
    echo "✅ Torch installed"
fi
echo ""

# Check if transformers is installed in conda environment (not user's local)
echo "🔍 Checking transformers installation location..."
TRANSFORMERS_LOCATION=$(python -c "import transformers; import os; print(os.path.dirname(transformers.__file__))" 2>/dev/null || echo "")

if [[ -n "$TRANSFORMERS_LOCATION" ]]; then
    if [[ "$TRANSFORMERS_LOCATION" == *"$CONDA_PREFIX"* ]]; then
        TRANSFORMERS_VERSION=$(python -c "import transformers; print(transformers.__version__)" 2>/dev/null)
        echo "  ✅ Transformers is installed in conda environment (version: $TRANSFORMERS_VERSION)"
        
        # Check if Qwen3-VL support is needed
        if [[ "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
            echo "  🔍 Checking if current transformers version supports Qwen3-VL..."
            if python -c "from transformers import Qwen3VLForConditionalGeneration" 2>/dev/null; then
                echo "  ✅ Current transformers version supports Qwen3-VL, no upgrade needed"
            else
                echo "  ⚠️  Current version may not support Qwen3-VL, upgrading from source..."
                echo "  ⚠️  This may take several minutes..."
                python -m pip install --upgrade --force-reinstall --no-deps git+https://github.com/huggingface/transformers.git || {
                    echo "❌ Error: Failed to upgrade transformers from source"
                    exit 1
                }
                echo "  ✅ Transformers upgraded"
            fi
        fi
    else
        echo "  ⚠️  Transformers is installed in user's local site-packages: $TRANSFORMERS_LOCATION"
        echo "  📦 Installing transformers in conda environment..."
        # Uninstall from user's local first to avoid conflicts
        python -m pip uninstall -y transformers 2>/dev/null || true
        
        if [[ "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
            echo "  Installing from source for Qwen3-VL support..."
            echo "  ⚠️  This may take several minutes..."
            python -m pip install --no-cache-dir git+https://github.com/huggingface/transformers.git || {
                echo "❌ Error: Failed to install transformers from source"
                exit 1
            }
        else
            python -m pip install --no-cache-dir transformers || {
                echo "❌ Error: Failed to install transformers"
                exit 1
            }
        fi
        echo "  ✅ Transformers installed in conda environment"
    fi
else
    # Install transformers if not present
    echo "📦 Installing transformers in conda environment..."
    if [[ "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
        echo "  Installing from source for Qwen3-VL support..."
        echo "  ⚠️  This may take several minutes..."
        python -m pip install --no-cache-dir git+https://github.com/huggingface/transformers.git || {
            echo "❌ Error: Failed to install transformers from source"
            exit 1
        }
    else
        python -m pip install --no-cache-dir transformers || {
            echo "❌ Error: Failed to install transformers"
            exit 1
        }
    fi
    echo "✅ Transformers installed"
fi

# Fix huggingface-hub version conflict if needed
echo ""
echo "🔍 Checking huggingface-hub version..."
if python -c "import transformers" 2>/dev/null; then
    # Try to import and see if there's a version conflict
    if ! python -c "import transformers; from transformers import dependency_versions_check" 2>/dev/null; then
        echo "  ⚠️  Detected version conflict, fixing huggingface-hub..."
        python -m pip install --upgrade "huggingface-hub>=1.0.0" || {
            echo "  ⚠️  Could not fix huggingface-hub automatically"
        }
    fi
fi
echo ""

# Verify installation
echo ""
echo "🔍 Verifying installation..."
python -c "import transformers; print(f'✅ Transformers {transformers.__version__} is installed')" || {
    echo "❌ Error: Transformers verification failed"
    exit 1
}

python -c "import torch; print(f'✅ Torch {torch.__version__} is installed')" || {
    echo "❌ Error: Torch verification failed"
    exit 1
}

echo ""
echo "🎉 Setup completed successfully!"
echo "✅ All required packages are installed in $CONDA_ENV"

