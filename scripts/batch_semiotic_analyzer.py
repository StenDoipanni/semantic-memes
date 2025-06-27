#!/usr/bin/env python3
"""
Batch Image Analysis Script
Processes multiple images using structured semiotic analysis.
Creates organized folders for each image analysis.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from advanced_semiotic_analyzer import analyze_image, create_analysis_folder, save_analysis_files, load_json_schema
import time

def load_batch_config(config_path):
    """Load batch configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        return None

def process_batch(config_path):
    """Process a batch of images according to configuration."""
    
    # Load configuration
    config = load_batch_config(config_path)
    if not config:
        return
    
    # Load schema
    schema = load_json_schema(config['schema_path'])
    if not schema:
        return
    
    # Create output directory
    output_dir = Path(config['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize batch results
    batch_results = {
        'metadata': {
            'config_path': str(config_path),
            'processed_at': datetime.now().isoformat(),
            'total_images': len(config['images']),
            'successful_analyses': 0,
            'failed_analyses': 0
        },
        'results': []
    }
    
    print(f"🚀 Starting batch analysis of {len(config['images'])} images...")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 50)
    
    total_start_time = time.time()
    
    for i, image_config in enumerate(config['images'], 1):
        image_path = image_config['image_path']
        fact_statement = image_config['fact_statement']
        
        print(f"\n📸 Processing image {i}/{len(config['images'])}: {image_path}")
        print(f"💭 Fact statement: {fact_statement}")
        
        image_start_time = time.time()
        
        try:
            # Analyze image
            result, raw_response, prompt = analyze_image(
                image_path=image_path,
                fact_statement=fact_statement,
                schema_path=config['schema_path'],
                prompt_path=config['prompt_path']
            )
            
            image_end_time = time.time()
            image_analysis_time = image_end_time - image_start_time
            
            if result:
                # Save individual result
                output_filename = f"analysis_{i:03d}_{Path(image_path).stem}.json"
                output_path = output_dir / output_filename
                
                # Add timing information to result
                result['metadata'] = {
                    'image_path': image_path,
                    'fact_statement': fact_statement,
                    'analysis_time_seconds': round(image_analysis_time, 2),
                    'processed_at': datetime.now().isoformat()
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                # Add to batch results
                batch_results['results'].append({
                    'image_path': image_path,
                    'fact_statement': fact_statement,
                    'output_file': str(output_path),
                    'analysis_time_seconds': round(image_analysis_time, 2),
                    'status': 'success'
                })
                
                batch_results['metadata']['successful_analyses'] += 1
                
                print(f"✅ Analysis completed in {image_analysis_time:.2f}s")
                print(f"💾 Saved to: {output_path}")
                
            else:
                print(f"❌ Analysis failed")
                batch_results['results'].append({
                    'image_path': image_path,
                    'fact_statement': fact_statement,
                    'analysis_time_seconds': round(image_analysis_time, 2),
                    'status': 'failed',
                    'error': 'Analysis returned no result'
                })
                batch_results['metadata']['failed_analyses'] += 1
                
        except Exception as e:
            image_end_time = time.time()
            image_analysis_time = image_end_time - image_start_time
            
            print(f"❌ Analysis failed with error: {e}")
            batch_results['results'].append({
                'image_path': image_path,
                'fact_statement': fact_statement,
                'analysis_time_seconds': round(image_analysis_time, 2),
                'status': 'failed',
                'error': str(e)
            })
            batch_results['metadata']['failed_analyses'] += 1
    
    total_end_time = time.time()
    total_analysis_time = total_end_time - total_start_time
    
    # Add timing to batch metadata
    batch_results['metadata']['total_analysis_time_seconds'] = round(total_analysis_time, 2)
    batch_results['metadata']['average_time_per_image'] = round(total_analysis_time / len(config['images']), 2)
    
    # Save batch summary
    summary_path = output_dir / 'batch_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(batch_results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 50)
    print("📊 BATCH PROCESSING COMPLETE")
    print(f"⏱️  Total time: {total_analysis_time:.2f} seconds")
    print(f"📈 Average time per image: {total_analysis_time / len(config['images']):.2f} seconds")
    print(f"✅ Successful analyses: {batch_results['metadata']['successful_analyses']}")
    print(f"❌ Failed analyses: {batch_results['metadata']['failed_analyses']}")
    print(f"📁 Batch summary saved to: {summary_path}")
    
    # Print timing breakdown
    print("\n📋 Timing breakdown:")
    for result in batch_results['results']:
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"  {status_icon} {Path(result['image_path']).name}: {result['analysis_time_seconds']}s")

def main():
    if len(sys.argv) != 2:
        print("Usage: python batch_semiotic_analyzer.py <config_file>")
        print("Example: python batch_semiotic_analyzer.py batch_config.json")
        print("\nConfig file should contain:")
        print("- images: list of image configurations")
        print("- default_fact_statement: default fact statement for images")
        print("- schema_path: path to JSON schema (optional)")
        print("- prompt_path: path to prompt template (optional)")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Process batch
    process_batch(config_path)

if __name__ == "__main__":
    main() 