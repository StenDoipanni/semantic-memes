#!/usr/bin/env python3
"""
Script to further optimize panda-rosso-general_small_text.png to reduce file size
"""

from PIL import Image
import os

def optimize_image():
    input_file = "panda-rosso-general_small_text.png"
    output_file = "panda-rosso-general_small_text_optimized.png"
    
    try:
        # Open the image
        with Image.open(input_file) as img:
            print(f"Original image size: {img.size}")
            print(f"Original mode: {img.mode}")
            
            # Convert RGBA to RGB if needed (remove alpha channel)
            if img.mode == 'RGBA':
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                img = background
                print("Converted RGBA to RGB")
            
            # Further reduce dimensions if needed (make it even smaller)
            # Target: around 500x750 to get closer to the JPG file size
            target_width = 500
            target_height = 750
            
            resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Save with optimization
            resized_img.save(output_file, "PNG", optimize=True, compress_level=9)
            
            # Get file sizes
            original_size = os.path.getsize(input_file)
            new_size = os.path.getsize(output_file)
            
            print(f"Optimized image size: {resized_img.size}")
            print(f"Original file size: {original_size:,} bytes ({original_size/1024/1024:.2f} MB)")
            print(f"New file size: {new_size:,} bytes ({new_size/1024/1024:.2f} MB)")
            print(f"Size reduction: {((original_size - new_size) / original_size * 100):.1f}%")
            print(f"Optimized image saved as: {output_file}")
            
            # Also create a JPEG version for comparison
            jpeg_file = "panda-rosso-general_small_text_optimized.jpg"
            resized_img.save(jpeg_file, "JPEG", quality=85, optimize=True)
            jpeg_size = os.path.getsize(jpeg_file)
            print(f"JPEG version size: {jpeg_size:,} bytes ({jpeg_size/1024/1024:.2f} MB)")
            print(f"JPEG file saved as: {jpeg_file}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    optimize_image()