#!/usr/bin/env python3

import os
import sys
import requests
import time
from pathlib import Path
from urllib.parse import urlparse
import re


def clean_filename(filename):
    """Clean filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def extract_paper_id(url):
    """Extract paper ID from ArXiv URL."""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None


def download_pdf(url, output_dir):
    """Download PDF from URL to output directory."""
    try:
        paper_id = extract_paper_id(url)
        if not paper_id:
            print(f"Could not extract paper ID from {url}")
            return False
        
        filename = f"{paper_id}.pdf"
        filepath = output_dir / filename
        
        if filepath.exists():
            print(f"File already exists: {filename}")
            return True
        
        print(f"Downloading {filename}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Successfully downloaded: {filename}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error downloading {url}: {e}")
        return False


def process_url_file(file_path):
    """Process a file containing ArXiv URLs."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return
    
    # Create output directory based on filename
    base_name = Path(file_path).stem
    output_dir = Path(base_name)
    output_dir.mkdir(exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Read URLs from file
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
    
    if not urls:
        print("No valid URLs found in file")
        return
    
    print(f"Found {len(urls)} URLs to process")
    
    # Download each PDF
    successful = 0
    failed = 0
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        
        if download_pdf(url, output_dir):
            successful += 1
        else:
            failed += 1
        
        # Small delay to be respectful to the server
        time.sleep(1)
    
    print(f"\n=== Download Summary ===")
    print(f"Total URLs: {len(urls)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Output directory: {output_dir}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python arxiv_downloader.py <url_file>")
        print("Example: python arxiv_downloader.py CoT.txt")
        sys.exit(1)
    
    url_file = sys.argv[1]
    process_url_file(url_file)


if __name__ == "__main__":
    main()