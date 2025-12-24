#!/usr/bin/env python3
"""
Script to copy 1000 random images from local machine to remote server.
Run this script on your LOCAL machine (Mac).

Usage:
    python3 copy_hateful_memes_local.py
"""

import os
import random
import subprocess
import sys
from pathlib import Path

# Configuration - UPDATE THESE VALUES
SOURCE_DIR = "/Users/stefanodegiorgis/Downloads/Hateful Memes data/img"
REMOTE_USER = "stefano"
REMOTE_HOST = "stlab-disi-delfino"  # Server hostname
REMOTE_PATH = "/home/stefano/memes/semantic-memes/img/hateful-memes-img"
NUM_IMAGES = 1000

# Image extensions to look for
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

def find_images(directory):
    """Find all image files in the directory."""
    images = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in IMAGE_EXTENSIONS:
                images.append(os.path.join(root, file))
    return images

def main():
    # Check if source directory exists
    if not os.path.isdir(SOURCE_DIR):
        print(f"Error: Source directory does not exist: {SOURCE_DIR}")
        sys.exit(1)
    
    print(f"Scanning for images in: {SOURCE_DIR}")
    all_images = find_images(SOURCE_DIR)
    
    if not all_images:
        print("Error: No images found in source directory")
        sys.exit(1)
    
    total_images = len(all_images)
    print(f"Found {total_images} images")
    
    # Select random images
    num_to_copy = min(NUM_IMAGES, total_images)
    if total_images < NUM_IMAGES:
        print(f"Warning: Only {total_images} images found, but {NUM_IMAGES} requested.")
        print(f"Will copy all available images.")
    
    selected_images = random.sample(all_images, num_to_copy)
    print(f"Selected {num_to_copy} random images")
    
    # Copy files using rsync
    print(f"Copying to {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}...")
    
    # Create a file list for rsync
    temp_list = "/tmp/rsync_file_list.txt"
    with open(temp_list, 'w') as f:
        for img_path in selected_images:
            # Get relative path from source directory
            rel_path = os.path.relpath(img_path, SOURCE_DIR)
            f.write(f"{rel_path}\n")
    
    # Use rsync to copy files
    rsync_cmd = [
        'rsync',
        '-avz',
        '--files-from', temp_list,
        '--no-relative',
        f"{SOURCE_DIR}/",
        f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}/"
    ]
    
    try:
        subprocess.run(rsync_cmd, check=True)
        print(f"Successfully copied {num_to_copy} images!")
    except subprocess.CalledProcessError as e:
        print(f"Error during rsync: {e}")
        print("\nAlternative: You can also use scp manually:")
        print(f"  scp {' '.join(selected_images[:5])} {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}/")
        sys.exit(1)
    finally:
        # Clean up temp file
        if os.path.exists(temp_list):
            os.remove(temp_list)

if __name__ == "__main__":
    main()

