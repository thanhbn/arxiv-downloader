#!/usr/bin/env python3
"""
Simple status checker for all collections
"""

import os
import glob
from pathlib import Path

def check_collections_status():
    """Check status of all collections"""
    print("📊 Collection Status Report")
    print("=" * 50)
    
    # Find all arxiv_links.txt files
    arxiv_files = []
    for root, dirs, files in os.walk('.'):
        if 'arxiv_links.txt' in files:
            arxiv_files.append(os.path.join(root, 'arxiv_links.txt'))
    
    arxiv_files.sort()
    
    total_collections = len(arxiv_files)
    total_links = 0
    total_pdfs = 0
    total_txt = 0
    
    print(f"📋 Found {total_collections} collections\n")
    
    for file_path in arxiv_files:
        collection_dir = os.path.dirname(file_path)
        collection_name = os.path.basename(collection_dir) if collection_dir != '.' else 'root'
        
        # Count links in arxiv_links.txt
        links_count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and 'arxiv.org' in line:
                        links_count += 1
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            continue
        
        # Count PDFs and TXT files in collection directory
        pdf_files = glob.glob(os.path.join(collection_dir, '*.pdf'))
        txt_files = glob.glob(os.path.join(collection_dir, '*.txt'))
        # Exclude arxiv_links.txt from txt count
        txt_files = [f for f in txt_files if not f.endswith('arxiv_links.txt')]
        
        pdf_count = len(pdf_files)
        txt_count = len(txt_files)
        
        total_links += links_count
        total_pdfs += pdf_count
        total_txt += txt_count
        
        # Calculate completion percentage
        completion = (pdf_count / links_count * 100) if links_count > 0 else 0
        
        # Status indicator
        if completion >= 90:
            status = "✅"
        elif completion >= 50:
            status = "⚠️"
        else:
            status = "❌"
        
        print(f"{status} {collection_name:<20} Links: {links_count:3d} | PDFs: {pdf_count:3d} | TXT: {txt_count:3d} | Complete: {completion:5.1f}%")
    
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY:")
    print(f"  📁 Total collections: {total_collections}")
    print(f"  🔗 Total links: {total_links}")
    print(f"  📄 Total PDFs: {total_pdfs}")
    print(f"  📝 Total TXT: {total_txt}")
    
    if total_links > 0:
        overall_completion = (total_pdfs / total_links * 100)
        print(f"  ✅ Overall completion: {overall_completion:.1f}%")
    
    print("=" * 50)

if __name__ == "__main__":
    check_collections_status()