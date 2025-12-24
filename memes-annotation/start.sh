#!/bin/bash
# Quick start script for Meme Annotation Service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Meme Annotation Service..."
echo "📁 Working directory: $SCRIPT_DIR"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the service
echo "🌐 Starting Streamlit on http://localhost:8888"
echo "🛑 Press Ctrl+C to stop"
echo ""

streamlit run app.py --server.port=8888






