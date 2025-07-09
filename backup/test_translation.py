#!/usr/bin/env python3
"""
Test script to understand translation issues.
"""
import subprocess
import sys
from pathlib import Path

def test_translation():
    # Test file
    test_file = "coding/2401.08500-Code_Generation_with_AlphaCodium-_From_Prompt_Engineering_to_Flow.txt"
    
    if not Path(test_file).exists():
        print(f"Test file not found: {test_file}")
        return False
    
    # Read content
    content = Path(test_file).read_text(encoding='utf-8')
    print(f"File content length: {len(content)} characters")
    
    # Build translation prompt - use only first 500 chars for testing
    test_content = content[200:700]  # Skip header comments
    prompt = f"""Translate the following text to Vietnamese:

{test_content}

Vietnamese translation:"""
    
    print(f"Prompt length: {len(prompt)} characters")
    
    # Test with Claude CLI
    try:
        result = subprocess.run(
            ["claude", "--print", "--dangerously-skip-permissions", "--model", "sonnet"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Stdout length: {len(result.stdout)} characters")
        print(f"Stderr: {result.stderr}")
        print(f"First 500 chars of output: {result.stdout[:500]}")
        
        return result.returncode == 0 and len(result.stdout.strip()) > 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_translation()
    sys.exit(0 if success else 1)