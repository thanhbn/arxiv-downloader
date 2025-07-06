#!/usr/bin/env python3
"""
Check which papers are missing from multimodal collection
"""

import os
import re

def extract_arxiv_id(url):
    """Extract arXiv ID from URL"""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def check_multimodal():
    """Check multimodal collection"""
    base_dir = "/home/admin88/arxiv-downloader"
    multimodal_dir = os.path.join(base_dir, "multimodal")
    
    # Read URLs from arxiv_links.txt
    links_file = os.path.join(multimodal_dir, "arxiv_links.txt")
    with open(links_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"URLs in arxiv_links.txt: {len(urls)}")
    
    # Get arxiv IDs from URLs
    expected_ids = []
    for url in urls:
        arxiv_id = extract_arxiv_id(url)
        if arxiv_id:
            expected_ids.append(arxiv_id)
    
    print(f"Valid arXiv IDs: {len(expected_ids)}")
    
    # Get actual PDF files
    actual_files = [f for f in os.listdir(multimodal_dir) if f.endswith('.pdf')]
    actual_ids = [f.replace('.pdf', '') for f in actual_files]
    
    print(f"PDF files in folder: {len(actual_files)}")
    
    # Find missing papers
    missing_ids = set(expected_ids) - set(actual_ids)
    extra_ids = set(actual_ids) - set(expected_ids)
    
    print(f"\nMissing papers: {len(missing_ids)}")
    if missing_ids:
        print("Missing papers:")
        for arxiv_id in sorted(missing_ids)[:20]:  # Show first 20
            print(f"  {arxiv_id}.pdf")
        if len(missing_ids) > 20:
            print(f"  ... and {len(missing_ids) - 20} more")
    
    print(f"\nExtra papers (not in arxiv_links.txt): {len(extra_ids)}")
    if extra_ids:
        print("Extra papers:")
        for arxiv_id in sorted(extra_ids)[:10]:  # Show first 10
            print(f"  {arxiv_id}.pdf")
        if len(extra_ids) > 10:
            print(f"  ... and {len(extra_ids) - 10} more")
    
    # Check if missing papers exist elsewhere
    print(f"\nSearching for missing papers in other directories...")
    found_count = 0
    for arxiv_id in list(missing_ids)[:10]:  # Check first 10
        for root, dirs, files in os.walk(base_dir):
            if f"{arxiv_id}.pdf" in files:
                rel_path = os.path.relpath(root, base_dir)
                print(f"  Found {arxiv_id}.pdf in {rel_path}/")
                found_count += 1
                break
    
    if found_count > 0:
        print(f"Found {found_count} missing papers in other directories")

if __name__ == "__main__":
    check_multimodal()