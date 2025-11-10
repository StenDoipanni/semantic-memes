# 🖥️ Meme Pipeline Server Setup Guide

This guide will help you deploy the meme analysis pipeline to your server with local small language models.

## 📋 Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8+
- At least 8GB RAM (16GB recommended for larger models)
- 20GB+ free disk space
- SSH access to the server

## 🚀 Deployment Steps

### Step 1: Prepare Local Machine

```bash
# Navigate to the pipeline directory
cd /path/to/meme-pipeline-server

# Make deployment script executable
chmod +x deploy_to_server.sh

# Run deployment (replace with your server details)
./deploy_to_server.sh ubuntu your-server.com
```

### Step 2: Server Setup

#### 2.1 Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install curl for Ollama
sudo apt install curl -y
```

#### 2.2 Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
sudo systemctl start ollama
sudo systemctl enable ollama

# Verify installation
ollama --version
```

#### 2.3 Pull Required Models

```bash
# Pull recommended models (choose based on your server capacity)
ollama pull llama3.2:latest      # ~4GB - Recommended
ollama pull llama3.1:latest       # ~4GB - Alternative
ollama pull mistral:latest        # ~4GB - Alternative
ollama pull phi3:latest          # ~2GB - Lightweight option

# List available models
ollama list
```

#### 2.4 Copy Required Files

```bash
# Copy memes-features folder to server
scp -r /path/to/memes-features/ ubuntu@your-server.com:/opt/meme-pipeline/

# Verify files are in place
ssh ubuntu@your-server.com "ls -la /opt/meme-pipeline/"
```

### Step 3: Test the Pipeline

#### 3.1 Basic Test

```bash
# SSH into server
ssh ubuntu@your-server.com

# Navigate to pipeline directory
cd /opt/meme-pipeline

# Test with a sample image
./run_server_pipeline.sh --image /path/to/test-image.jpg --mode Core --model llama3.2:latest
```

#### 3.2 Verify Output

```bash
# Check output files
ls -la output/
ls -la output/dimensions/
ls -la output/qa/
```

## 🔧 Configuration Options

### Available Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llama3.2:latest` | ~4GB | Fast | High | **Recommended** |
| `llama3.1:latest` | ~4GB | Fast | High | Alternative |
| `mistral:latest` | ~4GB | Fast | High | Alternative |
| `phi3:latest` | ~2GB | Very Fast | Good | Lightweight |
| `codellama:latest` | ~4GB | Fast | High | Code-focused |

### Dimension Sets

#### Core Dimensions (4)
```bash
./run_server_pipeline.sh --image meme.jpg --mode Core
```
- TextualMaterial
- VisualMaterial  
- SceneUnderstanding
- BackgroundKnowledge

#### All Dimensions (13)
```bash
./run_server_pipeline.sh --image meme.jpg --mode All
```
- All Core dimensions plus:
- EmotionExpression, ColorComposition, Metadata
- MetaphoricalAndAnalogicalMapping, OverallIntent
- SemioticInterpretation, TargetCommunity
- TemplateStructure, ToxicityAssessment

#### Custom Dimensions
```bash
./run_server_pipeline.sh --image meme.jpg --dimensions "TextualMaterial VisualMaterial"
```

## 📊 Performance Optimization

### Server Resources

| Task | RAM Usage | Processing Time |
|------|-----------|----------------|
| Core (4 dims) | 2-4GB | 2-5 minutes |
| All (13 dims) | 4-8GB | 5-15 minutes |
| Q&A Generation | +1-2GB | +2-5 minutes |

### Optimization Tips

1. **Use SSD storage** for faster model loading
2. **Allocate sufficient RAM** (8GB+ recommended)
3. **Use faster models** (llama3.2, mistral) for better performance
4. **Process images in batches** for efficiency
5. **Monitor system resources** during processing

## 🔍 Troubleshooting

### Common Issues

#### Ollama Service Not Running
```bash
sudo systemctl status ollama
sudo systemctl start ollama
```

#### Model Not Found
```bash
ollama list
ollama pull llama3.2:latest
```

#### Permission Issues
```bash
sudo chown -R ubuntu:ubuntu /opt/meme-pipeline/
chmod +x /opt/meme-pipeline/*.sh
```

#### Memory Issues
```bash
# Check available memory
free -h
# Use smaller model
./run_server_pipeline.sh --image meme.jpg --model phi3:latest
```

### Logs and Debugging

```bash
# Check pipeline logs
tail -f /opt/meme-pipeline/output/*.log

# Test individual components
cd /opt/meme-pipeline
python3 test_pipeline.py

# Check Ollama logs
journalctl -u ollama -f
```

## 🚀 Production Deployment

### Systemd Service (Optional)

Create a systemd service for automated processing:

```bash
sudo nano /etc/systemd/system/meme-pipeline.service
```

```ini
[Unit]
Description=Meme Analysis Pipeline
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/meme-pipeline
ExecStart=/opt/meme-pipeline/run_server_pipeline.sh --image %i --mode Core
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Monitoring

```bash
# Monitor system resources
htop
# Monitor Ollama
ollama ps
# Check disk usage
df -h
```

## 📞 Support

If you encounter issues:

1. Check the logs in `/opt/meme-pipeline/output/`
2. Verify Ollama is running: `ollama list`
3. Test with a simple image first
4. Use Core mode before trying All mode
5. Monitor system resources during processing

## 🎉 Success!

Once everything is working, you should see:
- ✅ Dimension extraction completing successfully
- ✅ TTL files being generated
- ✅ Q&A pairs being created
- ✅ All output files in the correct directories

Your server is now ready for meme analysis with local LLMs! 🚀

