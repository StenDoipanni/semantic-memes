#!/usr/bin/env python3
"""
Script to randomly select images from a source directory and copy them to destination.
Run this script ON THE SERVER.

This is useful when you've already copied images to the server via any method,
and you want to randomly select a subset.

Usage:
    python3 select_random_images_server.py <source_dir> <dest_dir> <num_images>
    
Example:
    python3 select_random_images_server.py /tmp/all_hateful_images /home/stefano/memes/semantic-memes/img/hateful-memes-img 1000
"""

import os
import random
import shutil
import sys
from pathlib import Path

# Image extensions to look for
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

def find_images(directory):
    """Find all image files in the directory."""
    images = []
    if not os.path.isdir(directory):
        print(f"Error: Source directory does not exist: {directory}")
        return images
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in IMAGE_EXTENSIONS:
                images.append(os.path.join(root, file))
    return images

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 select_random_images_server.py <source_dir> <dest_dir> <num_images>")
        print("\nExample:")
        print("  python3 select_random_images_server.py /tmp/all_hateful_images /home/stefano/memes/semantic-memes/img/hateful-memes-img 1000")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    dest_dir = sys.argv[2]
    num_images = int(sys.argv[3])
    
    # Check if source directory exists
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Create destination directory if it doesn't exist
    os.makedirs(dest_dir, exist_ok=True)
    
    print(f"Scanning for images in: {source_dir}")
    all_images = find_images(source_dir)
    
    if not all_images:
        print("Error: No images found in source directory")
        sys.exit(1)
    
    total_images = len(all_images)
    print(f"Found {total_images} images")
    
    # Select random images
    num_to_copy = min(num_images, total_images)
    if total_images < num_images:
        print(f"Warning: Only {total_images} images found, but {num_images} requested.")
        print(f"Will copy all available images.")
    
    selected_images = random.sample(all_images, num_to_copy)
    print(f"Selected {num_to_copy} random images")
    print(f"Copying to: {dest_dir}")
    
    # Copy files
    copied = 0
    for img_path in selected_images:
        try:
            # Get just the filename (not full path)
            filename = os.path.basename(img_path)
            dest_path = os.path.join(dest_dir, filename)
            
            # Handle duplicate filenames by adding a number
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                    counter += 1
            
            shutil.copy2(img_path, dest_path)
            copied += 1
            
            if copied % 100 == 0:
                print(f"Copied {copied}/{num_to_copy} images...")
        except Exception as e:
            print(f"Error copying {img_path}: {e}")
    
    print(f"Successfully copied {copied} images to {dest_dir}")

if __name__ == "__main__":
    main()

