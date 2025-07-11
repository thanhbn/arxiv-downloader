#!/usr/bin/env python3
"""
Organize ArXiv papers by scanning all arxiv_links.txt files and moving papers to correct collection folders.
"""

import os
import shutil
import re
from pathlib import Path

def extract_arxiv_id(url):
    """Extract arXiv ID from URL"""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def find_arxiv_links_files(base_dir):
    """Find all arxiv_links.txt files in subdirectories"""
    links_files = []
    for root, dirs, files in os.walk(base_dir):
        if 'arxiv_links.txt' in files:
            collection_name = os.path.basename(root)
            links_files.append((collection_name, os.path.join(root, 'arxiv_links.txt')))
    return links_files

def find_paper_in_directories(arxiv_id, base_dir):
    """Find paper PDF file in any subdirectory"""
    pdf_filename = f"{arxiv_id}.pdf"
    for root, dirs, files in os.walk(base_dir):
        if pdf_filename in files:
            return os.path.join(root, pdf_filename)
    return None

def organize_papers():
    """Main function to organize papers"""
    base_dir = "."
    os.chdir(base_dir)
    
    # Find all arxiv_links.txt files
    links_files = find_arxiv_links_files(base_dir)
    
    print(f"Found {len(links_files)} collections with arxiv_links.txt files:")
    for collection, path in links_files:
        print(f"  - {collection}: {path}")
    
    moved_count = 0
    total_papers = 0
    
    # Process each collection
    for collection_name, links_file_path in links_files:
        print(f"\nProcessing collection: {collection_name}")
        
        # Read URLs from arxiv_links.txt
        try:
            with open(links_file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"  Error reading {links_file_path}: {e}")
            continue
            
        print(f"  Found {len(urls)} URLs in {collection_name}")
        total_papers += len(urls)
        
        # Create collection directory if it doesn't exist
        collection_dir = os.path.join(base_dir, collection_name)
        os.makedirs(collection_dir, exist_ok=True)
        
        # Process each URL
        for url in urls:
            arxiv_id = extract_arxiv_id(url)
            if not arxiv_id:
                print(f"    Could not extract arXiv ID from: {url}")
                continue
                
            # Look for the paper in any directory
            paper_path = find_paper_in_directories(arxiv_id, base_dir)
            if paper_path:
                # Check if paper is already in correct location
                target_path = os.path.join(collection_dir, f"{arxiv_id}.pdf")
                if paper_path != target_path:
                    try:
                        shutil.move(paper_path, target_path)
                        print(f"    Moved {arxiv_id}.pdf to {collection_name}/")
                        moved_count += 1
                    except Exception as e:
                        print(f"    Error moving {arxiv_id}.pdf: {e}")
                else:
                    print(f"    {arxiv_id}.pdf already in correct location")
            else:
                print(f"    Paper {arxiv_id}.pdf not found")
    
    print(f"\nSummary:")
    print(f"  Total collections processed: {len(links_files)}")
    print(f"  Total papers expected: {total_papers}")
    print(f"  Papers moved: {moved_count}")
    
    # Show final collection status
    print(f"\nFinal collection status:")
    for collection_name, _ in links_files:
        collection_dir = os.path.join(base_dir, collection_name)
        if os.path.exists(collection_dir):
            pdf_count = len([f for f in os.listdir(collection_dir) if f.endswith('.pdf')])
            print(f"  {collection_name}: {pdf_count} papers")

if __name__ == "__main__":
    organize_papers()