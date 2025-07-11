#!/usr/bin/env python3

import os
import sys
import requests
import time
from pathlib import Path
from urllib.parse import urlparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import random
import glob


class ArxivDownloader:
    def __init__(self, max_workers=1, min_delay=3.0, max_delay=3.5, check_existing_txt=True):
        self.max_workers = max_workers
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.check_existing_txt = check_existing_txt
        self.stats_lock = Lock()
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        
    def clean_filename(self, filename):
        """Clean filename by removing invalid characters."""
        return re.sub(r'[<>:"/\\|?*]', '_', filename)

    def extract_paper_id(self, url):
        """Extract paper ID from ArXiv URL."""
        match = re.search(r'(\d{4}\.\d{4,5})', url)
        return match.group(1) if match else None
    
    def check_existing_txt_files(self, paper_id, project_root="."):
        """Check if any TXT file with the same arXiv ID exists anywhere in the project."""
        # Search for TXT files starting with the arXiv ID
        search_pattern = os.path.join(project_root, "**", f"{paper_id}*.txt")
        existing_files = glob.glob(search_pattern, recursive=True)
        
        # Filter out files that don't actually start with the arXiv ID
        # (in case glob matches partial matches)
        valid_files = []
        for file_path in existing_files:
            filename = os.path.basename(file_path)
            if filename.startswith(paper_id):
                valid_files.append(file_path)
        
        return valid_files

    def download_pdf(self, url, output_dir):
        """Download PDF from URL to output directory."""
        try:
            paper_id = self.extract_paper_id(url)
            if not paper_id:
                print(f"Could not extract paper ID from {url}")
                return False
            
            filename = f"{paper_id}.pdf"
            filepath = output_dir / filename
            
            # Check if PDF already exists in target directory
            if filepath.exists():
                print(f"✓ Already exists: {filename}")
                with self.stats_lock:
                    self.skipped += 1
                return True
            
            # Check if any TXT file with this arXiv ID exists anywhere in the project
            if self.check_existing_txt:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                existing_txt_files = self.check_existing_txt_files(paper_id, project_root)
                
                if existing_txt_files:
                    print(f"📝 TXT file already exists for {paper_id}: {os.path.basename(existing_txt_files[0])}")
                    print(f"⏭️  Skipping download of {filename}")
                    with self.stats_lock:
                        self.skipped += 1
                    return True
            
            print(f"📥 Downloading {filename}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*'
            }
            
            # Add random delay for rate limiting
            delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(delay)
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Create temp file first
            temp_filepath = filepath.with_suffix('.tmp')
            
            with open(temp_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Rename temp file to final name
            temp_filepath.rename(filepath)
            
            print(f"✅ Downloaded: {filename}")
            with self.stats_lock:
                self.successful += 1
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error for {url}: {e}")
            with self.stats_lock:
                self.failed += 1
            return False
        except Exception as e:
            print(f"❌ Unexpected error for {url}: {e}")
            with self.stats_lock:
                self.failed += 1
            return False

    def download_batch(self, urls, output_dir):
        """Download multiple PDFs concurrently."""
        print(f"🚀 Starting concurrent downloads with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(self.download_pdf, url, output_dir): url 
                for url in urls
            }
            
            # Process completed downloads
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Exception in download thread for {url}: {e}")
                    with self.stats_lock:
                        self.failed += 1

    def process_url_file(self, file_path, output_dir=None):
        """Process a file containing ArXiv URLs."""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        # Create output directory
        if output_dir is None:
            # Create output directory based on filename (default behavior)
            base_name = Path(file_path).stem
            output_dir = Path(base_name)
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {output_dir}")
        
        # Read URLs from file
        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
        
        if not urls:
            print("❌ No valid URLs found in file")
            return
        
        print(f"🔗 Found {len(urls)} URLs to process")
        
        # Reset stats
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        
        # Record start time
        start_time = time.time()
        
        # Download all PDFs concurrently
        self.download_batch(urls, output_dir)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 DOWNLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"Total URLs: {len(urls)}")
        print(f"✅ Successful: {self.successful}")
        print(f"⏩ Skipped (already exists): {self.skipped}")
        print(f"❌ Failed: {self.failed}")
        print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
        print(f"🚀 Average time per file: {elapsed_time/len(urls):.1f} seconds")
        print(f"📁 Output directory: {output_dir}")
        
        # Success rate
        if len(urls) > 0:
            success_rate = (self.successful + self.skipped) / len(urls) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")


def main():
    if len(sys.argv) < 2:
        print("Usage: python arxiv_downloader.py <url_file> [max_workers] [output_dir]")
        print("Examples:")
        print("  python arxiv_downloader.py CoT.txt")
        print("  python arxiv_downloader.py CoT.txt 1")
        print("  python arxiv_downloader.py multimodal/arxiv_links.txt 1 multimodal")
        print("WARNING: ArXiv rate limit is 1 request per 3 seconds with 1 connection only!")
        sys.exit(1)
    
    url_file = sys.argv[1]
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Create downloader with specified workers
    downloader = ArxivDownloader(max_workers=max_workers)
    
    print(f"🔧 Configuration:")
    print(f"   Max workers: {max_workers}")
    print(f"   Rate limit: {downloader.min_delay}-{downloader.max_delay} seconds")
    print(f"   Input file: {url_file}")
    if output_dir:
        print(f"   Output directory: {output_dir}")
    if max_workers > 1:
        print(f"⚠️  WARNING: ArXiv allows only 1 concurrent connection!")
        print(f"   Using {max_workers} workers may result in blocked requests.")
    print()
    
    downloader.process_url_file(url_file, output_dir)


if __name__ == "__main__":
    main()