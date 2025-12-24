# Meme Annotation Service

A Streamlit-based web service for viewing and annotating meme analysis results.

## Features

- 📸 View meme images from the `img/` folder
- 📊 Display extracted dimensions from `output_reversed/`
- ✏️ Add and save annotations for each dimension
- 🔍 Filter dimensions by type
- 📋 View metadata and raw JSON-LD data

## Installation

1. Install dependencies:
```bash
cd memes-annotation
pip install -r requirements.txt
```

2. Ensure the project structure is correct:
- `../img/` - Contains meme images
- `../output_reversed/` - Contains extracted dimensions

## Running the Service

### Development Mode

```bash
streamlit run app.py
```

The service will be available at `http://localhost:8888`

### Production Mode (Permanent Service)

See the deployment section below for setting up a permanent service.

## Deployment as Permanent Service

### Option 1: Using systemd (Recommended for Linux)

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/meme-annotation.service
```

2. Add the following content (adjust paths and user as needed):

```ini
[Unit]
Description=Meme Annotation Streamlit Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/stefano/memes/semantic-memes/memes-annotation
Environment="PATH=/home/stefano/memes/semantic-memes/venv/bin"
ExecStart=/home/stefano/memes/semantic-memes/venv/bin/streamlit run app.py --server.port=8888 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable meme-annotation.service
sudo systemctl start meme-annotation.service
```

4. Check status:

```bash
sudo systemctl status meme-annotation.service
```

### Option 2: Using nohup (Simple)

```bash
cd /home/stefano/memes/semantic-memes/memes-annotation
nohup streamlit run app.py --server.port=8888 --server.address=0.0.0.0 > streamlit.log 2>&1 &
```

### Option 3: Using screen/tmux

```bash
# Using screen
screen -S meme-annotation
cd /home/stefano/memes/semantic-memes/memes-annotation
streamlit run app.py --server.port=8888 --server.address=0.0.0.0
# Press Ctrl+A then D to detach

# To reattach later:
screen -r meme-annotation
```

## Accessing from Web

Once the service is running:

1. **Local access**: `http://localhost:8888`
2. **Network access**: `http://YOUR_SERVER_IP:8888`

### Firewall Configuration

If accessing from outside the server, ensure port 8888 is open:

```bash
# Ubuntu/Debian
sudo ufw allow 8888/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --reload
```

### Reverse Proxy (Optional)

For production, consider using nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Directory Structure

```
memes-annotation/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .streamlit/
│   └── config.toml      # Streamlit configuration
├── utils/
│   ├── __init__.py
│   ├── data_loader.py   # Data loading utilities
│   └── annotation_manager.py  # Annotation management
└── annotations/         # User annotations (created automatically)
```

## Usage

1. **Select a Meme**: Choose a meme from the sidebar dropdown
2. **View Dimensions**: Browse through extracted dimensions organized by type
3. **Add Annotations**: Use the annotation text area to add notes for each dimension
4. **Save Annotations**: Click "Save Annotation" to persist your notes
5. **Filter Dimensions**: Use the sidebar to filter which dimension types are displayed

## Troubleshooting

### Service won't start
- Check that port 8888 is not already in use: `lsof -i :8888`
- Verify Python and Streamlit are installed correctly
- Check logs: `journalctl -u meme-annotation.service -f` (for systemd)

### Images not showing
- Verify images exist in `../img/` directory
- Check file permissions
- Ensure image file extensions are supported (.png, .jpg, .jpeg, .webp)

### Dimensions not loading
- Verify `../output_reversed/` directory exists
- Check JSON-LD files are valid JSON
- Review browser console for errors

## License

Same as parent project.






