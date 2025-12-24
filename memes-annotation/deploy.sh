#!/bin/bash
# Deployment script for Meme Annotation Service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="meme-annotation"
PORT=8888

echo "🚀 Deploying Meme Annotation Service..."

# Check if running as root for systemd setup
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Running as root. Setting up systemd service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Meme Annotation Streamlit Service
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$PROJECT_ROOT/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$(which streamlit) run $SCRIPT_DIR/app.py --server.port=$PORT --server.address=0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}.service
    systemctl restart ${SERVICE_NAME}.service
    
    echo "✅ Service installed and started!"
    echo "📊 Check status with: sudo systemctl status ${SERVICE_NAME}"
    echo "📝 View logs with: sudo journalctl -u ${SERVICE_NAME} -f"
    
else
    echo "📝 Running as regular user. Using nohup method..."
    
    # Check if service is already running
    if pgrep -f "streamlit.*app.py" > /dev/null; then
        echo "⚠️  Service appears to be already running. Stopping..."
        pkill -f "streamlit.*app.py"
        sleep 2
    fi
    
    # Start service in background
    cd "$SCRIPT_DIR"
    nohup streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 > streamlit.log 2>&1 &
    
    echo "✅ Service started in background!"
    echo "📊 Check logs with: tail -f $SCRIPT_DIR/streamlit.log"
    echo "🛑 Stop with: pkill -f 'streamlit.*app.py'"
fi

echo ""
echo "🌐 Service should be accessible at:"
echo "   - Local: http://localhost:$PORT"
echo "   - Network: http://$(hostname -I | awk '{print $1}'):$PORT"
echo ""
echo "🔒 If accessing from outside, ensure firewall allows port $PORT:"
echo "   sudo ufw allow $PORT/tcp"






