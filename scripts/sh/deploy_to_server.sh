#!/bin/bash

# Meme Pipeline Server Deployment Script
# This script prepares and deploys the meme analysis pipeline to a server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Meme Pipeline Server Deployment${NC}"
echo "=============================================="

# Configuration
SERVER_USER="${1:-ubuntu}"
SERVER_HOST="${2:-your-server.com}"
SERVER_PATH="/opt/meme-pipeline"
LOCAL_PACKAGE="meme-pipeline-server.tar.gz"

echo -e "${YELLOW}📋 Deployment Configuration:${NC}"
echo "  Server User: $SERVER_USER"
echo "  Server Host: $SERVER_HOST"
echo "  Server Path: $SERVER_PATH"
echo "  Local Package: $LOCAL_PACKAGE"
echo ""

# Step 1: Create deployment package
echo -e "${BLUE}📦 Step 1: Creating deployment package...${NC}"
tar -czf "$LOCAL_PACKAGE" \
    --exclude="output/*" \
    --exclude="__pycache__/*" \
    --exclude="*.pyc" \
    --exclude="*.log" \
    --exclude=".env" \
    --exclude="*.zip" \
    .

echo -e "${GREEN}✅ Package created: $LOCAL_PACKAGE${NC}"

# Step 2: Copy to server
echo -e "${BLUE}📤 Step 2: Copying to server...${NC}"
scp "$LOCAL_PACKAGE" "$SERVER_USER@$SERVER_HOST:/tmp/"

echo -e "${GREEN}✅ Package copied to server${NC}"

# Step 3: Deploy on server
echo -e "${BLUE}🔧 Step 3: Deploying on server...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" << EOF
    set -e
    
    echo "📁 Creating server directory structure..."
    sudo mkdir -p $SERVER_PATH
    sudo chown $USER:$USER $SERVER_PATH
    
    echo "📦 Extracting package..."
    cd $SERVER_PATH
    tar -xzf /tmp/$LOCAL_PACKAGE
    
    echo "🔧 Setting up Python environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "📁 Creating output directories..."
    mkdir -p output/dimensions output/qa
    
    echo "🔑 Setting up environment variables..."
    cat > .env << 'ENVEOF'
# Server Environment Variables
ONTOLOGY_PATH=$SERVER_PATH/memes-features/meme-dimensions.ttl
PROMPTS_DIR=$SERVER_PATH/memes-features/prompts/dimension-extraction-prompts
OUTPUT_DIR=$SERVER_PATH/output
LLM_PROVIDER=ollama
SERVER_MODE=true
ENVEOF
    
    echo "🧹 Cleaning up..."
    rm /tmp/$LOCAL_PACKAGE
    
    echo "✅ Server deployment completed!"
    echo "📋 Next steps:"
    echo "  1. Copy memes-features folder to $SERVER_PATH/"
    echo "  2. Install and configure Ollama"
    echo "  3. Test the pipeline"
EOF

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Manual steps required on server:${NC}"
echo "  1. Copy memes-features folder: scp -r memes-features/ $SERVER_USER@$SERVER_HOST:$SERVER_PATH/"
echo "  2. Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh"
echo "  3. Pull model: ollama pull llama3.2:latest"
echo "  4. Test: ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && python3 test_pipeline.py'"

