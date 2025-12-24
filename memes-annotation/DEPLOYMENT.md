# Deployment Guide: Meme Annotation Service

This guide explains how to set up the Meme Annotation Service as a permanent, web-accessible service.

## Prerequisites

1. Python 3.8+ installed
2. Streamlit installed (`pip install streamlit`)
3. Access to the server/machine where you want to run the service
4. (Optional) sudo/root access for systemd setup

## Quick Start (Development)

For testing or development:

```bash
cd memes-annotation
./start.sh
```

Or manually:

```bash
cd memes-annotation
streamlit run app.py
```

The service will be available at `http://localhost:8888`

## Permanent Service Setup

### Option 1: Systemd Service (Recommended for Production)

This method ensures the service starts automatically on boot and restarts if it crashes.

#### Step 1: Create the Service File

```bash
sudo nano /etc/systemd/system/meme-annotation.service
```

#### Step 2: Add Service Configuration

Replace `your_username` with your actual username and adjust paths as needed:

```ini
[Unit]
Description=Meme Annotation Streamlit Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/stefano/memes/semantic-memes/memes-annotation
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/streamlit run /home/stefano/memes/semantic-memes/memes-annotation/app.py --server.port=8888 --server.address=0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Note**: Find your streamlit path with `which streamlit`

#### Step 3: Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (starts on boot)
sudo systemctl enable meme-annotation.service

# Start the service
sudo systemctl start meme-annotation.service

# Check status
sudo systemctl status meme-annotation.service
```

#### Step 4: Useful Commands

```bash
# View logs
sudo journalctl -u meme-annotation.service -f

# Stop service
sudo systemctl stop meme-annotation.service

# Restart service
sudo systemctl restart meme-annotation.service

# Disable auto-start on boot
sudo systemctl disable meme-annotation.service
```

### Option 2: Using the Deployment Script

The provided `deploy.sh` script automates the setup:

```bash
cd memes-annotation

# As regular user (uses nohup)
./deploy.sh

# As root/sudo (creates systemd service)
sudo ./deploy.sh
```

### Option 3: Using nohup (Simple Background Process)

```bash
cd /home/stefano/memes/semantic-memes/memes-annotation
nohup streamlit run app.py --server.port=8888 --server.address=0.0.0.0 > streamlit.log 2>&1 &
```

To stop:
```bash
pkill -f "streamlit.*app.py"
```

### Option 4: Using screen/tmux (For Manual Management)

**Using screen:**
```bash
screen -S meme-annotation
cd /home/stefano/memes/semantic-memes/memes-annotation
streamlit run app.py --server.port=8888 --server.address=0.0.0.0
# Press Ctrl+A then D to detach

# Reattach later
screen -r meme-annotation
```

**Using tmux:**
```bash
tmux new -s meme-annotation
cd /home/stefano/memes/semantic-memes/memes-annotation
streamlit run app.py --server.port=8888 --server.address=0.0.0.0
# Press Ctrl+B then D to detach

# Reattach later
tmux attach -t meme-annotation
```

## Network Access

### Firewall Configuration

To allow access from other machines, open port 8888:

**Ubuntu/Debian:**
```bash
sudo ufw allow 8888/tcp
sudo ufw reload
```

**CentOS/RHEL:**
```bash
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --reload
```

**Check if port is open:**
```bash
sudo netstat -tulpn | grep 8888
# or
sudo ss -tulpn | grep 8888
```

### Access URLs

- **Local**: `http://localhost:8888`
- **Network**: `http://YOUR_SERVER_IP:8888`
- **Find your IP**: `hostname -I` or `ip addr show`

## Reverse Proxy with Nginx (Optional)

For production, use nginx as a reverse proxy with SSL:

### 1. Install Nginx

```bash
sudo apt-get update
sudo apt-get install nginx
```

### 2. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/meme-annotation
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    location / {
        proxy_pass http://localhost:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

### 3. Enable and Restart

```bash
sudo ln -s /etc/nginx/sites-available/meme-annotation /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### 4. SSL with Let's Encrypt (Optional)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Troubleshooting

### Service Won't Start

1. **Check if port is in use:**
   ```bash
   lsof -i :8888
   # or
   sudo netstat -tulpn | grep 8888
   ```

2. **Check Streamlit installation:**
   ```bash
   which streamlit
   streamlit --version
   ```

3. **Check logs:**
   - Systemd: `sudo journalctl -u meme-annotation.service -f`
   - Nohup: `tail -f memes-annotation/streamlit.log`

### Permission Issues

```bash
# Ensure correct ownership
sudo chown -R your_username:your_username /home/stefano/memes/semantic-memes/memes-annotation

# Ensure scripts are executable
chmod +x memes-annotation/*.sh
```

### Images/Dimensions Not Loading

1. **Verify paths:**
   - Images: `../img/` should exist relative to `memes-annotation/`
   - Dimensions: `../output_reversed/` should exist

2. **Check file permissions:**
   ```bash
   ls -la ../img/
   ls -la ../output_reversed/
   ```

3. **Check logs in browser console** (F12) for JavaScript errors

### Connection Refused

1. **Check if service is running:**
   ```bash
   ps aux | grep streamlit
   ```

2. **Check firewall:**
   ```bash
   sudo ufw status
   ```

3. **Verify address binding:**
   - Service should bind to `0.0.0.0`, not `127.0.0.1`
   - Check `.streamlit/config.toml` or command line arguments

## Monitoring

### Check Service Status

```bash
# Systemd
sudo systemctl status meme-annotation.service

# Process
ps aux | grep streamlit

# Port
netstat -tulpn | grep 8888
```

### View Logs

```bash
# Systemd
sudo journalctl -u meme-annotation.service -f

# Nohup
tail -f memes-annotation/streamlit.log

# Screen/Tmux
# Attach to session and view output
```

## Security Considerations

1. **Firewall**: Only open necessary ports
2. **Authentication**: Consider adding authentication if exposing publicly
3. **HTTPS**: Use reverse proxy with SSL for production
4. **Access Control**: Consider IP whitelisting if only internal access needed

## Updating the Service

1. **Stop the service:**
   ```bash
   sudo systemctl stop meme-annotation.service
   # or
   pkill -f "streamlit.*app.py"
   ```

2. **Update code/files**

3. **Restart the service:**
   ```bash
   sudo systemctl start meme-annotation.service
   # or
   ./deploy.sh
   ```

## Summary

The easiest way to set up a permanent service:

1. **For quick setup**: Use `./deploy.sh` as regular user (nohup method)
2. **For production**: Use systemd service (Option 1)
3. **For development**: Use `./start.sh` or run directly

The service will be accessible at `http://YOUR_SERVER_IP:8888` once running and firewall is configured.






