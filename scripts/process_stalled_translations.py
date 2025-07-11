#!/usr/bin/env python3
import re
import os
from datetime import datetime, timedelta
import subprocess

def parse_timestamp(timestamp_str):
    """Parse timestamp from format YYYYMMDD-HHMM"""
    return datetime.strptime(timestamp_str, "%Y%m%d-%H%M")

def is_older_than_1_hour(timestamp_str, current_time):
    """Check if timestamp is older than 1 hour"""
    file_time = parse_timestamp(timestamp_str)
    return (current_time - file_time) > timedelta(hours=1)

def check_vi_file_exists(source_path):
    """Check if Vietnamese translation file exists"""
    if source_path.endswith('.txt'):
        vi_path = source_path[:-4] + '_vi.txt'
        return os.path.exists(vi_path), vi_path
    return False, None

def check_translation_completeness(vi_path):
    """Check if Vietnamese translation file has reasonable completeness"""
    try:
        # Read both English and Vietnamese files
        en_path = vi_path.replace('_vi.txt', '.txt')
        
        if not os.path.exists(en_path):
            print(f"    English file not found: {en_path}")
            return 0.0
            
        if not os.path.exists(vi_path):
            print(f"    Vietnamese file not found: {vi_path}")
            return 0.0
        
        # Count tokens in both files
        with open(en_path, 'r', encoding='utf-8', errors='ignore') as f:
            en_content = f.read()
        with open(vi_path, 'r', encoding='utf-8', errors='ignore') as f:
            vi_content = f.read()
        
        en_tokens = len(en_content.split())
        vi_tokens = len(vi_content.split())
        
        if en_tokens == 0:
            return 0.0
            
        ratio = vi_tokens / en_tokens
        print(f"    EN tokens: {en_tokens}, VI tokens: {vi_tokens}, Ratio: {ratio:.3f}")
        return ratio
        
    except Exception as e:
        print(f"    Error checking completeness for {vi_path}: {e}")
        return 0.0

def main():
    current_time = datetime.now()
    print(f"Current time: {current_time.strftime('%Y%m%d-%H%M')}")
    
    # Read translation queue
    with open('translation_queue.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    processing_pattern = r'^\[Processing\]\s+(\d{8}-\d{4})\s+(.+)$'
    processed_count = 0
    removed_count = 0
    
    # Process modifications in reverse order to maintain indices
    lines_to_modify_stalled = []  # (index, new_line) for stalled entries
    lines_to_remove_completed = []  # indices for completed entries
    
    for i, line in enumerate(lines):
        match = re.match(processing_pattern, line.strip())
        if match:
            timestamp, file_path = match.groups()
            processed_count += 1
            
            print(f"\nProcessing entry {processed_count}: {timestamp} - {file_path}")
            
            if is_older_than_1_hour(timestamp, current_time):
                print(f"  -> Older than 1 hour")
                
                vi_exists, vi_path = check_vi_file_exists(file_path)
                if vi_exists:
                    print(f"  -> Vietnamese file exists: {vi_path}")
                    score = check_translation_completeness(vi_path)
                    print(f"  -> Completeness score: {score}")
                    
                    if score > 0.4:
                        print(f"  -> Score > 0.4, removing completely (completed)")
                        lines_to_remove_completed.append(i)
                        removed_count += 1
                    else:
                        print(f"  -> Score <= 0.4, keeping in queue")
                else:
                    print(f"  -> No Vietnamese file found, removing processing status (stalled)")
                    # Remove processing status but keep file path
                    new_line = file_path + '\n'
                    lines_to_modify_stalled.append((i, new_line))
                    removed_count += 1
            else:
                print(f"  -> Less than 1 hour old, keeping")
    
    # Apply modifications in reverse order to maintain indices
    if lines_to_remove_completed or lines_to_modify_stalled:
        print(f"\nProcessing {len(lines_to_remove_completed)} completed and {len(lines_to_modify_stalled)} stalled entries...")
        
        # Remove completed entries first (in reverse order)
        for i in reversed(lines_to_remove_completed):
            del lines[i]
        
        # Then modify stalled entries (adjust indices for removed lines)
        for i, new_line in reversed(lines_to_modify_stalled):
            # Adjust index for previously removed lines
            adjusted_i = i
            for removed_i in lines_to_remove_completed:
                if removed_i < i:
                    adjusted_i -= 1
            lines[adjusted_i] = new_line
        
        # Write back to file
        with open('translation_queue.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"Successfully processed {removed_count} entries:")
        print(f"  - Completely removed: {len(lines_to_remove_completed)} (completed translations)")
        print(f"  - Status removed: {len(lines_to_modify_stalled)} (stalled, ready for retranslation)")
    else:
        print("\nNo entries to modify")
    
    print(f"\nSummary:")
    print(f"  Total processing entries found: {processed_count}")
    print(f"  Entries removed: {removed_count}")
    print(f"  Entries remaining: {processed_count - removed_count}")

if __name__ == "__main__":
    main()