#!/usr/bin/env python3
"""
Remove Big Papers from Translation Queue

This script removes papers listed in translation_queue_big_file.txt from translation_queue.txt.
It handles files with processing timestamps and extracts clean paths for matching.
"""

import os
import re
import argparse
from pathlib import Path
from typing import Set, List


def extract_clean_path(line: str) -> str:
    """Extract clean file path from a line that might have processing timestamps."""
    line = line.strip()
    if not line or line.startswith('#'):
        return ""
    
    # Remove processing timestamps like "[Processing] 20250708-1025 "
    # Pattern: [Processing] YYYYMMDD-HHMM or [Processing] YYYYMMDD-HHMM YYYYMMDD-HHMM
    pattern = r'^\[Processing\]\s+\d{8}-\d{4}(?:\s+\d{8}-\d{4})?\s+'
    clean_line = re.sub(pattern, '', line)
    
    return clean_line.strip()


def load_big_files(big_file_path: str) -> Set[str]:
    """Load the list of big files to remove."""
    big_files = set()
    
    try:
        with open(big_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                clean_path = extract_clean_path(line)
                if clean_path:
                    big_files.add(clean_path)
    except FileNotFoundError:
        print(f"❌ Big file list not found: {big_file_path}")
        return set()
    except Exception as e:
        print(f"❌ Error reading big file list: {e}")
        return set()
    
    print(f"📋 Loaded {len(big_files)} big files to remove")
    return big_files


def clean_translation_queue(queue_file_path: str, big_files: Set[str], output_file_path: str = None) -> int:
    """Remove big files from translation queue."""
    if not output_file_path:
        output_file_path = queue_file_path + ".cleaned"
    
    removed_count = 0
    kept_lines = []
    
    try:
        with open(queue_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                original_line = line.rstrip('\n\r')
                clean_path = extract_clean_path(line)
                
                if not clean_path or clean_path.startswith('#'):
                    # Keep comments and empty lines
                    kept_lines.append(original_line)
                elif clean_path in big_files:
                    # Remove this file
                    removed_count += 1
                    print(f"🗑️  Removing: {clean_path}")
                else:
                    # Keep this file
                    kept_lines.append(original_line)
        
        # Write cleaned queue
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for line in kept_lines:
                f.write(line + '\n')
        
        print(f"\n✅ Cleaning complete!")
        print(f"📊 Removed {removed_count} big files")
        print(f"📊 Kept {len([l for l in kept_lines if l and not l.startswith('#')])} files")
        print(f"📄 Cleaned queue saved to: {output_file_path}")
        
        return removed_count
        
    except FileNotFoundError:
        print(f"❌ Translation queue not found: {queue_file_path}")
        return 0
    except Exception as e:
        print(f"❌ Error processing translation queue: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Remove big papers from translation queue")
    parser.add_argument("--big-file", type=str, default="translation_queue_big_file.txt",
                       help="File containing list of big papers to remove")
    parser.add_argument("--queue-file", type=str, default="translation_queue.txt",
                       help="Translation queue file to clean")
    parser.add_argument("--output", type=str, 
                       help="Output file (default: queue-file.cleaned)")
    parser.add_argument("--backup", action="store_true",
                       help="Create backup of original queue file")
    parser.add_argument("--replace", action="store_true",
                       help="Replace original queue file with cleaned version")
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.big_file):
        print(f"❌ Big file list not found: {args.big_file}")
        return 1
    
    if not os.path.exists(args.queue_file):
        print(f"❌ Translation queue not found: {args.queue_file}")
        return 1
    
    # Create backup if requested
    if args.backup:
        backup_path = args.queue_file + ".backup"
        try:
            import shutil
            shutil.copy2(args.queue_file, backup_path)
            print(f"📋 Backup created: {backup_path}")
        except Exception as e:
            print(f"⚠️  Failed to create backup: {e}")
    
    # Load big files to remove
    big_files = load_big_files(args.big_file)
    if not big_files:
        print("❌ No big files loaded")
        return 1
    
    # Determine output file
    if args.replace:
        output_file = args.queue_file + ".tmp"
    else:
        output_file = args.output or (args.queue_file + ".cleaned")
    
    # Clean the queue
    removed_count = clean_translation_queue(args.queue_file, big_files, output_file)
    
    # Replace original if requested
    if args.replace and removed_count > 0:
        try:
            os.replace(output_file, args.queue_file)
            print(f"✅ Original queue file updated: {args.queue_file}")
        except Exception as e:
            print(f"❌ Failed to replace original file: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())