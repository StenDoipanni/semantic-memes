#!/bin/bash
# Test SSH connection from local machine
# Run this on your LOCAL Mac

REMOTE_USER="stefano"
REMOTE_HOST="stlab-disi-delfino"

echo "Testing SSH connection to $REMOTE_USER@$REMOTE_HOST..."
ssh -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH connection successful!'" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ SSH connection works! You can use the Python script."
else
    echo "✗ SSH connection failed. Possible reasons:"
    echo "  1. Server hostname not resolvable from your network"
    echo "  2. Need to use IP address instead of hostname"
    echo "  3. Need to connect via VPN"
    echo "  4. SSH keys not set up"
    echo ""
    echo "Alternative: Use Option 1 (two-step process) instead."
fi

