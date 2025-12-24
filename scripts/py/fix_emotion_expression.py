#!/usr/bin/env python3
"""
Fix EmotionExpression -> Emotion in TTL files.
Replaces EmotionExpression with Emotion when it appears as a class name in RDF type declarations.
"""

import re
from pathlib import Path
from typing import List

def fix_emotion_expression_in_ttl(ttl_file: Path) -> tuple[bool, int]:
    """
    Fix EmotionExpression -> Emotion in a TTL file.
    
    Args:
        ttl_file: Path to the TTL file
        
    Returns:
        Tuple of (changed: bool, replacements_count: int)
    """
    try:
        with open(ttl_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements = 0
        
        # Pattern 1: rdf:type :EmotionExpression (with or without semicolon/period)
        # Replace :EmotionExpression with :Emotion when it's a type declaration
        pattern1 = r':EmotionExpression([\s;.])'
        matches1 = re.findall(pattern1, content)
        if matches1:
            content = re.sub(pattern1, r':Emotion\1', content)
            replacements += len(matches1)
        
        # Pattern 2: rdfs:subClassOf :EmotionExpression
        pattern2 = r':EmotionExpression([\s;.])'
        # This is already covered by pattern1, but let's be explicit
        # Actually pattern1 should catch all cases
        
        # Pattern 3: In comments or labels that might reference it (optional, but let's be safe)
        # We only want to replace when it's a URI/class reference, not in text
        
        changed = (content != original_content)
        
        if changed:
            with open(ttl_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return changed, replacements
        
    except Exception as e:
        print(f"Error processing {ttl_file}: {e}")
        return False, 0

def main():
    """Main function to fix all TTL files."""
    base_dir = Path("/home/stefano/memes/semantic-memes/output_reversed/hateful-memes-out")
    
    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        return
    
    # Find all refined and enhanced ontology TTL files
    ttl_files = list(base_dir.glob("*_refined_ontology.ttl")) + list(base_dir.glob("*_enhanced_ontology_reversed.ttl"))
    
    print(f"Found {len(ttl_files)} TTL files to process")
    print()
    
    total_changed = 0
    total_replacements = 0
    
    for ttl_file in sorted(ttl_files):
        changed, replacements = fix_emotion_expression_in_ttl(ttl_file)
        
        if changed:
            total_changed += 1
            total_replacements += replacements
            print(f"✅ {ttl_file.name}: {replacements} replacement(s)")
        else:
            if replacements > 0:
                print(f"⚠️  {ttl_file.name}: Found {replacements} but no changes made")
            # Uncomment to see files with no EmotionExpression
            # else:
            #     print(f"   {ttl_file.name}: No EmotionExpression found")
    
    print()
    print(f"Summary:")
    print(f"  Files changed: {total_changed}/{len(ttl_files)}")
    print(f"  Total replacements: {total_replacements}")

if __name__ == "__main__":
    main()

