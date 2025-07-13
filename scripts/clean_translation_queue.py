#!/usr/bin/env python3
"""
Clean Translation Queue - Remove files that already have Vietnamese translations

This script removes files from translation_queue.txt that already have corresponding
Vietnamese translation files (*_vi.txt).
"""

import os
import re
from pathlib import Path

def extract_arxiv_id(filename: str) -> str:
    """Extract arxiv ID from filename."""
    path = Path(filename)
    filename_only = path.name
    
    # Pattern to match arxiv ID (YYMM.NNNNN)
    match = re.match(r'(\d{4}\.\d{5})', filename_only)
    if match:
        return match.group(1)
    return ""

def has_vietnamese_translation(filename: str) -> bool:
    """Check if file already has a Vietnamese translation."""
    path = Path(filename)
    
    if not path.exists():
        return False
        
    arxiv_id = extract_arxiv_id(filename)
    if not arxiv_id:
        return False
        
    # Check for any file with the pattern: arxiv_id*_vi.txt in the same directory
    parent_dir = path.parent
    vi_pattern = f"{arxiv_id}*_vi.txt"
    vi_files = list(parent_dir.glob(vi_pattern))
    
    return len(vi_files) > 0

def parse_retry_info(line: str) -> tuple:
    """Parse retry count and timestamp from queue line. Returns (filename, retry_count, timestamp)."""
    line = line.strip()
    if line.startswith('[retry:') and ']:' in line:
        # Format: [retry:N:timestamp]:filename or [retry:N]:filename
        try:
            retry_part, filename = line.split(']:', 1)
            retry_info = retry_part.split(':', 1)[1]  # Remove '[retry:'
            
            if ':' in retry_info:
                # Has timestamp: retry:N:timestamp
                retry_count_str, timestamp = retry_info.split(':', 1)
                retry_count = int(retry_count_str)
                return filename.strip(), retry_count, timestamp
            else:
                # No timestamp: retry:N
                retry_count = int(retry_info)
                return filename.strip(), retry_count, None
        except (ValueError, IndexError):
            # Invalid format, treat as retry count 0
            return line, 0, None
    return line, 0, None

def clean_translation_queue():
    """Clean files with existing Vietnamese translations from the queue."""
    queue_file = Path("translation_queue.txt")
    
    if not queue_file.exists():
        print(f"❌ Queue file {queue_file} does not exist")
        return
    
    print("🧹 Cleaning translation queue...")
    
    # Read all lines
    lines = queue_file.read_text().strip().split('\n')
    lines = [line for line in lines if line.strip()]
    
    original_count = len(lines)
    cleaned_lines = []
    removed_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle processing lines
        if line.startswith('[Processing]'):
            parts = line.split(' ', 2)
            if len(parts) >= 3:
                # New format: [Processing] timestamp filename
                raw_filename = parts[2].strip()
            elif len(parts) == 2:
                # Old format: [Processing] filename
                raw_filename = parts[1].strip()
            else:
                # Keep malformed processing lines
                cleaned_lines.append(line)
                continue
            
            # Parse retry info from filename
            filename, retry_count, timestamp = parse_retry_info(raw_filename)
        else:
            # Regular queue line
            filename, retry_count, timestamp = parse_retry_info(line)
        
        # Check if file has Vietnamese translation
        if has_vietnamese_translation(filename):
            print(f"🗑️  Removing {filename} - already has Vietnamese translation")
            removed_count += 1
        else:
            # Keep the file in queue
            cleaned_lines.append(line)
    
    # Write back cleaned queue
    if cleaned_lines:
        queue_file.write_text('\n'.join(cleaned_lines) + '\n')
    else:
        queue_file.write_text('')
    
    print(f"✅ Cleaned translation queue:")
    print(f"   📄 Original entries: {original_count}")
    print(f"   🗑️  Removed entries: {removed_count}")
    print(f"   📄 Remaining entries: {len(cleaned_lines)}")
    
    if removed_count > 0:
        print(f"💾 Updated {queue_file}")

if __name__ == "__main__":
    clean_translation_queue()