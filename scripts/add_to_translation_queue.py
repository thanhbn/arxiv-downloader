#!/usr/bin/env python3
"""
Add Files to Translation Queue

Helper script to add .txt files to the translation queue.
Supports adding individual files, directories, or patterns.

Usage:
    python add_to_translation_queue.py [files/patterns/directories...]
    
Examples:
    python add_to_translation_queue.py paper1.txt paper2.txt
    python add_to_translation_queue.py *.txt
    python add_to_translation_queue.py ./papers/
    python add_to_translation_queue.py --recursive ./collections/
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from typing import List, Set
import fcntl

class QueueManager:
    """Manages the translation queue file safely."""
    
    def __init__(self, queue_file: str = "translation_queue.txt"):
        self.queue_file = Path(queue_file)
        self.lock_file = Path(f"{queue_file}.lock")
        
    def _acquire_lock(self):
        """Acquire file lock for safe concurrent access."""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
            return True
        except Exception as e:
            print(f"Failed to acquire lock: {e}")
            return False
            
    def _release_lock(self):
        """Release file lock."""
        try:
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            self.lock_fd.close()
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            print(f"Failed to release lock: {e}")
    
    def get_existing_entries(self) -> Set[str]:
        """Get existing entries in the queue."""
        if not self.queue_file.exists():
            return set()
            
        try:
            lines = self.queue_file.read_text().strip().split('\n')
            entries = set()
            for line in lines:
                line = line.strip()
                if line:
                    # Remove [Processing] prefix if present
                    if line.startswith('[Processing] '):
                        line = line[13:]  # Remove '[Processing] '
                    entries.add(line)
            return entries
        except Exception as e:
            print(f"Error reading queue file: {e}")
            return set()
    
    def add_files(self, files: List[str], skip_existing: bool = True) -> tuple:
        """Add files to the queue. Returns (added_count, skipped_count, failed_count)."""
        if not self._acquire_lock():
            return (0, 0, len(files))
            
        try:
            existing_entries = self.get_existing_entries()
            
            added_files = []
            skipped_files = []
            failed_files = []
            
            for file_path in files:
                # Use relative path to avoid hardcoded absolute paths
                file_path = str(Path(file_path))
                
                # Check if file exists
                if not Path(file_path).exists():
                    print(f"⚠️  File not found: {file_path}")
                    failed_files.append(file_path)
                    continue
                
                # Check if already in queue
                if skip_existing and file_path in existing_entries:
                    print(f"📝 Already in queue: {file_path}")
                    skipped_files.append(file_path)
                    continue
                
                added_files.append(file_path)
            
            # Write to queue file
            if added_files:
                try:
                    with open(self.queue_file, 'a', encoding='utf-8') as f:
                        for file_path in added_files:
                            f.write(f"{file_path}\n")
                            print(f"✅ Added: {file_path}")
                except Exception as e:
                    print(f"Error writing to queue file: {e}")
                    return (0, len(skipped_files), len(files))
            
            return (len(added_files), len(skipped_files), len(failed_files))
            
        finally:
            self._release_lock()

def find_txt_files(path: str, recursive: bool = False) -> List[str]:
    """Find all .txt files in a path."""
    path_obj = Path(path)
    
    if path_obj.is_file():
        if path_obj.suffix == '.txt':
            return [str(path_obj)]
        else:
            print(f"⚠️  Not a .txt file: {path}")
            return []
    
    elif path_obj.is_dir():
        if recursive:
            pattern = "**/*.txt"
        else:
            pattern = "*.txt"
        
        txt_files = list(path_obj.glob(pattern))
        return [str(f) for f in txt_files if f.is_file()]
    
    else:
        # Try as glob pattern
        try:
            matching_files = glob.glob(path)
            return [f for f in matching_files if f.endswith('.txt') and Path(f).is_file()]
        except Exception:
            print(f"⚠️  Invalid path or pattern: {path}")
            return []

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add files to translation queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s paper1.txt paper2.txt          # Add specific files
  %(prog)s *.txt                          # Add all .txt files in current directory
  %(prog)s ./papers/                      # Add all .txt files in papers directory
  %(prog)s --recursive ./collections/    # Add all .txt files recursively
  %(prog)s --force existing.txt           # Add even if already in queue
  %(prog)s --list                         # Just list what would be added
        """
    )
    
    parser.add_argument("paths", nargs="*", 
                       help="Files, directories, or patterns to add")
    parser.add_argument("--queue-file", type=str, default="translation_queue.txt",
                       help="Path to translation queue file (default: translation_queue.txt)")
    parser.add_argument("--recursive", "-r", action="store_true",
                       help="Search directories recursively")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Add files even if already in queue")
    parser.add_argument("--list", "-l", action="store_true",
                       help="Just list files that would be added (dry run)")
    parser.add_argument("--clear", action="store_true",
                       help="Clear the entire queue before adding")
    
    args = parser.parse_args()
    
    # If no paths provided, show help
    if not args.paths and not args.clear:
        parser.print_help()
        sys.exit(1)
    
    queue_manager = QueueManager(args.queue_file)
    
    # Handle clear option
    if args.clear:
        if Path(args.queue_file).exists():
            response = input(f"Are you sure you want to clear the queue file '{args.queue_file}'? (y/N): ")
            if response.lower() == 'y':
                Path(args.queue_file).write_text("")
                print(f"✅ Queue cleared: {args.queue_file}")
            else:
                print("❌ Queue clear cancelled")
        else:
            print(f"ℹ️  Queue file doesn't exist: {args.queue_file}")
        
        if not args.paths:
            sys.exit(0)
    
    # Collect all files
    all_files = []
    for path in args.paths:
        files = find_txt_files(path, args.recursive)
        all_files.extend(files)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in all_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    
    if not unique_files:
        print("❌ No .txt files found")
        sys.exit(1)
    
    print(f"📋 Found {len(unique_files)} .txt files")
    
    # List mode - just show what would be added
    if args.list:
        print("\nFiles that would be added:")
        for i, file_path in enumerate(unique_files, 1):
            print(f"{i:3d}. {file_path}")
        sys.exit(0)
    
    # Add files to queue
    print("\n🔄 Adding files to queue...")
    added, skipped, failed = queue_manager.add_files(
        unique_files, 
        skip_existing=not args.force
    )
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"✅ Added:   {added}")
    print(f"📝 Skipped: {skipped}")
    print(f"❌ Failed:  {failed}")
    print(f"📁 Queue file: {args.queue_file}")
    
    if added > 0:
        print(f"\n🚀 Ready to start translation with:")
        print(f"   python translate_manager.py --queue-file {args.queue_file}")

if __name__ == "__main__":
    main()