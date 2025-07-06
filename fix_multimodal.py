#!/usr/bin/env python3
"""
Fix multimodal collection by copying back papers that belong to multimodal
"""

import os
import shutil
import re

def extract_arxiv_id(url):
    """Extract arXiv ID from URL"""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def find_paper_in_directories(arxiv_id, base_dir, exclude_dir):
    """Find paper PDF file in any subdirectory except exclude_dir"""
    pdf_filename = f"{arxiv_id}.pdf"
    for root, dirs, files in os.walk(base_dir):
        if root == exclude_dir:
            continue
        if pdf_filename in files:
            return os.path.join(root, pdf_filename)
    return None

def fix_multimodal():
    """Fix multimodal collection"""
    base_dir = "/home/admin88/arxiv-downloader"
    multimodal_dir = os.path.join(base_dir, "multimodal")
    
    # Read URLs from arxiv_links.txt
    links_file = os.path.join(multimodal_dir, "arxiv_links.txt")
    with open(links_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"Processing {len(urls)} URLs from multimodal/arxiv_links.txt")
    
    # Get expected arxiv IDs
    expected_ids = []
    for url in urls:
        arxiv_id = extract_arxiv_id(url)
        if arxiv_id:
            expected_ids.append(arxiv_id)
    
    # Get current PDF files in multimodal
    current_files = [f.replace('.pdf', '') for f in os.listdir(multimodal_dir) if f.endswith('.pdf')]
    missing_ids = set(expected_ids) - set(current_files)
    
    print(f"Missing papers: {len(missing_ids)}")
    
    # Copy missing papers back to multimodal
    copied_count = 0
    not_found_count = 0
    
    for arxiv_id in missing_ids:
        # Find paper in other directories
        paper_path = find_paper_in_directories(arxiv_id, base_dir, multimodal_dir)
        if paper_path:
            target_path = os.path.join(multimodal_dir, f"{arxiv_id}.pdf")
            try:
                shutil.copy2(paper_path, target_path)  # Use copy2 to preserve, not move
                print(f"  Copied {arxiv_id}.pdf from {os.path.dirname(paper_path)}")
                copied_count += 1
            except Exception as e:
                print(f"  Error copying {arxiv_id}.pdf: {e}")
        else:
            print(f"  Paper {arxiv_id}.pdf not found anywhere")
            not_found_count += 1
    
    print(f"\nSummary:")
    print(f"  Papers copied back: {copied_count}")
    print(f"  Papers not found: {not_found_count}")
    
    # Final count
    final_count = len([f for f in os.listdir(multimodal_dir) if f.endswith('.pdf')])
    print(f"  Final PDF count in multimodal/: {final_count}")
    print(f"  Expected count: {len(expected_ids)}")

if __name__ == "__main__":
    fix_multimodal()