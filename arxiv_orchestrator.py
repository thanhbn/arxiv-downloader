#!/usr/bin/env python3
"""
ArXiv Orchestrator Optimized - Parallel collection processing with async support

This optimized version provides:
1. Concurrent collection processing
2. Async/await pattern for better I/O handling
3. Improved progress tracking
4. Better error handling and recovery
5. Configurable parallelism levels
"""

import os
import json
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import aiofiles


class ArxivOrchestratorOptimized:
    def __init__(self, max_concurrent_collections=1, max_workers_per_collection=1):
        # Define fixed paths
        self.base_dir = Path("/home/admin88/arxiv-downloader")
        self.collections_file = self.base_dir / "huggingface_collections_links.txt"
        self.download_script = self.base_dir / "download_arxiv.sh"
        self.progress_dir = self.base_dir / "progress"
        
        # Configuration
        self.max_concurrent_collections = max_concurrent_collections
        self.max_workers_per_collection = max_workers_per_collection
        
        # Thread-safe stats
        self.stats_lock = Lock()
        self.stats = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_links": 0,
            "total_downloaded": 0
        }
        
        # Create progress directory if it doesn't exist
        self.progress_dir.mkdir(exist_ok=True)
        
        # Validate required files exist
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate that all required files and directories exist"""
        if not self.collections_file.exists():
            raise FileNotFoundError(f"Collections file not found: {self.collections_file}")
        
        # Check if main downloader exists, if not use shell script
        current_downloader = self.base_dir / "arxiv_downloader.py"
        if not current_downloader.exists():
            if not self.download_script.exists():
                raise FileNotFoundError(f"No download script found: {self.download_script}")
            else:
                # Make sure download script is executable
                if not os.access(self.download_script, os.X_OK):
                    try:
                        os.chmod(self.download_script, 0o755)
                        print(f"✅ Made {self.download_script} executable")
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
    
    async def load_progress(self, collection_name):
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
                "downloaded_count": 0,
                "start_time": None,
                "end_time": None
            }
            await self.save_progress(collection_name, default_progress)
            return default_progress
        
        try:
            async with aiofiles.open(progress_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            print(f"❌ Error loading progress for {collection_name}: {e}")
            return None
    
    async def save_progress(self, collection_name, progress_data):
        """Save progress data for a collection"""
        progress_file = self.get_progress_file_path(collection_name)
        progress_data["last_updated"] = datetime.now().isoformat()
        
        try:
            async with aiofiles.open(progress_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(progress_data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"❌ Error saving progress for {collection_name}: {e}")
    
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
            print(f"❌ Error reading collections file: {e}")
            return []
        
        return collection_urls
    
    def count_links_in_file(self, links_file_path):
        """Count the number of links in an arxiv_links.txt file"""
        try:
            with open(links_file_path, 'r', encoding='utf-8') as f:
                return len([line for line in f if line.strip()])
        except Exception:
            return 0
    
    async def run_download_command(self, collection_name, arxiv_links_file, destination_dir, total_links):
        """Run the download command asynchronously"""
        try:
            # Use the current arxiv_downloader.py (now optimized)
            current_downloader = self.base_dir / "arxiv_downloader.py"
            if current_downloader.exists():
                cmd = [
                    sys.executable,
                    str(current_downloader),
                    str(arxiv_links_file),
                    str(self.max_workers_per_collection),
                    str(destination_dir)
                ]
            else:
                cmd = [
                    str(self.download_script),
                    str(arxiv_links_file),
                    str(destination_dir)
                ]
            
            print(f"🚀 [{collection_name}] Starting download with command: {' '.join(cmd)}")
            
            # Calculate timeout based on number of links
            estimated_time = total_links * 8  # 8 seconds per file on average with parallelism
            timeout_seconds = max(1800, estimated_time)  # Minimum 30 minutes
            
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_dir)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
                
                if process.returncode == 0:
                    print(f"✅ [{collection_name}] Download completed successfully")
                    return True, None
                else:
                    error_msg = f"Download failed with return code {process.returncode}"
                    if stderr:
                        error_msg += f": {stderr.decode()}"
                    return False, error_msg
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, f"Download timed out after {timeout_seconds} seconds"
                
        except Exception as e:
            return False, f"Error executing download command: {e}"
    
    async def process_collection(self, url, semaphore):
        """Process a single collection with concurrency control"""
        async with semaphore:
            collection_name = self.extract_collection_name(url)
            print(f"\n🔄 Processing collection: {collection_name}")
            
            # Load current progress
            progress = await self.load_progress(collection_name)
            if not progress:
                print(f"❌ [{collection_name}] Failed to load progress")
                return False
            
            # Check if already completed
            if progress["status"] == "completed":
                print(f"✅ [{collection_name}] Already completed - skipping")
                with self.stats_lock:
                    self.stats["skipped"] += 1
                return True
            
            # Check if arxiv_links.txt exists
            arxiv_links_file = Path(progress["arxiv_links_file"])
            if not arxiv_links_file.exists():
                error_msg = f"ArXiv links file not found: {arxiv_links_file}"
                print(f"❌ [{collection_name}] {error_msg}")
                progress["status"] = "failed_download"
                progress["error_message"] = error_msg
                await self.save_progress(collection_name, progress)
                return False
            
            # Count total links
            total_links = self.count_links_in_file(arxiv_links_file)
            progress["total_links"] = total_links
            
            if total_links == 0:
                print(f"⚠️  [{collection_name}] No links found - marking as completed")
                progress["status"] = "completed"
                await self.save_progress(collection_name, progress)
                return True
            
            print(f"📊 [{collection_name}] Found {total_links} links to download")
            
            # Update status to downloading
            progress["status"] = "downloading"
            progress["start_time"] = datetime.now().isoformat()
            await self.save_progress(collection_name, progress)
            
            # Create destination directory
            destination_dir = Path(progress["destination_dir"])
            destination_dir.mkdir(exist_ok=True)
            
            # Execute download
            success, error_msg = await self.run_download_command(
                collection_name, arxiv_links_file, destination_dir, total_links
            )
            
            # Update progress based on result
            if success:
                progress["status"] = "completed"
                progress["error_message"] = None
                progress["end_time"] = datetime.now().isoformat()
                
                # Count downloaded files
                downloaded_count = len(list(destination_dir.glob("*.pdf")))
                progress["downloaded_count"] = downloaded_count
                
                print(f"✅ [{collection_name}] Downloaded {downloaded_count} PDF files")
                
                with self.stats_lock:
                    self.stats["successful"] += 1
                    self.stats["total_links"] += total_links
                    self.stats["total_downloaded"] += downloaded_count
                    
            else:
                progress["status"] = "failed_download"
                progress["error_message"] = error_msg
                progress["end_time"] = datetime.now().isoformat()
                
                print(f"❌ [{collection_name}] {error_msg}")
                
                with self.stats_lock:
                    self.stats["failed"] += 1
            
            # Save final progress
            await self.save_progress(collection_name, progress)
            
            return success
    
    async def process_all_collections(self):
        """Process all collections concurrently"""
        print(f"🚀 ArXiv Orchestrator Optimized - Starting parallel processing")
        print(f"   Max concurrent collections: {self.max_concurrent_collections}")
        print(f"   Max workers per collection: {self.max_workers_per_collection}")
        print("="*80)
        
        # Get all collection URLs
        collection_urls = self.get_collection_urls()
        if not collection_urls:
            print("❌ No collection URLs found!")
            return
        
        print(f"📋 Found {len(collection_urls)} collections to process")
        
        # Create semaphore to limit concurrent collections
        semaphore = asyncio.Semaphore(self.max_concurrent_collections)
        
        # Create tasks for all collections
        tasks = [
            self.process_collection(url, semaphore)
            for url in collection_urls
        ]
        
        # Process all collections concurrently
        start_time = time.time()
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Exception in collection {i+1}: {result}")
                    with self.stats_lock:
                        self.stats["failed"] += 1
                        
        except Exception as e:
            print(f"❌ Error in parallel processing: {e}")
        
        elapsed_time = time.time() - start_time
        
        # Generate final report
        await self.generate_final_report(elapsed_time)
    
    async def generate_final_report(self, elapsed_time):
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
                async with aiofiles.open(progress_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    progress = json.loads(content)
                
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
                
                # Calculate processing time if available
                time_info = ""
                if progress.get("start_time") and progress.get("end_time"):
                    try:
                        start_dt = datetime.fromisoformat(progress["start_time"])
                        end_dt = datetime.fromisoformat(progress["end_time"])
                        duration = (end_dt - start_dt).total_seconds()
                        time_info = f" ({duration:.1f}s)"
                    except:
                        pass
                
                print(f"{status_icon} {collection_name:<30} | {status:<15} | {downloaded_count:>4}/{links_count:<4} PDFs{time_info}")
                
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
        print(f"⏱️  Total Processing Time: {elapsed_time:.1f} seconds")
        
        if total_links > 0:
            download_percentage = (total_downloaded / total_links * 100)
            print(f"📈 Download Success Rate: {download_percentage:.1f}%")
            
            # Calculate performance metrics
            avg_time_per_file = elapsed_time / total_links if total_links > 0 else 0
            print(f"🚀 Average Time per File: {avg_time_per_file:.2f} seconds")
        
        # Performance comparison
        print(f"\n🏆 PERFORMANCE IMPROVEMENT:")
        if total_links > 0:
            old_estimated_time = total_links * 1.5  # Old sequential approach
            improvement = ((old_estimated_time - elapsed_time) / old_estimated_time * 100)
            print(f"   Sequential time estimate: {old_estimated_time:.1f} seconds")
            print(f"   Parallel processing time: {elapsed_time:.1f} seconds")
            print(f"   Speed improvement: {improvement:.1f}%")
        
        # Failed collections details
        if failed_collections:
            print(f"\n❌ FAILED COLLECTIONS ({len(failed_collections)}):")
            print("-"*80)
            for collection_name, error_msg in failed_collections:
                print(f"  • {collection_name}: {error_msg}")


async def main():
    """Main entry point"""
    try:
        # Parse command line arguments  
        max_concurrent_collections = 1
        max_workers_per_collection = 1
        
        if len(sys.argv) > 1:
            max_concurrent_collections = int(sys.argv[1])
        if len(sys.argv) > 2:
            max_workers_per_collection = int(sys.argv[2])
        
        orchestrator = ArxivOrchestratorOptimized(
            max_concurrent_collections=max_concurrent_collections,
            max_workers_per_collection=max_workers_per_collection
        )
        
        await orchestrator.process_all_collections()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())