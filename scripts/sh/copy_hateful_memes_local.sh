#!/bin/bash

# Script to copy 1000 random images from local machine to remote server
# Run this script on your LOCAL machine (Mac)

# Configuration - UPDATE THESE VALUES
SOURCE_DIR="/Users/stefanodegiorgis/Downloads/Hateful Memes data/img"
REMOTE_USER="stefano"
REMOTE_HOST="stlab-disi-delfino"  # Server hostname
REMOTE_PATH="/home/stefano/memes/semantic-memes/img/hateful-memes-img"
NUM_IMAGES=1000

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# Count total images
total_images=$(find "$SOURCE_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.bmp" \) | wc -l | tr -d ' ')

if [ "$total_images" -lt "$NUM_IMAGES" ]; then
    echo "Warning: Only $total_images images found, but $NUM_IMAGES requested."
    echo "Will copy all available images."
    NUM_IMAGES=$total_images
fi

echo "Found $total_images images in source directory"
echo "Selecting $NUM_IMAGES random images..."

# Create a temporary file list
temp_list=$(mktemp)

# Find all images and randomly select NUM_IMAGES
find "$SOURCE_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.bmp" \) | shuf -n "$NUM_IMAGES" > "$temp_list"

echo "Copying $NUM_IMAGES images to remote server..."

# Use rsync to copy files (more efficient than scp for multiple files)
# rsync will preserve file structure and show progress
rsync -avz --files-from="$temp_list" --no-relative "$SOURCE_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

# Alternative: If rsync doesn't work, you can use scp in a loop (slower)
# while IFS= read -r file; do
#     relative_path="${file#$SOURCE_DIR/}"
#     scp "$file" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"
# done < "$temp_list"

# Clean up
rm "$temp_list"

echo "Done! Copied $NUM_IMAGES images to $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"

