#!/usr/bin/env python3
"""
Google Drive PDF Uploader
Uploads all PDF files in the repository to Google Drive with organized folder structure.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Try to setup environment
try:
    # Import common environment setup if available
    from scripts.setup_env_common import setup_arxiv_env
    setup_arxiv_env(quiet=True)
except ImportError:
    # Fallback to manual setup if common script not available
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Activate virtual environment if available
    venv_activate = os.path.join(project_root, '.venv', 'bin', 'activate')
    if os.path.exists(venv_activate):
        # This is a workaround since we can't source in Python
        # The environment should already be activated by direnv or manual activation
        pass

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Please run: pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

# Configuration
SERVICE_ACCOUNT_FILE = 'service-account-key.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
DRIVE_FOLDER_ID = 'YOUR_DRIVE_FOLDER_ID'  # Replace with your Google Drive folder ID

# Global variables for progress tracking
upload_lock = threading.Lock()
upload_stats = {
    'total': 0,
    'completed': 0,
    'failed': 0,
    'skipped': 0
}

class GoogleDriveUploader:
    def __init__(self, service_account_file: str, folder_id: str):
        """Initialize Google Drive uploader."""
        self.folder_id = folder_id
        self.service = self._authenticate(service_account_file)
        self.folder_cache = {}
        
    def _authenticate(self, service_account_file: str):
        """Authenticate with Google Drive API."""
        if not os.path.exists(service_account_file):
            raise FileNotFoundError(f"Service account file not found: {service_account_file}")
            
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES)
        return build('drive', 'v3', credentials=credentials)
    
    def create_folder(self, folder_name: str, parent_id: str) -> str:
        """Create a folder in Google Drive."""
        # Check if folder already exists
        cache_key = f"{parent_id}:{folder_name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]
            
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and parents in '{parent_id}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                self.folder_cache[cache_key] = folder_id
                return folder_id
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'parents': [parent_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            self.folder_cache[cache_key] = folder_id
            return folder_id
            
        except HttpError as error:
            print(f"Error creating folder '{folder_name}': {error}")
            return parent_id
    
    def file_exists(self, filename: str, parent_id: str) -> bool:
        """Check if file already exists in Google Drive."""
        try:
            query = f"name='{filename}' and parents in '{parent_id}'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            return len(files) > 0
        except HttpError as error:
            print(f"Error checking file existence: {error}")
            return False
    
    def upload_file(self, file_path: str, collection_name: str, skip_existing: bool = True) -> bool:
        """Upload a single PDF file to Google Drive."""
        try:
            filename = os.path.basename(file_path)
            
            # Create collection folder
            collection_folder_id = self.create_folder(collection_name, self.folder_id)
            
            # Check if file already exists
            if skip_existing and self.file_exists(filename, collection_folder_id):
                with upload_lock:
                    upload_stats['skipped'] += 1
                print(f"⏭️  Skipped (exists): {collection_name}/{filename}")
                return True
            
            # Upload file
            file_metadata = {
                'name': filename,
                'parents': [collection_folder_id]
            }
            
            media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=True)
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            # Execute upload with progress
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress % 25 == 0:  # Show progress every 25%
                        print(f"  📤 Uploading {filename}: {progress}%")
            
            with upload_lock:
                upload_stats['completed'] += 1
            
            print(f"✅ Uploaded: {collection_name}/{filename}")
            return True
            
        except HttpError as error:
            with upload_lock:
                upload_stats['failed'] += 1
            print(f"❌ Failed to upload {file_path}: {error}")
            return False
        except Exception as error:
            with upload_lock:
                upload_stats['failed'] += 1
            print(f"❌ Unexpected error uploading {file_path}: {error}")
            return False

def find_pdf_files(root_dir: str) -> Dict[str, List[str]]:
    """Find all PDF files organized by collection."""
    pdf_files = {}
    root_path = Path(root_dir)
    
    for pdf_file in root_path.rglob("*.pdf"):
        # Get collection name (parent directory)
        collection = pdf_file.parent.name
        if collection == root_path.name:
            collection = "root"
        
        if collection not in pdf_files:
            pdf_files[collection] = []
        
        pdf_files[collection].append(str(pdf_file))
    
    return pdf_files

def upload_worker(uploader: GoogleDriveUploader, file_path: str, collection: str, skip_existing: bool):
    """Worker function for parallel uploads."""
    return uploader.upload_file(file_path, collection, skip_existing)

def print_progress():
    """Print current upload progress."""
    with upload_lock:
        total = upload_stats['total']
        completed = upload_stats['completed']
        failed = upload_stats['failed']
        skipped = upload_stats['skipped']
        processed = completed + failed + skipped
        
        if total > 0:
            progress = (processed / total) * 100
            print(f"\n📊 Progress: {processed}/{total} ({progress:.1f}%) | "
                  f"✅{completed} ❌{failed} ⏭️{skipped}")

def main():
    parser = argparse.ArgumentParser(description="Upload PDF files to Google Drive")
    parser.add_argument("--folder-id", required=True, 
                       help="Google Drive folder ID to upload to")
    parser.add_argument("--service-account", default=SERVICE_ACCOUNT_FILE,
                       help="Path to service account JSON file")
    parser.add_argument("--collection", 
                       help="Upload only specific collection")
    parser.add_argument("--workers", type=int, default=3,
                       help="Number of parallel upload workers (default: 3)")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                       help="Skip files that already exist (default: True)")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be uploaded without actually uploading")
    
    args = parser.parse_args()
    
    if args.overwrite:
        args.skip_existing = False
    
    print("🚀 ArXiv PDF to Google Drive Uploader")
    print("=" * 50)
    
    # Find all PDF files
    print("📁 Scanning for PDF files...")
    pdf_collections = find_pdf_files(".")
    
    if not pdf_collections:
        print("❌ No PDF files found!")
        return
    
    # Filter by collection if specified
    if args.collection:
        if args.collection in pdf_collections:
            pdf_collections = {args.collection: pdf_collections[args.collection]}
        else:
            print(f"❌ Collection '{args.collection}' not found!")
            print(f"Available collections: {', '.join(pdf_collections.keys())}")
            return
    
    # Calculate totals
    total_files = sum(len(files) for files in pdf_collections.values())
    upload_stats['total'] = total_files
    
    print(f"📋 Found {total_files} PDF files in {len(pdf_collections)} collections:")
    for collection, files in pdf_collections.items():
        print(f"  📂 {collection}: {len(files)} files")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No files will be uploaded")
        return
    
    # Initialize uploader
    try:
        uploader = GoogleDriveUploader(args.service_account, args.folder_id)
        print(f"✅ Connected to Google Drive")
    except Exception as e:
        print(f"❌ Failed to connect to Google Drive: {e}")
        return
    
    # Start uploads
    print(f"\n🔄 Starting upload with {args.workers} workers...")
    print(f"⚙️  Skip existing: {args.skip_existing}")
    
    start_time = time.time()
    
    # Prepare all upload tasks
    upload_tasks = []
    for collection, files in pdf_collections.items():
        for file_path in files:
            upload_tasks.append((file_path, collection))
    
    # Execute uploads with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(upload_worker, uploader, file_path, collection, args.skip_existing): (file_path, collection)
            for file_path, collection in upload_tasks
        }
        
        # Process completed tasks
        for future in as_completed(future_to_task):
            file_path, collection = future_to_task[future]
            try:
                success = future.result()
                # Progress is printed by individual workers
            except Exception as exc:
                with upload_lock:
                    upload_stats['failed'] += 1
                print(f"❌ Upload task failed for {file_path}: {exc}")
            
            # Print progress every 10 files
            if (upload_stats['completed'] + upload_stats['failed'] + upload_stats['skipped']) % 10 == 0:
                print_progress()
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 50)
    print("📊 UPLOAD SUMMARY")
    print("=" * 50)
    print(f"⏱️  Duration: {duration:.1f} seconds")
    print(f"📁 Total files: {upload_stats['total']}")
    print(f"✅ Uploaded: {upload_stats['completed']}")
    print(f"⏭️  Skipped: {upload_stats['skipped']}")
    print(f"❌ Failed: {upload_stats['failed']}")
    
    if upload_stats['completed'] > 0:
        avg_time = duration / upload_stats['completed']
        print(f"⚡ Average upload time: {avg_time:.1f} seconds/file")
    
    if upload_stats['failed'] > 0:
        print(f"\n⚠️  {upload_stats['failed']} files failed to upload. Check the logs above for details.")
    else:
        print(f"\n🎉 All files processed successfully!")

if __name__ == "__main__":
    main()