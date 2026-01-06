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
import re
from pathlib import Path
from typing import List, Set, Optional
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
    
    def _extract_arxiv_id(self, filename: str) -> Optional[str]:
        """Extract arxiv ID from filename."""
        match = re.search(r'(\d{4}\.\d{4,5})', filename)
        return match.group(1) if match else None

    def _has_vietnamese_translation(self, file_path: str, global_check: bool = False) -> bool:
        """Check if file already has a Vietnamese translation by arxiv ID.

        Args:
            file_path: Path to the file to check
            global_check: If True, search entire repository for translations
        """
        path = Path(file_path)
        arxiv_id = self._extract_arxiv_id(path.name)

        if not arxiv_id:
            return False

        vi_pattern = f"{arxiv_id}*_vi.txt"

        if global_check:
            # Search entire repository from current working directory
            root_dir = Path('.')
            vi_files = list(root_dir.glob(f"**/{vi_pattern}"))
        else:
            # Check only in same directory
            parent_dir = path.parent
            vi_files = list(parent_dir.glob(vi_pattern))

        return len(vi_files) > 0

    def add_files(self, files: List[str], skip_existing: bool = True,
                  ignore_translated: bool = True, global_check: bool = False) -> tuple:
        """Add files to the queue. Returns (added_count, skipped_count, failed_count, translated_count).

        Args:
            files: List of file paths to add
            skip_existing: Skip files already in queue
            ignore_translated: Skip files that have Vietnamese translations
            global_check: Check for translations across entire repository
        """
        if not self._acquire_lock():
            return (0, 0, len(files), 0)

        try:
            existing_entries = self.get_existing_entries()

            added_files = []
            skipped_files = []
            failed_files = []
            translated_files = []

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

                # Check if already has Vietnamese translation
                if ignore_translated and self._has_vietnamese_translation(file_path, global_check):
                    print(f"🇻🇳 Already translated: {file_path}")
                    translated_files.append(file_path)
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
                    return (0, len(skipped_files), len(files), len(translated_files))

            return (len(added_files), len(skipped_files), len(failed_files), len(translated_files))

        finally:
            self._release_lock()

def has_arxiv_id(filename: str) -> bool:
    """Check if filename starts with arxiv ID pattern (YYMM.NNNNN)."""
    name = Path(filename).name
    return bool(re.match(r'^\d{4}\.\d{4,5}', name))


def find_txt_files(path: str, recursive: bool = False, exclude_vi: bool = True,
                   arxiv_only: bool = False) -> List[str]:
    """Find all .txt files in a path, optionally excluding _vi.txt files."""
    path_obj = Path(path)

    # List of metadata files to always exclude
    EXCLUDED_FILES = {
        'arxiv_links.txt', 'translation_queue.txt', 'requirements.txt',
        'missing_papers.txt', 'arxiv_duplicate_report.txt', 'README.txt',
        'translation_queue_big_file.txt', 'CLAUDE.txt'
    }

    def is_valid_file(f: Path) -> bool:
        """Check if file is valid for translation queue."""
        if not f.is_file():
            return False
        if exclude_vi and f.name.endswith('_vi.txt'):
            return False
        # Exclude metadata files
        if f.name in EXCLUDED_FILES:
            return False
        # If arxiv_only mode, check for arxiv ID prefix
        if arxiv_only and not has_arxiv_id(f.name):
            return False
        return True

    if path_obj.is_file():
        if path_obj.suffix == '.txt' and is_valid_file(path_obj):
            return [str(path_obj)]
        else:
            if path_obj.name.endswith('_vi.txt'):
                print(f"🇻🇳 Skipping _vi.txt file: {path}")
            elif arxiv_only and not has_arxiv_id(path_obj.name):
                print(f"⏭️  Skipping non-arxiv file: {path}")
            else:
                print(f"⚠️  Not a valid .txt file: {path}")
            return []

    elif path_obj.is_dir():
        if recursive:
            pattern = "**/*.txt"
        else:
            pattern = "*.txt"

        txt_files = list(path_obj.glob(pattern))
        return [str(f) for f in txt_files if is_valid_file(f)]

    else:
        # Try as glob pattern
        try:
            matching_files = glob.glob(path)
            return [f for f in matching_files if f.endswith('.txt') and is_valid_file(Path(f))]
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
    parser.add_argument("--include-translated", action="store_true",
                       help="Include files that already have _vi.txt translations (default: skip them)")
    parser.add_argument("--arxiv-only", "-a", action="store_true",
                       help="Only include files with arxiv ID prefix (e.g., 2305.12345-*.txt)")
    parser.add_argument("--global-check", "-g", action="store_true",
                       help="Check for translations across entire repository (not just same folder)")
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
    arxiv_only = getattr(args, 'arxiv_only', False)
    for path in args.paths:
        files = find_txt_files(path, args.recursive, arxiv_only=arxiv_only)
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
    global_check = getattr(args, 'global_check', False)
    if global_check:
        print("\n🔄 Adding files to queue (checking translations globally)...")
    else:
        print("\n🔄 Adding files to queue...")

    added, skipped, failed, translated = queue_manager.add_files(
        unique_files,
        skip_existing=not args.force,
        ignore_translated=not args.include_translated,
        global_check=global_check
    )

    # Summary
    print(f"\n📊 Summary:")
    print(f"✅ Added:      {added}")
    print(f"📝 In queue:   {skipped}")
    print(f"🇻🇳 Translated: {translated}")
    print(f"❌ Failed:     {failed}")
    print(f"📁 Queue file: {args.queue_file}")

    if added > 0:
        print(f"\n🚀 Ready to start translation with:")
        print(f"   python translate_manager.py --queue-file {args.queue_file}")
    elif translated > 0:
        print(f"\nℹ️  {translated} files already have Vietnamese translations.")
        print(f"   Use --include-translated to add them anyway.")

if __name__ == "__main__":
    main()