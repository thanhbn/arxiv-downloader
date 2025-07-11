#!/usr/bin/env python3
"""
Check Vietnamese translation files for common translation errors and suggest deletions.
"""

import os
import glob
from pathlib import Path

def check_translation_quality(file_path):
    """Check if a Vietnamese translation file has quality issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Common indicators of bad translations
        bad_indicators = [
            "Claude configuration file",
            "corrupted",
            "Unexpected end of JSON input",
            "Error:",
            "Execution error",
            "Tôi đã dịch toàn bộ",  # Summary instead of translation
            "Đây là một bài báo",   # Summary instead of translation
            "configuration file",
            "The corrupted file has been back",
            "stderr:",
            "return code",
            "subprocess.run",
            "traceback",
            "exception",
            "failed to",
            "timeout"
        ]
        
        # Check content length (too short = likely error)
        if len(content.strip()) < 100:
            return "TOO_SHORT", f"Content too short: {len(content)} chars"
        
        # Check for error indicators
        for indicator in bad_indicators:
            if indicator.lower() in content.lower():
                return "ERROR_CONTENT", f"Contains error indicator: '{indicator}'"
        
        # Check if it's just English (not translated)
        vietnamese_chars = 'àáâãèéêìíòóôõùúûụủũýỹ'
        has_vietnamese = any(char in content.lower() for char in vietnamese_chars)
        
        # If it's long but has no Vietnamese characters, it might be untranslated
        if len(content) > 1000 and not has_vietnamese:
            # Check ratio of English words to total
            words = content.split()
            english_words = ['the', 'and', 'of', 'to', 'a', 'in', 'for', 'is', 'on', 'that', 'by', 'this', 'with', 'from', 'are', 'as', 'be', 'or', 'an', 'can', 'we', 'our', 'model', 'data', 'results', 'paper', 'method', 'approach', 'figure', 'table']
            english_count = sum(1 for word in words[:100] if word.lower().strip('.,()[]') in english_words)
            if english_count > 20:  # More than 20% are common English words
                return "NOT_TRANSLATED", f"Appears to be English, not Vietnamese. English words: {english_count}/100"
        
        return "GOOD", f"Appears to be a valid translation ({len(content)} chars)"
        
    except Exception as e:
        return "READ_ERROR", f"Error reading file: {e}"

def main():
    print("Checking Vietnamese translation files for quality issues...\n")
    
    # Find all _vi.txt files
    vi_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('_vi.txt'):
                vi_files.append(os.path.join(root, file))
    
    print(f"Found {len(vi_files)} Vietnamese translation files\n")
    
    bad_files = []
    good_files = []
    
    for file_path in sorted(vi_files):
        status, reason = check_translation_quality(file_path)
        
        if status == "GOOD":
            good_files.append(file_path)
            print(f"✓ GOOD: {file_path}")
        else:
            bad_files.append((file_path, status, reason))
            print(f"✗ {status}: {file_path}")
            print(f"  Reason: {reason}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Good translations: {len(good_files)}")
    print(f"Bad translations: {len(bad_files)}")
    
    if bad_files:
        print(f"\n=== BAD FILES TO DELETE ===")
        for file_path, status, reason in bad_files:
            print(f"rm \"{file_path}\"  # {status}: {reason}")
        
        print(f"\n=== DELETE COMMAND ===")
        print("# Copy and paste this command to delete all bad translation files:")
        for file_path, status, reason in bad_files:
            print(f"rm \"{file_path}\"")
    
    # Check for corresponding original files that need re-translation
    print(f"\n=== FILES NEEDING RE-TRANSLATION ===")
    for file_path, status, reason in bad_files:
        # Find corresponding original file
        if file_path.endswith('_vi.txt'):
            original = file_path[:-7] + '.txt'  # Remove '_vi.txt', add '.txt'
            if os.path.exists(original):
                print(f"echo \"{original}\" >> translation_queue.txt  # Re-add to queue")

if __name__ == "__main__":
    main()