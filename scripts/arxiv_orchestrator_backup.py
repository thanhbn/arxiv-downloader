#!/usr/bin/env python3
"""
ArXiv Orchestrator - Main script for managing the entire PDF download process

This script coordinates the complete workflow:
1. Reads Hugging Face collection URLs
2. Tracks progress with JSON checkpoints
3. Manages PDF downloads using download_arxiv.sh
4. Provides comprehensive status reporting
"""

import os
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import re


class ArxivOrchestrator:
    def __init__(self):
        # Define fixed paths
        self.base_dir = Path(".")
        self.collections_file = self.base_dir / "huggingface_collections_links.txt"
        self.download_script = self.base_dir / "download_arxiv.sh"
        self.progress_dir = self.base_dir / "progress"
        
        # Create progress directory if it doesn't exist
        self.progress_dir.mkdir(exist_ok=True)
        
        # Validate required files exist
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate that all required files and directories exist"""
        if not self.collections_file.exists():
            raise FileNotFoundError(f"Collections file not found: {self.collections_file}")
        
        if not self.download_script.exists():
            raise FileNotFoundError(f"Download script not found: {self.download_script}")
        
        # Make sure download script is executable
        if not os.access(self.download_script, os.X_OK):
            try:
                os.chmod(self.download_script, 0o755)
                print(f"Made {self.download_script} executable")
            except Exception as e:
                raise PermissionError(f"Cannot make download script executable: {e}")
    
    def extract_collection_name(self, url):
        """Extract meaningful collection name from Hugging Face URL"""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # URL format: /collections/username/collection-name-id
        if len(path_parts) >= 3 and path_parts[0] == 'collections':
            collection_part = path_parts[2]
            # Remove the ID part (usually after the last dash followed by hex)
            name_match = re.match(r'^([a-zA-Z0-9\-]+?)-[a-f0-9]+$', collection_part)
            if name_match:
                return name_match.group(1)
            return collection_part
        
        return path_parts[-1] if path_parts else 'unknown'
    
    def get_progress_file_path(self, collection_name):
        """Get the path to the progress file for a collection"""
        return self.progress_dir / f"{collection_name}_progress.json"
    
    def load_progress(self, collection_name):
        """Load progress data for a collection"""
        progress_file = self.get_progress_file_path(collection_name)
        
        if not progress_file.exists():
            # Create default progress
            default_progress = {
                "collection_name": collection_name,
                "status": "pending",
                "arxiv_links_file": str(self.base_dir / collection_name / "arxiv_links.txt"),
                "destination_dir": str(self.base_dir / collection_name),
                "last_updated": datetime.now().isoformat(),
                "error_message": None,
                "total_links": 0,
                "downloaded_count": 0
            }
            self.save_progress(collection_name, default_progress)
            return default_progress
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading progress for {collection_name}: {e}")
            return None
    
    def save_progress(self, collection_name, progress_data):
        """Save progress data for a collection"""
        progress_file = self.get_progress_file_path(collection_name)
        progress_data["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving progress for {collection_name}: {e}")
    
    def get_collection_urls(self):
        """Read and return all collection URLs"""
        collection_urls = []
        try:
            with open(self.collections_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('https://'):
                        collection_urls.append(line)
        except Exception as e:
            print(f"Error reading collections file: {e}")
            return []
        
        return collection_urls
    
    def count_links_in_file(self, links_file_path):
        """Count the number of links in an arxiv_links.txt file"""
        try:
            with open(links_file_path, 'r', encoding='utf-8') as f:
                return len([line for line in f if line.strip()])
        except Exception:
            return 0
    
    def process_collection(self, url):
        """Process a single collection"""
        collection_name = self.extract_collection_name(url)
        print(f"\nProcessing collection: {collection_name}")
        
        # Load current progress
        progress = self.load_progress(collection_name)
        if not progress:
            print(f"  ✗ Failed to load progress for {collection_name}")
            return False
        
        # Check if already completed
        if progress["status"] == "completed":
            print(f"  ✓ Already completed - skipping")
            return True
        
        # Check if arxiv_links.txt exists
        arxiv_links_file = Path(progress["arxiv_links_file"])
        if not arxiv_links_file.exists():
            error_msg = f"ArXiv links file not found: {arxiv_links_file}"
            print(f"  ✗ {error_msg}")
            progress["status"] = "failed_download"
            progress["error_message"] = error_msg
            self.save_progress(collection_name, progress)
            return False
        
        # Count total links
        total_links = self.count_links_in_file(arxiv_links_file)
        progress["total_links"] = total_links
        
        if total_links == 0:
            print(f"  ⚠ No links found in {arxiv_links_file} - marking as completed")
            progress["status"] = "completed"
            self.save_progress(collection_name, progress)
            return True
        
        print(f"  📊 Found {total_links} links to download")
        
        # Update status to downloading
        progress["status"] = "downloading"
        self.save_progress(collection_name, progress)
        
        # Execute download script
        destination_dir = Path(progress["destination_dir"])
        destination_dir.mkdir(exist_ok=True)
        
        try:
            print(f"  🚀 Starting download to {destination_dir}")
            
            # Run download_arxiv.sh with the links file and destination directory
            cmd = [
                str(self.download_script),
                str(arxiv_links_file),
                str(destination_dir)
            ]
            
            # Calculate timeout based on number of links (more conservative)
            # Assume 10-15 seconds per file on average (including delays)
            estimated_time = total_links * 15  # 15 seconds per file
            timeout_seconds = max(3600, estimated_time)  # Minimum 1 hour, or calculated time
            
            print(f"  ⏱️  Estimated download time: {estimated_time//60} minutes")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            if result.returncode == 0:
                print(f"  ✓ Download completed successfully")
                progress["status"] = "completed"
                progress["error_message"] = None
                
                # Count downloaded files
                downloaded_count = len(list(destination_dir.glob("*.pdf")))
                progress["downloaded_count"] = downloaded_count
                print(f"  📁 Downloaded {downloaded_count} PDF files")
                
            else:
                error_msg = f"Download script failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                
                print(f"  ✗ {error_msg}")
                progress["status"] = "failed_download"
                progress["error_message"] = error_msg
            
        except subprocess.TimeoutExpired:
            error_msg = "Download script timed out after 1 hour"
            print(f"  ✗ {error_msg}")
            progress["status"] = "failed_download"
            progress["error_message"] = error_msg
            
        except Exception as e:
            error_msg = f"Error executing download script: {e}"
            print(f"  ✗ {error_msg}")
            progress["status"] = "failed_download"
            progress["error_message"] = error_msg
        
        # Save final progress
        self.save_progress(collection_name, progress)
        
        return progress["status"] == "completed"
    
    def generate_final_report(self):
        """Generate and display final status report"""
        print("\n" + "="*80)
        print("📊 FINAL STATUS REPORT")
        print("="*80)
        
        # Collect all progress files
        progress_files = list(self.progress_dir.glob("*_progress.json"))
        
        if not progress_files:
            print("No progress files found.")
            return
        
        status_counts = {
            "completed": 0,
            "pending": 0,
            "downloading": 0,
            "failed_download": 0
        }
        
        total_links = 0
        total_downloaded = 0
        failed_collections = []
        
        for progress_file in sorted(progress_files):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                
                collection_name = progress.get("collection_name", "unknown")
                status = progress.get("status", "unknown")
                links_count = progress.get("total_links", 0)
                downloaded_count = progress.get("downloaded_count", 0)
                
                status_counts[status] = status_counts.get(status, 0) + 1
                total_links += links_count
                total_downloaded += downloaded_count
                
                # Status icon
                status_icon = {
                    "completed": "✅",
                    "pending": "⏳",
                    "downloading": "🔄",
                    "failed_download": "❌"
                }.get(status, "❓")
                
                print(f"{status_icon} {collection_name:<30} | {status:<15} | {downloaded_count:>4}/{links_count:<4} PDFs")
                
                if status == "failed_download":
                    error_msg = progress.get("error_message", "Unknown error")
                    failed_collections.append((collection_name, error_msg))
                    
            except Exception as e:
                print(f"❓ Error reading {progress_file.name}: {e}")
        
        # Summary statistics
        print("\n" + "-"*80)
        print("📈 SUMMARY STATISTICS")
        print("-"*80)
        total_collections = sum(status_counts.values())
        
        for status, count in status_counts.items():
            percentage = (count / total_collections * 100) if total_collections > 0 else 0
            status_icon = {
                "completed": "✅",
                "pending": "⏳", 
                "downloading": "🔄",
                "failed_download": "❌"
            }.get(status, "❓")
            print(f"{status_icon} {status.replace('_', ' ').title():<20}: {count:>3} ({percentage:5.1f}%)")
        
        print(f"\n📊 Total Collections: {total_collections}")
        print(f"🔗 Total ArXiv Links: {total_links}")
        print(f"📁 Total PDFs Downloaded: {total_downloaded}")
        
        if total_links > 0:
            download_percentage = (total_downloaded / total_links * 100)
            print(f"📈 Download Success Rate: {download_percentage:.1f}%")
        
        # Failed collections details
        if failed_collections:
            print(f"\n❌ FAILED COLLECTIONS ({len(failed_collections)}):")
            print("-"*80)
            for collection_name, error_msg in failed_collections:
                print(f"  • {collection_name}: {error_msg}")
    
    def run(self):
        """Main execution method"""
        print("🚀 ArXiv Orchestrator - Starting PDF Download Process")
        print("="*80)
        
        # Get all collection URLs
        collection_urls = self.get_collection_urls()
        if not collection_urls:
            print("❌ No collection URLs found!")
            return
        
        print(f"📋 Found {len(collection_urls)} collections to process")
        
        # Process each collection
        successful_collections = 0
        failed_collections = 0
        skipped_collections = 0
        
        for i, url in enumerate(collection_urls, 1):
            print(f"\n[{i}/{len(collection_urls)}] Processing collection from URL: {url}")
            
            try:
                # Load progress to check if already completed
                collection_name = self.extract_collection_name(url)
                progress = self.load_progress(collection_name)
                
                if progress and progress.get("status") == "completed":
                    print(f"  ✓ Collection '{collection_name}' already completed - skipping")
                    skipped_collections += 1
                    continue
                
                result = self.process_collection(url)
                if result:
                    successful_collections += 1
                else:
                    failed_collections += 1
                    
            except Exception as e:
                print(f"  ❌ Unexpected error processing collection: {e}")
                failed_collections += 1
            
            # Longer delay between collections to be respectful to ArXiv
            if i < len(collection_urls):
                delay_time = 30  # 30 seconds between collections
                print(f"  💤 Waiting {delay_time} seconds before processing next collection...")
                time.sleep(delay_time)
        
        # Generate final report
        self.generate_final_report()
        
        print(f"\n🏁 Processing completed!")
        print(f"✅ Successful: {successful_collections}")
        print(f"⏩ Skipped (already completed): {skipped_collections}")
        print(f"❌ Failed: {failed_collections}")


def main():
    """Main entry point"""
    try:
        orchestrator = ArxivOrchestrator()
        orchestrator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()