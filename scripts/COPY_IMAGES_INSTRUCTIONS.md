# Instructions for Copying Hateful Memes Images

## Problem
The Python script requires SSH access from your local Mac to the server, which may not be configured.

## Solution: Two-Step Process (Recommended)

### Step 1: Transfer all images to server (use any method)

**Option A: If you can SSH manually from terminal:**
```bash
# On your local Mac terminal:
mkdir -p /tmp/all_hateful_images
scp -r "/Users/stefanodegiorgis/Downloads/Hateful Memes data/img"/* stefano@stlab-disi-delfino:/tmp/all_hateful_images/
```

**Option B: Use an SFTP client (FileZilla, Cyberduck, etc.)**
- Connect to: `stefano@stlab-disi-delfino`
- Upload all images from `/Users/stefanodegiorgis/Downloads/Hateful Memes data/img` to `/tmp/all_hateful_images/` on server

**Option C: If you're already connected via SSH in another terminal:**
You can use `scp` from that terminal session.

### Step 2: Randomly select 1000 images on the server

Once all images are on the server, run this command **on the server**:

```bash
python3 /home/stefano/memes/semantic-memes/scripts/py/select_random_images_server.py /tmp/all_hateful_images /home/stefano/memes/semantic-memes/img/hateful-memes-img 1000
```

This will:
- Find all images in `/tmp/all_hateful_images`
- Randomly select 1000 of them
- Copy them to `/home/stefano/memes/semantic-memes/img/hateful-memes-img`

## Alternative: Fix SSH and use original script

If you want to use the original Python script that does everything in one step:

1. Test SSH connection from your Mac:
   ```bash
   ssh stefano@stlab-disi-delfino
   ```

2. If that works, you can use the original script:
   ```bash
   python3 copy_hateful_memes_local.py
   ```

3. If SSH doesn't work, you may need to:
   - Use the server's IP address instead of hostname
   - Connect to VPN if required
   - Set up SSH keys for passwordless access

