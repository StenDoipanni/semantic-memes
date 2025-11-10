# GitHub Setup Guide

This guide will help you push your Meme Analysis Pipeline to GitHub.

## ⚠️ Important Security Notice

**Before pushing to GitHub, you should remove hardcoded API keys from the following files:**

- `scripts/sh/activate_env.sh`
- `scripts/sh/run_meme_pipeline.sh`
- `scripts/sh/run_dimension_extraction.sh`
- `scripts/sh/run_qa_generation.sh`
- `scripts/sh/test_ollama_local.sh`
- `scripts/py/run_qa_from_ttl.py`

These files currently contain hardcoded API keys. Replace them with environment variable references (e.g., `$CLAUDE_API_KEY` or `os.getenv("CLAUDE_API_KEY")`).

## Step 1: Create a GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Choose a repository name (e.g., `meme-analysis-pipeline`)
5. **Do NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Add GitHub Remote

After creating the repository, GitHub will show you commands. Use the HTTPS or SSH URL:

```bash
cd /home/sdegiorgis/memes/meme-pipeline-server

# For HTTPS (recommended for first-time setup)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# OR for SSH (if you have SSH keys set up)
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name.

## Step 3: Verify Remote

```bash
git remote -v
```

You should see your repository URL listed.

## Step 4: Push to GitHub

```bash
# Rename branch to 'main' (GitHub's default)
git branch -M main

# Push to GitHub
git push -u origin main
```

If you're using HTTPS, GitHub will prompt you for credentials. You may need to:
- Use a Personal Access Token instead of your password
- Or set up SSH keys for easier authentication

## Step 5: Verify on GitHub

1. Go to your repository on GitHub
2. You should see all your files
3. Check that `.gitignore` is working (logs, output, etc. should not be visible)

## Optional: Configure Git User (if not already done)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Future Updates

After making changes to your code:

```bash
# Stage changes
git add .

# Commit changes
git commit -m "Description of your changes"

# Push to GitHub
git push
```

## Troubleshooting

### Authentication Issues

If you have trouble pushing:
- **HTTPS**: Use a Personal Access Token (Settings → Developer settings → Personal access tokens)
- **SSH**: Set up SSH keys (Settings → SSH and GPG keys)

### Branch Name Conflicts

If GitHub uses `main` and you have `master`:
```bash
git branch -M main
git push -u origin main
```

### Large Files

If you have large image files, consider:
- Using Git LFS (Large File Storage)
- Or excluding them from the repository (add to `.gitignore`)

