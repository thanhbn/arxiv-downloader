#!/usr/bin/env python3
"""
Script to backup duplicate arXiv files.
Moves simple arXiv ID files (e.g., 2505.20355.txt) to backup folder,
keeps descriptive named files (e.g., 2505.20355-GraLoRA-_Granular_Low-Rank_Adaptation_for.txt).
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict
import argparse
import zipfile
from datetime import datetime

def find_arxiv_duplicates(root_dir):
    """Find duplicate arXiv files based on arXiv ID."""
    arxiv_files = defaultdict(list)
    
    # Pattern to match arXiv IDs (YYYY.NNNNN)
    arxiv_pattern = re.compile(r'(\d{4}\.\d{5})')
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.txt'):
                match = arxiv_pattern.search(file)
                if match:
                    arxiv_id = match.group(1)
                    full_path = os.path.join(root, file)
                    arxiv_files[arxiv_id].append(full_path)
    
    # Filter to only duplicates
    duplicates = {k: v for k, v in arxiv_files.items() if len(v) > 1}
    return duplicates

def categorize_files(file_list):
    """Categorize files into simple ID vs descriptive names."""
    simple_files = []
    descriptive_files = []
    
    # Pattern for simple arXiv ID files (just the ID + .txt)
    simple_pattern = re.compile(r'^(\d{4}\.\d{5})\.txt$')
    
    for file_path in file_list:
        filename = os.path.basename(file_path)
        if simple_pattern.match(filename):
            simple_files.append(file_path)
        else:
            descriptive_files.append(file_path)
    
    return simple_files, descriptive_files

def backup_files(files_to_backup, backup_dir, dry_run=False):
    """Move files to backup directory."""
    if not os.path.exists(backup_dir) and not dry_run:
        os.makedirs(backup_dir)
        print(f"Created backup directory: {backup_dir}")
    
    moved_count = 0
    for file_path in files_to_backup:
        filename = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, filename)
        
        if dry_run:
            print(f"[DRY RUN] Would move: {file_path} -> {backup_path}")
        else:
            try:
                shutil.move(file_path, backup_path)
                print(f"Moved: {file_path} -> {backup_path}")
                moved_count += 1
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
    
    return moved_count

def zip_backup_files(backup_dir, dry_run=False):
    """Zip all txt files in backup directory with yymmdd_txt_bak.zip format."""
    if not os.path.exists(backup_dir):
        print(f"❌ Backup directory {backup_dir} does not exist.")
        return None
    
    # Get all txt files in backup directory
    txt_files = []
    for file in os.listdir(backup_dir):
        if file.endswith('.txt'):
            txt_files.append(os.path.join(backup_dir, file))
    
    if not txt_files:
        print(f"📁 No .txt files found in {backup_dir} to zip.")
        return None
    
    # Create zip filename with yymmdd format
    today = datetime.now()
    zip_filename = f"{today.strftime('%y%m%d')}_txt_bak.zip"
    zip_path = os.path.join(backup_dir, zip_filename)
    
    if dry_run:
        print(f"[DRY RUN] Would create zip: {zip_path}")
        print(f"[DRY RUN] Would include {len(txt_files)} .txt files:")
        for txt_file in txt_files[:5]:  # Show first 5 files
            print(f"  - {os.path.basename(txt_file)}")
        if len(txt_files) > 5:
            print(f"  ... and {len(txt_files) - 5} more files")
        return zip_path
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for txt_file in txt_files:
                # Add file to zip with just the filename (not full path)
                arcname = os.path.basename(txt_file)
                zipf.write(txt_file, arcname)
                print(f"Added to zip: {arcname}")
        
        print(f"✅ Successfully created zip: {zip_path}")
        print(f"📦 Zipped {len(txt_files)} .txt files")
        
        # Optionally remove original txt files after successful zip
        try:
            remove_originals = input("Remove original .txt files after zipping? (y/N): ")
            if remove_originals.lower() == 'y':
                for txt_file in txt_files:
                    os.remove(txt_file)
                    print(f"Removed: {os.path.basename(txt_file)}")
                print(f"🗑️  Removed {len(txt_files)} original .txt files")
        except (EOFError, KeyboardInterrupt):
            print("\n📁 Keeping original .txt files")
        
        return zip_path
        
    except Exception as e:
        print(f"❌ Error creating zip file: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Backup duplicate arXiv files')
    parser.add_argument('--root-dir', '-r', default='.', 
                       help='Root directory to search for files (default: current directory)')
    parser.add_argument('--backup-dir', '-b', default='./arxiv_backup', 
                       help='Backup directory (default: ./arxiv_backup)')
    parser.add_argument('--dry-run', '-d', action='store_true', 
                       help='Show what would be moved without actually moving')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose output')
    parser.add_argument('--zip', '-z', action='store_true',
                       help='Zip all txt files in backup directory after moving')
    parser.add_argument('--zip-only', action='store_true',
                       help='Only zip existing txt files in backup directory (skip file moving)')
    
    args = parser.parse_args()
    
    # If zip-only mode, just zip existing files and exit
    if args.zip_only:
        print("📦 ZIP-ONLY MODE: Zipping existing txt files in backup directory")
        zip_path = zip_backup_files(args.backup_dir, args.dry_run)
        if zip_path:
            print(f"✅ Zip operation completed: {zip_path}")
        return
    
    print("🔍 Searching for duplicate arXiv files...")
    duplicates = find_arxiv_duplicates(args.root_dir)
    
    if not duplicates:
        print("✅ No duplicate arXiv files found.")
        return
    
    print(f"📋 Found {len(duplicates)} arXiv IDs with duplicates:")
    
    total_to_backup = 0
    backup_list = []
    
    for arxiv_id, files in duplicates.items():
        simple_files, descriptive_files = categorize_files(files)
        
        if args.verbose:
            print(f"\n📄 arXiv ID: {arxiv_id}")
            print(f"  Simple files: {len(simple_files)}")
            for f in simple_files:
                print(f"    - {f}")
            print(f"  Descriptive files: {len(descriptive_files)}")
            for f in descriptive_files:
                print(f"    - {f}")
        
        # Only backup simple files if there are descriptive files to keep
        if simple_files and descriptive_files:
            backup_list.extend(simple_files)
            total_to_backup += len(simple_files)
            if not args.verbose:
                print(f"  {arxiv_id}: {len(simple_files)} simple files to backup, {len(descriptive_files)} descriptive files to keep")
        elif simple_files and not descriptive_files:
            if args.verbose:
                print(f"  ⚠️  Only simple files found for {arxiv_id}, skipping backup")
        elif not simple_files and descriptive_files:
            if args.verbose:
                print(f"  ✅ Only descriptive files found for {arxiv_id}, no backup needed")
    
    if total_to_backup == 0:
        print("✅ No simple duplicate files found to backup.")
        return
    
    print(f"\n📦 Total files to backup: {total_to_backup}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be moved")
    else:
        confirm = input("Continue with backup? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Backup cancelled.")
            return
    
    moved_count = backup_files(backup_list, args.backup_dir, args.dry_run)
    
    if not args.dry_run:
        print(f"✅ Successfully moved {moved_count} files to {args.backup_dir}")
        
        # Zip files if requested
        if args.zip:
            print("\n📦 Creating zip archive of backup files...")
            zip_path = zip_backup_files(args.backup_dir, args.dry_run)
            if zip_path:
                print(f"✅ Zip operation completed: {zip_path}")
    else:
        print(f"✅ Dry run completed. {total_to_backup} files would be moved.")
        
        # Show what zip would be created in dry run mode
        if args.zip:
            print("\n📦 ZIP PREVIEW:")
            zip_backup_files(args.backup_dir, True)

if __name__ == '__main__':
    main()