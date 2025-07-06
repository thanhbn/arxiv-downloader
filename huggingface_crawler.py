#!/usr/bin/env python3
"""
Hugging Face Collections ArXiv Crawler

This script crawls Hugging Face collections to extract ArXiv links and converts them to PDF format.
It creates organized directories and saves ArXiv PDF links to text files for later downloading.
"""

import os
import re
import requests
from urllib.parse import urlparse, urljoin
import time
from pathlib import Path


def extract_collection_name(url):
    """Extract meaningful collection name from Hugging Face URL"""
    # Parse URL to get the last part after the last slash
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    
    # URL format: /collections/username/collection-name-id
    if len(path_parts) >= 3 and path_parts[0] == 'collections':
        collection_part = path_parts[2]
        # Remove the ID part (usually after the last dash followed by hex)
        # Example: multimodal-65389aebc8b0cccf1f3c97b7 -> multimodal
        name_match = re.match(r'^([a-zA-Z0-9\-]+?)-[a-f0-9]+$', collection_part)
        if name_match:
            return name_match.group(1)
        # If no hex ID pattern, return the whole part
        return collection_part
    
    # Fallback: use the last part of the path
    return path_parts[-1] if path_parts else 'unknown'


def get_arxiv_links_from_page(url):
    """Extract ArXiv links from a Hugging Face collection page using regex"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        arxiv_ids = set()
        
        # Method 1: Find ArXiv IDs in title attributes (e.g., title="arxiv:2310.07488")
        title_pattern = r'title=["\']arxiv:([0-9]+\.[0-9]+)["\']'
        title_matches = re.findall(title_pattern, html_content, re.IGNORECASE)
        for arxiv_id in title_matches:
            arxiv_ids.add(arxiv_id)
        
        # Method 2: Find /papers/ID links and extract ArXiv IDs
        papers_pattern = r'href=["\']\/papers\/([0-9]+\.[0-9]+)["\']'
        paper_matches = re.findall(papers_pattern, html_content)
        for arxiv_id in paper_matches:
            arxiv_ids.add(arxiv_id)
        
        # Method 3: Find direct arxiv.org links (backup method)
        arxiv_pattern = r'arxiv\.org/(?:abs/|pdf/)([0-9]+\.[0-9]+)'
        arxiv_matches = re.findall(arxiv_pattern, html_content, re.IGNORECASE)
        for arxiv_id in arxiv_matches:
            arxiv_ids.add(arxiv_id)
        
        # Convert ArXiv IDs to full URLs
        arxiv_urls = []
        for arxiv_id in arxiv_ids:
            arxiv_urls.append(f"https://arxiv.org/abs/{arxiv_id}")
        
        return arxiv_urls
        
    except requests.RequestException as e:
        return []
    except Exception as e:
        return []


def convert_to_pdf_links(arxiv_links):
    """Convert ArXiv abstract links to PDF links and deduplicate"""
    pdf_links = set()
    
    for link in arxiv_links:
        # Extract ArXiv ID from the URL
        arxiv_id_match = re.search(r'arxiv\.org/(?:abs/|pdf/)([0-9]+\.[0-9]+)', link)
        if arxiv_id_match:
            arxiv_id = arxiv_id_match.group(1)
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            pdf_links.add(pdf_url)
    
    return sorted(list(pdf_links))


def save_links_to_file(links, filepath):
    """Save ArXiv PDF links to a text file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for link in links:
                f.write(link + '\n')
        return True
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")
        return False


def process_collection(url, base_dir):
    """Process a single Hugging Face collection"""
    # Extract collection name
    collection_name = extract_collection_name(url)
    
    # Create collection directory
    collection_dir = Path(base_dir) / collection_name
    collection_dir.mkdir(exist_ok=True)
    
    # Get ArXiv links from the page
    arxiv_links = get_arxiv_links_from_page(url)
    if not arxiv_links:
        return False
    
    # Convert to PDF links and deduplicate
    pdf_links = convert_to_pdf_links(arxiv_links)
    if not pdf_links:
        return False
    
    # Save to file
    output_file = collection_dir / "arxiv_links.txt"
    if save_links_to_file(pdf_links, output_file):
        print(f"({len(pdf_links)} links -> {output_file})")
        return True
    else:
        return False


def main():
    """Main function to process all collections"""
    base_dir = Path("/home/admin88/arxiv-downloader")
    collections_file = base_dir / "huggingface_collections_links.txt"
    
    if not collections_file.exists():
        print(f"Error: {collections_file} not found")
        return
    
    # Read collection URLs
    collection_urls = []
    try:
        with open(collections_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and line.startswith('https://'):
                    collection_urls.append(line)
    except Exception as e:
        print(f"Error reading {collections_file}: {e}")
        return
    
    print(f"Found {len(collection_urls)} collections to process")
    print("=" * 50)
    
    # Process each collection
    successful_collections = 0
    failed_collections = 0
    
    for i, url in enumerate(collection_urls, 1):
        print(f"[{i}/{len(collection_urls)}] Processing...", end=" ")
        try:
            result = process_collection(url, base_dir)
            if result:
                successful_collections += 1
                print("✓")
            else:
                failed_collections += 1
                print("✗")
        except Exception as e:
            failed_collections += 1
            print(f"✗ Error: {e}")
        
        # Be respectful with rate limiting
        if i < len(collection_urls):
            time.sleep(1)  # Reduced to 1-second delay between requests
    
    print(f"\nSummary: {successful_collections} successful, {failed_collections} failed out of {len(collection_urls)} total collections")


if __name__ == "__main__":
    main()