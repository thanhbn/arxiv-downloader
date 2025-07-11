#!/usr/bin/env python3
"""
Check all collections against their arxiv_links.txt files and move misplaced papers to correct folders
"""

import os
import shutil
import re
from pathlib import Path
import argparse

def extract_arxiv_id(url):
    """Extract arXiv ID from URL"""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def find_arxiv_links_files(base_dir, exclude_dirs=None):
    """Find all arxiv_links.txt files in subdirectories"""
    if exclude_dirs is None:
        exclude_dirs = {'progress', '.git'}
    
    links_files = []
    for root, dirs, files in os.walk(base_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        if 'arxiv_links.txt' in files:
            collection_name = os.path.basename(root)
            links_files.append((collection_name, root, os.path.join(root, 'arxiv_links.txt')))
    
    return links_files

def find_paper_globally(arxiv_id, base_dir, exclude_dirs=None):
    """Find paper PDF file in any subdirectory"""
    if exclude_dirs is None:
        exclude_dirs = {'progress', '.git'}
    
    pdf_filename = f"{arxiv_id}.pdf"
    found_locations = []
    
    for root, dirs, files in os.walk(base_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        if pdf_filename in files:
            found_locations.append(os.path.join(root, pdf_filename))
    
    return found_locations

def read_arxiv_links(links_file_path):
    """Read and parse arxiv_links.txt file"""
    try:
        with open(links_file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        arxiv_ids = []
        for url in urls:
            arxiv_id = extract_arxiv_id(url)
            if arxiv_id:
                arxiv_ids.append(arxiv_id)
            else:
                print(f"    Warning: Could not extract arXiv ID from: {url}")
        
        return arxiv_ids
    except Exception as e:
        print(f"    Error reading {links_file_path}: {e}")
        return []

def check_and_move_papers(base_dir, dry_run=True, collections_filter=None):
    """Check all collections and move misplaced papers"""
    os.chdir(base_dir)
    
    # Find all arxiv_links.txt files
    links_files = find_arxiv_links_files(base_dir)
    
    if collections_filter:
        # Filter collections if specified
        links_files = [(name, path, links) for name, path, links in links_files 
                      if name in collections_filter]
    
    print(f"Found {len(links_files)} collections to check")
    if collections_filter:
        print(f"Filtering to: {collections_filter}")
    
    total_moved = 0
    total_missing = 0
    total_correct = 0
    
    # Process each collection
    for collection_name, collection_path, links_file_path in links_files:
        print(f"\n{'='*60}")
        print(f"Processing collection: {collection_name}")
        print(f"Path: {collection_path}")
        
        # Read expected arxiv IDs
        expected_ids = read_arxiv_links(links_file_path)
        if not expected_ids:
            print(f"  No valid arXiv IDs found, skipping...")
            continue
        
        print(f"  Expected papers: {len(expected_ids)}")
        
        # Check current papers in collection folder
        current_papers = [f.replace('.pdf', '') for f in os.listdir(collection_path) 
                         if f.endswith('.pdf')]
        print(f"  Current papers in folder: {len(current_papers)}")
        
        # Find missing and extra papers
        missing_ids = set(expected_ids) - set(current_papers)
        extra_ids = set(current_papers) - set(expected_ids)
        correct_ids = set(current_papers) & set(expected_ids)
        
        print(f"  Correct papers: {len(correct_ids)}")
        print(f"  Missing papers: {len(missing_ids)}")
        print(f"  Extra papers: {len(extra_ids)}")
        
        total_correct += len(correct_ids)
        total_missing += len(missing_ids)
        
        # Handle missing papers
        if missing_ids:
            print(f"  \nSearching for missing papers...")
            moved_count = 0
            for arxiv_id in missing_ids:
                # Find paper globally
                locations = find_paper_globally(arxiv_id, base_dir)
                if locations:
                    # Use the first location found
                    source_path = locations[0]
                    source_dir = os.path.dirname(source_path)
                    source_collection = os.path.basename(source_dir)
                    target_path = os.path.join(collection_path, f"{arxiv_id}.pdf")
                    
                    if dry_run:
                        print(f"    [DRY RUN] Would move {arxiv_id}.pdf from {source_collection}/ to {collection_name}/")
                    else:
                        try:
                            shutil.move(source_path, target_path)
                            print(f"    Moved {arxiv_id}.pdf from {source_collection}/ to {collection_name}/")
                            moved_count += 1
                            total_moved += 1
                        except Exception as e:
                            print(f"    Error moving {arxiv_id}.pdf: {e}")
                    
                    # Show additional locations if found
                    if len(locations) > 1:
                        print(f"      Note: Also found in {len(locations)-1} other location(s)")
                else:
                    print(f"    Paper {arxiv_id}.pdf not found anywhere")
            
            if not dry_run and moved_count > 0:
                print(f"  Successfully moved {moved_count} papers to {collection_name}/")
        
        # Handle extra papers
        if extra_ids:
            print(f"  \nExtra papers in {collection_name}/ (not in arxiv_links.txt):")
            for arxiv_id in list(extra_ids)[:10]:  # Show first 10
                print(f"    {arxiv_id}.pdf")
            if len(extra_ids) > 10:
                print(f"    ... and {len(extra_ids) - 10} more")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Collections processed: {len(links_files)}")
    print(f"  Papers in correct locations: {total_correct}")
    print(f"  Papers missing: {total_missing}")
    if dry_run:
        print(f"  Papers that would be moved: {total_moved}")
        print(f"  \nTo actually move papers, run with --execute flag")
    else:
        print(f"  Papers moved: {total_moved}")

def main():
    parser = argparse.ArgumentParser(description='Check and move papers to correct collections')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually move files (default is dry run)')
    parser.add_argument('--base-dir', default='.',
                       help='Base directory to search')
    parser.add_argument('--collections', nargs='+',
                       help='Specific collections to process (default: all)')
    parser.add_argument('--exclude', nargs='+', default=['progress', '.git'],
                       help='Directories to exclude')
    
    args = parser.parse_args()
    
    print(f"Base directory: {args.base_dir}")
    if args.execute:
        print("Mode: EXECUTE (will actually move files)")
    else:
        print("Mode: DRY RUN (will only show what would be moved)")
    
    check_and_move_papers(
        base_dir=args.base_dir,
        dry_run=not args.execute,
        collections_filter=args.collections
    )

if __name__ == "__main__":
    main()