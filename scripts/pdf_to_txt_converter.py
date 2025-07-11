#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF to TXT Converter for ArXiv Papers
Convert PDF papers to TXT format for text processing and translation
Optimized for ArXiv paper collections with parallel processing
"""

import os
import glob
import re
import subprocess
import sys
import time
import logging
import threading
import fcntl
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from contextlib import contextmanager

# Global statistics and progress tracking
conversion_stats = {
    'total': 0,
    'successful': 0,
    'failed': 0,
    'skipped': 0,
    'start_time': None,
    'lock': Lock()
}

# Setup logging
def setup_logging(level=logging.INFO, log_file=None):
    """Setup structured logging with optional file output"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

@contextmanager
def file_lock(file_path, mode='w', timeout=30):
    """Context manager for file locking to prevent concurrent writes"""
    lock_file = f"{file_path}.lock"
    lock_fd = None
    
    try:
        # Create lock file
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        
        # Acquire exclusive lock with timeout
        start_time = time.time()
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except IOError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock for {file_path} within {timeout}s")
                time.sleep(0.1)
        
        # Open actual file for writing
        with open(file_path, mode, encoding='utf-8') as f:
            yield f
            
    except FileExistsError:
        # Lock file already exists, wait for it to be released
        start_time = time.time()
        while os.path.exists(lock_file):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Lock file {lock_file} exists for too long")
            time.sleep(0.1)
        
        # Retry opening the file
        with open(file_path, mode, encoding='utf-8') as f:
            yield f
            
    finally:
        # Release lock and clean up
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                os.unlink(lock_file)
            except (OSError, IOError):
                pass

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.1f}s...")
            time.sleep(delay)
    
    return None

def update_progress(operation, success=True):
    """Thread-safe progress tracking"""
    with conversion_stats['lock']:
        if operation == 'start':
            conversion_stats['start_time'] = time.time()
        elif operation == 'success':
            conversion_stats['successful'] += 1
        elif operation == 'failed':
            conversion_stats['failed'] += 1
        elif operation == 'skipped':
            conversion_stats['skipped'] += 1

def print_progress():
    """Print current progress statistics"""
    with conversion_stats['lock']:
        total_processed = conversion_stats['successful'] + conversion_stats['failed'] + conversion_stats['skipped']
        if conversion_stats['start_time']:
            elapsed = time.time() - conversion_stats['start_time']
            if total_processed > 0:
                avg_time = elapsed / total_processed
                eta = avg_time * (conversion_stats['total'] - total_processed)
                logger.info(f"Progress: {total_processed}/{conversion_stats['total']} "
                          f"(Success: {conversion_stats['successful']}, "
                          f"Failed: {conversion_stats['failed']}, "
                          f"Skipped: {conversion_stats['skipped']}) "
                          f"ETA: {eta:.1f}s")

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file using multiple methods
    """
    text = ""
    
    # Method 1: Try PyPDF2
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            print(f"  - Processing {total_pages} pages with PyPDF2...")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\n--- PAGE {page_num} ---\n"
                        text += page_text + "\n"
                    else:
                        text += f"\n--- PAGE {page_num} ---\n"
                        text += "[IMAGE: Unable to extract text from this page]\n"
                        
                except Exception as e:
                    text += f"\n--- PAGE {page_num} ---\n"
                    text += f"[ERROR: Cannot process this page - {str(e)}]\n"
                    
        return text
                    
    except ImportError:
        pass
    except Exception as e:
        text = f"[ERROR: Cannot read PDF file - {str(e)}]"
        
    # Method 2: Try pdfplumber as fallback
    try:
        import pdfplumber
        print(f"  - Trying pdfplumber as fallback...")
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += f"\n--- PAGE {page_num} ---\n"
                        text += page_text + "\n"
                    else:
                        text += f"\n--- PAGE {page_num} ---\n"
                        text += "[IMAGE: Unable to extract text from this page]\n"
                        
                        # Try to extract tables if text extraction fails
                        tables = page.extract_tables()
                        if tables:
                            text += "[TABLES FOUND - Attempting to extract data]\n"
                            for table_num, table in enumerate(tables, 1):
                                text += f"Table {table_num}:\n"
                                for row in table:
                                    if row:
                                        text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
                                text += "\n"
                        
                except Exception as e:
                    text += f"\n--- PAGE {page_num} ---\n"
                    text += f"[ERROR: Cannot process this page - {str(e)}]\n"
                    
        return text
        
    except ImportError:
        text = "[ERROR: No PDF processing library available. Please install PyPDF2 or pdfplumber]"
    except Exception as e:
        text = f"[ERROR: Cannot read PDF file with pdfplumber - {str(e)}]"
        
    return text

def convert_pdf_to_txt(pdf_path, txt_path, thread_id=None):
    """
    Convert a PDF file to TXT with retry logic and file locking
    """
    thread_prefix = f"[Thread-{thread_id}] " if thread_id else ""
    logger.info(f"{thread_prefix}Converting: {os.path.basename(pdf_path)}")
    
    def _convert():
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(pdf_path)
        
        # Create header for TXT file
        header = f"""# {os.path.basename(pdf_path)}
# Converted from PDF to TXT
# Source path: {pdf_path}
# File size: {os.path.getsize(pdf_path)} bytes

===============================================
PDF FILE CONTENT
===============================================

"""
        
        # Write to TXT file with file locking
        with file_lock(txt_path, 'w') as txt_file:
            txt_file.write(header + extracted_text)
        
        logger.info(f"{thread_prefix}[OK] Created: {os.path.basename(txt_path)}")
        return True
    
    # Use retry mechanism
    try:
        result = retry_with_backoff(_convert, max_retries=3, base_delay=1.0)
        if result:
            update_progress('success')
            return True
        else:
            logger.error(f"{thread_prefix}[ERROR] Failed to convert after retries: {os.path.basename(pdf_path)}")
            update_progress('failed')
            return False
    except Exception as e:
        logger.error(f"{thread_prefix}[ERROR] Conversion error: {str(e)}")
        update_progress('failed')
        return False

def convert_pdf_to_txt_parallel(pdf_files, working_dir, max_workers=4):
    """
    Convert multiple PDF files to TXT in parallel
    """
    if not pdf_files:
        logger.warning("No PDF files to process")
        return 0, 0
    
    # Initialize statistics
    conversion_stats['total'] = len(pdf_files)
    conversion_stats['successful'] = 0
    conversion_stats['failed'] = 0
    conversion_stats['skipped'] = 0
    update_progress('start')
    
    logger.info(f"Starting parallel conversion of {len(pdf_files)} PDFs using {max_workers} workers")
    
    successful = 0
    failed = 0
    skipped = 0
    
    # Create tasks for thread pool
    tasks = []
    for pdf_path in pdf_files:
        pdf_name = Path(pdf_path).stem
        txt_path = os.path.join(working_dir, f"{pdf_name}.txt")
        
        # Check if TXT file already exists
        if os.path.exists(txt_path):
            logger.info(f"File {os.path.basename(txt_path)} already exists. Skipping...")
            skipped += 1
            update_progress('skipped')
            continue
        
        # Double-check: Don't process if there's already a TXT file for this arXiv ID
        pdf_arxiv_id = Path(pdf_path).stem
        # Check for any TXT file that starts with this arXiv ID
        existing_txt_files = glob.glob(os.path.join(working_dir, f"{pdf_arxiv_id}*.txt"))
        if existing_txt_files:
            logger.info(f"TXT file already exists for arXiv ID {pdf_arxiv_id}. Skipping...")
            skipped += 1
            update_progress('skipped')
            continue
        
        tasks.append((pdf_path, txt_path))
    
    if not tasks:
        logger.info("All files already converted. Nothing to do.")
        return skipped, 0
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(convert_pdf_to_txt, pdf_path, txt_path, i % max_workers): 
            (pdf_path, txt_path) for i, (pdf_path, txt_path) in enumerate(tasks)
        }
        
        # Process completed tasks
        for future in as_completed(future_to_file):
            pdf_path, txt_path = future_to_file[future]
            
            try:
                result = future.result()
                if result:
                    successful += 1
                else:
                    failed += 1
                    
                # Print progress every 5 files
                total_processed = successful + failed + skipped
                if total_processed % 5 == 0:
                    print_progress()
                    
            except Exception as e:
                logger.error(f"Task failed for {os.path.basename(pdf_path)}: {str(e)}")
                failed += 1
                update_progress('failed')
    
    # Final statistics
    total_time = time.time() - conversion_stats['start_time']
    logger.info(f"\n" + "=" * 60)
    logger.info("PARALLEL CONVERSION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Successful: {successful} files")
    logger.info(f"Failed: {failed} files")
    logger.info(f"Skipped: {skipped} files")
    logger.info(f"Total: {len(pdf_files)} files")
    logger.info(f"Total time: {total_time:.2f}s")
    if successful > 0:
        logger.info(f"Average time per file: {total_time/successful:.2f}s")
    logger.info(f"Effective workers: {min(max_workers, len(tasks))}")
    
    return successful, failed

def is_arxiv_format(filename):
    """
    Check if filename matches arxiv ID format
    Examples: 2105.12655v2.txt, 2402.01035v2.txt, 2004.13820v2.txt
    """
    # Pattern for arxiv IDs: YYMM.NNNNN or YYMM.NNNNNvN
    # Note: Some papers have 4 or 5 digits after the dot
    pattern = r'^\d{4}\.\d{4,5}(v\d+)?\.txt$'
    return bool(re.match(pattern, filename))

def normalize_paper_name(paper_name):
    """
    Normalize paper name by replacing special characters
    - Replace ':' with '-'
    - Replace spaces with '_'
    - Remove other special characters
    """
    # Remove leading/trailing whitespace
    paper_name = paper_name.strip()
    
    # Replace colons with hyphens
    paper_name = paper_name.replace(':', '-')
    
    # Replace spaces with underscores
    paper_name = paper_name.replace(' ', '_')
    
    # Remove or replace other problematic characters
    paper_name = paper_name.replace('/', '-')
    paper_name = paper_name.replace('\\', '-')
    paper_name = paper_name.replace('?', '')
    paper_name = paper_name.replace('*', '')
    paper_name = paper_name.replace('"', '')
    paper_name = paper_name.replace('<', '')
    paper_name = paper_name.replace('>', '')
    paper_name = paper_name.replace('|', '-')
    paper_name = paper_name.replace('\n', '_')
    paper_name = paper_name.replace('\r', '')
    
    # Replace multiple underscores with single underscore
    paper_name = re.sub(r'_+', '_', paper_name)
    
    # Replace multiple hyphens with single hyphen
    paper_name = re.sub(r'-+', '-', paper_name)
    
    # Remove trailing underscores or hyphens
    paper_name = paper_name.rstrip('_-')
    
    # Limit length to avoid filesystem issues
    if len(paper_name) > 100:
        paper_name = paper_name[:100]
    
    return paper_name

def extract_paper_name_from_txt(txt_file):
    """
    Extract paper name from the first page using grep
    """
    try:
        # Read the file and look for PAGE 1 marker
        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Find the PAGE 1 marker and get lines after it
        page1_marker = "--- PAGE 1 ---"
        page1_index = content.find(page1_marker)
        
        if page1_index != -1:
            # Get text after PAGE 1 marker
            after_page1 = content[page1_index + len(page1_marker):].strip()
            lines = after_page1.split('\n')
            
            # Look for the paper title in the next few lines
            for i in range(min(10, len(lines))):  # Check up to 10 lines
                line = lines[i].strip()
                # Skip empty lines and obvious non-title lines
                if line and not line.startswith('[') and not line.startswith('#'):
                    # This should be the paper title
                    return line
                    
    except Exception as e:
        print(f"    [ERROR] Failed to extract paper name: {str(e)}")
    
    return None

def rename_arxiv_txt_files(working_dir):
    """
    Rename TXT files that match arxiv ID format to include paper name
    """
    print("\n" + "=" * 60)
    print("RENAMING ARXIV TXT FILES")
    print("=" * 60)
    
    # Find all TXT files
    txt_pattern = os.path.join(working_dir, "*.txt")
    txt_files = glob.glob(txt_pattern)
    
    print(f"\nFound {len(txt_files)} TXT files in total")
    
    renamed_count = 0
    skipped_count = 0
    
    # First, show arxiv format files that will be processed
    arxiv_files = [f for f in txt_files if is_arxiv_format(os.path.basename(f))]
    print(f"Found {len(arxiv_files)} files matching arxiv format")
    
    for txt_path in txt_files:
        filename = os.path.basename(txt_path)
        
        # Check if filename matches arxiv format
        if not is_arxiv_format(filename):
            # Only show first few non-arxiv files to avoid clutter
            if skipped_count < 5:
                print(f"Skipping (not arxiv format): {filename}")
            skipped_count += 1
            continue
        
        # Extract arxiv ID (without .txt extension)
        arxiv_id = filename[:-4]  # Remove .txt
        
        # Extract paper name from file content
        paper_name = extract_paper_name_from_txt(txt_path)
        
        if not paper_name:
            print(f"Skipping (no paper name found): {filename}")
            skipped_count += 1
            continue
        
        # Normalize the paper name
        normalized_name = normalize_paper_name(paper_name)
        
        # Create new filename
        new_filename = f"{arxiv_id}-{normalized_name}.txt"
        new_path = os.path.join(working_dir, new_filename)
        
        # Check if new filename already exists
        if os.path.exists(new_path):
            print(f"Skipping (target exists): {filename} -> {new_filename}")
            skipped_count += 1
            continue
        
        # Rename the file
        try:
            os.rename(txt_path, new_path)
            print(f"Renamed: {filename} -> {new_filename}")
            renamed_count += 1
        except Exception as e:
            print(f"Failed to rename {filename}: {str(e)}")
            skipped_count += 1
    
    print(f"\nRenaming complete:")
    print(f"  - Renamed: {renamed_count} files")
    print(f"  - Skipped: {skipped_count} files")

def process_all_collections(max_workers=4):
    """
    Process all collection directories automatically with parallel processing
    """
    base_dir = "."
    collections = [d for d in os.listdir(base_dir) 
                  if os.path.isdir(os.path.join(base_dir, d)) 
                  and not d.startswith('.') 
                  and not d in ['progress', '__pycache__']]
    
    logger.info("=" * 60)
    logger.info("PROCESSING ALL COLLECTIONS WITH PARALLEL CONVERSION")
    logger.info("=" * 60)
    
    total_processed = 0
    
    for collection in collections:
        collection_dir = os.path.join(base_dir, collection)
        pdf_files = glob.glob(os.path.join(collection_dir, "*.pdf"))
        
        if pdf_files:
            logger.info(f"\n📁 Processing collection: {collection} ({len(pdf_files)} PDFs)")
            
            # Convert PDFs to TXT using parallel processing
            successful, failed = convert_pdf_to_txt_parallel(pdf_files, collection_dir, max_workers)
            
            # Rename TXT files
            rename_arxiv_txt_files(collection_dir)
            
            logger.info(f"   ✅ {collection}: {successful}/{len(pdf_files)} files processed")
            total_processed += successful
        else:
            logger.info(f"   ⏭️  {collection}: No PDF files found")
    
    logger.info(f"\n🎉 Total files processed: {total_processed}")

def main():
    """
    Main function to convert all PDFs in directory and rename TXT files
    """
    # Working directory - use current directory
    working_dir = "."
    
    # Check if working directory exists
    if not os.path.exists(working_dir):
        working_dir = os.getcwd()
        print(f"Warning: Default directory not found, using current directory: {working_dir}")
    
    print("=" * 60)
    print("PDF TO TXT CONVERTER FOR ARXIV PAPERS")
    print("=" * 60)
    print(f"Working directory: {working_dir}")
    
    # Auto-detect optimal worker count based on system resources
    cpu_cores = os.cpu_count() or 4
    optimal_workers = min(cpu_cores // 2, 16)  # Use 50% of cores, cap at 16
    max_workers = max(optimal_workers, 4)  # Minimum 4 workers for reasonable performance
    
    logger.info(f"System: {cpu_cores} CPU cores detected")
    logger.info(f"Auto-configured: {max_workers} workers (optimal for your system)")
    
    # Check for command line arguments
    original_choice = None  # Track the original operation choice
    collection_mode = False
    
    if len(sys.argv) > 1:
        # Check for operation choice in arguments
        for arg in sys.argv[1:]:
            arg_lower = arg.lower()
            if arg_lower in ["--convert", "-c"]:
                choice = "1"
                original_choice = "1"
                print("\nMode: Convert PDFs only")
            elif arg_lower in ["--rename", "-r"]:
                choice = "2"
                original_choice = "2"
                print("\nMode: Rename TXT files only")
            elif arg_lower in ["--both", "-b"]:
                choice = "3"
                original_choice = "3"
                print("\nMode: Convert PDFs and rename TXT files")
            elif arg_lower in ["--collection", "-col"]:
                choice = "4"
                collection_mode = True
                print("\nMode: Process specific collection directory")
            elif arg_lower in ["--all", "-a"]:
                choice = "5"
                print("\nMode: Process all collections automatically")
            elif arg_lower.startswith("--workers="):
                try:
                    max_workers = int(arg_lower.split("=")[1])
                    print(f"\nUsing {max_workers} parallel workers")
                except ValueError:
                    print("\nWarning: Invalid worker count, using default (4)")
            elif arg_lower in ["--help", "-h"]:
                print("\nUsage:")
                print("  python3 pdf_to_txt_converter.py [operation] [collection_option] [collection_name]")
                print("\nOperation Options:")
                print("  --convert, -c      Convert PDFs to TXT only")
                print("  --rename, -r       Rename existing TXT files only")
                print("  --both, -b         Convert PDFs and rename TXT files (default)")
                print("\nCollection Options:")
                print("  --collection, -col Process specific collection (e.g., multimodal, CoT, RAG)")
                print("  --all, -a          Process all collections automatically")
                print("\nPerformance Options:")
                print(f"  --workers=N        Number of parallel workers (auto-detected: {max_workers})")
                print("\nExamples:")
                print("  python3 pdf_to_txt_converter.py --all")
                print("  python3 pdf_to_txt_converter.py --rename --collection pruning")
                print(f"  python3 pdf_to_txt_converter.py --both --collection multimodal --workers={min(max_workers + 4, 24)}")
                print("  python3 pdf_to_txt_converter.py --convert --workers=8")
                return
        
        # Set default choice if none specified
        if original_choice is None and not collection_mode and choice != "5":
            choice = "3"  # Default to both convert and rename
            original_choice = "3"
    else:
        # Interactive mode
        print("\nOptions:")
        print("1. Convert PDFs to TXT only")
        print("2. Rename existing TXT files only")
        print("3. Convert PDFs and rename all TXT files")
        print("4. Process specific collection directory")
        print("5. Process all collections automatically")
        
        choice = input("\nEnter your choice (1/2/3/4/5) [default: 3]: ").strip()
        if not choice:
            choice = "3"
    
    # Handle all collections processing
    if choice == "5":
        process_all_collections(max_workers)
        return
    
    # Handle collection-specific processing
    if choice == "4" or collection_mode:
        # Find collection name from arguments
        collection_name = None
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg.lower() in ["--collection", "-col"] and i + 1 < len(sys.argv):
                collection_name = sys.argv[i + 1]
                break
        
        if not collection_name:
            # List available collections
            collections = [d for d in os.listdir(working_dir) 
                          if os.path.isdir(os.path.join(working_dir, d)) 
                          and not d.startswith('.') 
                          and not d in ['progress', '__pycache__']]
            
            print("\nAvailable collections:")
            for i, col in enumerate(collections, 1):
                pdf_count = len(glob.glob(os.path.join(working_dir, col, "*.pdf")))
                print(f"  {i}. {col} ({pdf_count} PDFs)")
            
            collection_name = input("\nEnter collection name: ").strip()
        
        collection_dir = os.path.join(working_dir, collection_name)
        if os.path.exists(collection_dir):
            working_dir = collection_dir
            print(f"Processing collection: {collection_name}")
            # Use original choice if specified, otherwise default to both convert and rename
            if original_choice:
                choice = original_choice
            else:
                choice = "3"  # Default to both convert and rename
        else:
            print(f"Collection '{collection_name}' not found!")
            return
    
    if choice in ["1", "3"]:
        # Find all PDF files
        pdf_pattern = os.path.join(working_dir, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)
        
        if not pdf_files:
            logger.warning("No PDF files found in directory!")
        else:
            logger.info(f"Found {len(pdf_files)} PDF files:")
            for pdf_file in pdf_files:
                logger.info(f"  - {os.path.basename(pdf_file)}")
            
            logger.info("\n" + "=" * 60)
            logger.info("STARTING PARALLEL CONVERSION")
            logger.info("=" * 60)
            
            # Use parallel processing
            successful, failed = convert_pdf_to_txt_parallel(pdf_files, working_dir, max_workers)
            
            if successful > 0:
                logger.info(f"\nTXT files created in directory: {working_dir}")
    
    if choice in ["2", "3"]:
        # Rename arxiv format files to include paper names
        rename_arxiv_txt_files(working_dir)

if __name__ == "__main__":
    main()
