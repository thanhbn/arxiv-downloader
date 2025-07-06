#!/usr/bin/env python3
"""
Check all collections against their arxiv_links.txt files and move misplaced papers to correct folders
Enhanced version with comprehensive logging and progress indicators
"""

import os
import shutil
import re
import logging
import time
from pathlib import Path
from datetime import datetime
import argparse

# Configure logging
def setup_logging(log_level='INFO', log_file=None):
    """Setup logging configuration"""
    log_format = '[%(asctime)s] %(levelname)-8s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[]
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logging.getLogger().addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logging.getLogger().addHandler(file_handler)
        logging.info(f"Logging to file: {log_file}")

def log_progress(current, total, operation="Processing"):
    """Log progress with percentage"""
    percentage = (current / total * 100) if total > 0 else 0
    logging.info(f"{operation} progress: {current}/{total} ({percentage:.1f}%)")

def extract_arxiv_id(url):
    """Extract arXiv ID from URL"""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def find_arxiv_links_files(base_dir, exclude_dirs=None):
    """Find all arxiv_links.txt files in subdirectories"""
    if exclude_dirs is None:
        exclude_dirs = {'progress', '.git'}
    
    logging.info(f"Scanning for arxiv_links.txt files in: {base_dir}")
    logging.info(f"Excluding directories: {exclude_dirs}")
    
    links_files = []
    scanned_dirs = 0
    
    for root, dirs, files in os.walk(base_dir):
        scanned_dirs += 1
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        if 'arxiv_links.txt' in files:
            collection_name = os.path.basename(root)
            links_files.append((collection_name, root, os.path.join(root, 'arxiv_links.txt')))
            logging.debug(f"Found arxiv_links.txt in: {collection_name}/")
    
    logging.info(f"Scanned {scanned_dirs} directories, found {len(links_files)} collections with arxiv_links.txt")
    return links_files

def find_paper_globally(arxiv_id, base_dir, exclude_dirs=None):
    """Find paper PDF file in any subdirectory"""
    if exclude_dirs is None:
        exclude_dirs = {'progress', '.git'}
    
    pdf_filename = f"{arxiv_id}.pdf"
    found_locations = []
    
    logging.debug(f"Searching globally for: {pdf_filename}")
    
    for root, dirs, files in os.walk(base_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        if pdf_filename in files:
            location = os.path.join(root, pdf_filename)
            found_locations.append(location)
            logging.debug(f"Found {pdf_filename} at: {os.path.relpath(location, base_dir)}")
    
    if found_locations:
        logging.debug(f"Found {arxiv_id}.pdf in {len(found_locations)} location(s)")
    else:
        logging.debug(f"Paper {arxiv_id}.pdf not found anywhere")
    
    return found_locations

def read_arxiv_links(links_file_path):
    """Read and parse arxiv_links.txt file"""
    logging.debug(f"Reading arxiv_links.txt: {links_file_path}")
    
    try:
        with open(links_file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        logging.debug(f"Read {len(urls)} URLs from file")
        
        arxiv_ids = []
        invalid_urls = 0
        
        for url in urls:
            arxiv_id = extract_arxiv_id(url)
            if arxiv_id:
                arxiv_ids.append(arxiv_id)
            else:
                invalid_urls += 1
                logging.warning(f"Could not extract arXiv ID from: {url}")
        
        if invalid_urls > 0:
            logging.warning(f"Found {invalid_urls} invalid URLs in {links_file_path}")
        
        logging.debug(f"Extracted {len(arxiv_ids)} valid arXiv IDs")
        return arxiv_ids
        
    except Exception as e:
        logging.error(f"Error reading {links_file_path}: {e}")
        return []

def check_and_move_papers(base_dir, dry_run=True, collections_filter=None, verbose=False):
    """Check all collections and move misplaced papers"""
    start_time = time.time()
    
    logging.info("=" * 80)
    logging.info("ARXIV PAPERS ORGANIZATION SCRIPT")
    logging.info("=" * 80)
    logging.info(f"Base directory: {base_dir}")
    logging.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    logging.info(f"Verbose logging: {verbose}")
    
    os.chdir(base_dir)
    
    # Find all arxiv_links.txt files
    links_files = find_arxiv_links_files(base_dir)
    
    if collections_filter:
        # Filter collections if specified
        original_count = len(links_files)
        links_files = [(name, path, links) for name, path, links in links_files 
                      if name in collections_filter]
        logging.info(f"Filtered from {original_count} to {len(links_files)} collections")
        logging.info(f"Collections to process: {[name for name, _, _ in links_files]}")
    
    if not links_files:
        logging.warning("No collections found to process!")
        return
    
    # Initialize counters
    total_moved = 0
    total_missing = 0
    total_correct = 0
    total_extra = 0
    collections_processed = 0
    errors_count = 0
    
    # Store collection statistics for final report
    collection_stats = []
    
    # Process each collection
    for idx, (collection_name, collection_path, links_file_path) in enumerate(links_files, 1):
        logging.info("=" * 60)
        logging.info(f"Processing collection {idx}/{len(links_files)}: {collection_name}")
        logging.info(f"Path: {collection_path}")
        
        # Read expected arxiv IDs
        expected_ids = read_arxiv_links(links_file_path)
        if not expected_ids:
            logging.warning(f"No valid arXiv IDs found in {collection_name}, skipping...")
            continue
        
        collections_processed += 1
        logging.info(f"Expected papers: {len(expected_ids)}")
        
        # Check current papers in collection folder
        try:
            current_papers = [f.replace('.pdf', '') for f in os.listdir(collection_path) 
                             if f.endswith('.pdf')]
        except Exception as e:
            logging.error(f"Error listing files in {collection_path}: {e}")
            errors_count += 1
            continue
        
        logging.info(f"Current papers in folder: {len(current_papers)}")
        
        # Find missing and extra papers
        missing_ids = set(expected_ids) - set(current_papers)
        extra_ids = set(current_papers) - set(expected_ids)
        correct_ids = set(current_papers) & set(expected_ids)
        
        logging.info(f"✓ Correct papers: {len(correct_ids)}")
        logging.info(f"✗ Missing papers: {len(missing_ids)}")
        logging.info(f"? Extra papers: {len(extra_ids)}")
        
        total_correct += len(correct_ids)
        total_missing += len(missing_ids)
        total_extra += len(extra_ids)
        
        # Handle missing papers
        if missing_ids:
            logging.info(f"Searching for {len(missing_ids)} missing papers...")
            moved_count = 0
            not_found_count = 0
            
            for paper_idx, arxiv_id in enumerate(missing_ids, 1):
                if verbose:
                    log_progress(paper_idx, len(missing_ids), "Paper search")
                
                # Find paper globally
                locations = find_paper_globally(arxiv_id, base_dir)
                if locations:
                    # Use the first location found
                    source_path = locations[0]
                    source_dir = os.path.dirname(source_path)
                    source_collection = os.path.basename(source_dir)
                    target_path = os.path.join(collection_path, f"{arxiv_id}.pdf")
                    
                    if dry_run:
                        logging.info(f"  [DRY RUN] Would move {arxiv_id}.pdf: {source_collection}/ → {collection_name}/")
                        moved_count += 1
                    else:
                        try:
                            shutil.move(source_path, target_path)
                            logging.info(f"  ✓ Moved {arxiv_id}.pdf: {source_collection}/ → {collection_name}/")
                            moved_count += 1
                            total_moved += 1
                        except Exception as e:
                            logging.error(f"  ✗ Error moving {arxiv_id}.pdf: {e}")
                            errors_count += 1
                    
                    # Show additional locations if found
                    if len(locations) > 1:
                        other_locations = [os.path.relpath(loc, base_dir) for loc in locations[1:]]
                        logging.info(f"    Note: Also found in {len(locations)-1} other location(s): {other_locations}")
                else:
                    logging.warning(f"  ✗ Paper {arxiv_id}.pdf not found anywhere")
                    not_found_count += 1
            
            if moved_count > 0:
                if dry_run:
                    logging.info(f"Would move {moved_count} papers to {collection_name}/")
                else:
                    logging.info(f"Successfully moved {moved_count} papers to {collection_name}/")
            
            if not_found_count > 0:
                logging.warning(f"{not_found_count} papers not found anywhere")
        
        # Handle extra papers
        if extra_ids:
            logging.info(f"Extra papers in {collection_name}/ (not in arxiv_links.txt):")
            for arxiv_id in list(extra_ids)[:10]:  # Show first 10
                logging.info(f"  ? {arxiv_id}.pdf")
            if len(extra_ids) > 10:
                logging.info(f"  ... and {len(extra_ids) - 10} more extra papers")
        
        # Collection summary
        completion_rate = len(correct_ids) / len(expected_ids) * 100 if expected_ids else 0
        logging.info(f"Collection completion rate: {completion_rate:.1f}% ({len(correct_ids)}/{len(expected_ids)})")
        
        # Store collection statistics
        collection_stats.append({
            'name': collection_name,
            'expected': len(expected_ids),
            'current': len(current_papers),
            'correct': len(correct_ids),
            'missing': len(missing_ids),
            'extra': len(extra_ids),
            'completion_rate': completion_rate
        })
    
    # Final summary
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    logging.info("=" * 80)
    logging.info("FINAL SUMMARY")
    logging.info("=" * 80)
    logging.info(f"⏱️  Total execution time: {elapsed_time:.2f} seconds")
    logging.info(f"📁 Collections found: {len(links_files)}")
    logging.info(f"📁 Collections processed: {collections_processed}")
    logging.info(f"✓  Papers in correct locations: {total_correct}")
    logging.info(f"✗  Papers missing: {total_missing}")
    logging.info(f"?  Extra papers found: {total_extra}")
    logging.info(f"❌ Errors encountered: {errors_count}")
    
    if dry_run:
        logging.info(f"📦 Papers that would be moved: {total_moved}")
        logging.info("")
        logging.info("To actually move papers, run with --execute flag")
    else:
        logging.info(f"📦 Papers moved: {total_moved}")
        if total_moved > 0:
            logging.info("✅ Paper organization completed successfully!")
        else:
            logging.info("ℹ️  No papers needed to be moved")
    
    if errors_count > 0:
        logging.warning(f"⚠️  {errors_count} errors occurred during processing")
    
    # Collection statistics table
    if collection_stats:
        logging.info("")
        logging.info("📊 COLLECTION STATISTICS")
        logging.info("=" * 80)
        
        # Sort by completion rate (descending) then by name
        collection_stats.sort(key=lambda x: (-x['completion_rate'], x['name']))
        
        # Table header
        logging.info(f"{'Collection':<20} {'Expected':<8} {'Current':<8} {'Correct':<8} {'Missing':<8} {'Extra':<8} {'Complete':<10}")
        logging.info("-" * 80)
        
        # Table rows
        for stats in collection_stats:
            logging.info(f"{stats['name']:<20} "
                        f"{stats['expected']:<8} "
                        f"{stats['current']:<8} "
                        f"{stats['correct']:<8} "
                        f"{stats['missing']:<8} "
                        f"{stats['extra']:<8} "
                        f"{stats['completion_rate']:<10.1f}%")
        
        logging.info("-" * 80)
        
        # Summary statistics
        total_expected = sum(s['expected'] for s in collection_stats)
        total_current = sum(s['current'] for s in collection_stats)
        total_correct_overall = sum(s['correct'] for s in collection_stats)
        total_missing_overall = sum(s['missing'] for s in collection_stats)
        total_extra_overall = sum(s['extra'] for s in collection_stats)
        overall_completion = (total_correct_overall / total_expected * 100) if total_expected > 0 else 0
        
        logging.info(f"{'TOTAL':<20} "
                    f"{total_expected:<8} "
                    f"{total_current:<8} "
                    f"{total_correct_overall:<8} "
                    f"{total_missing_overall:<8} "
                    f"{total_extra_overall:<8} "
                    f"{overall_completion:<10.1f}%")
        
        # Top/bottom collections
        logging.info("")
        complete_collections = [s for s in collection_stats if s['completion_rate'] == 100.0]
        incomplete_collections = [s for s in collection_stats if s['completion_rate'] < 100.0]
        
        if complete_collections:
            logging.info(f"✅ Complete collections ({len(complete_collections)}): " + 
                        ", ".join([s['name'] for s in complete_collections[:10]]))
            if len(complete_collections) > 10:
                logging.info(f"   ... and {len(complete_collections) - 10} more complete collections")
        
        if incomplete_collections:
            logging.info(f"❌ Incomplete collections ({len(incomplete_collections)}): " + 
                        ", ".join([f"{s['name']} ({s['completion_rate']:.1f}%)" 
                                 for s in incomplete_collections[:5]]))
            if len(incomplete_collections) > 5:
                logging.info(f"   ... and {len(incomplete_collections) - 5} more incomplete collections")

def main():
    parser = argparse.ArgumentParser(
        description='Check and move papers to correct collections with enhanced logging',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with basic logging
  python3 %(prog)s
  
  # Execute with verbose logging
  python3 %(prog)s --execute --verbose
  
  # Process specific collections with debug logging
  python3 %(prog)s --collections multimodal rag --log-level DEBUG
  
  # Save log to file
  python3 %(prog)s --log-file arxiv_organization.log
        """
    )
    
    parser.add_argument('--execute', action='store_true', 
                       help='Actually move files (default is dry run)')
    parser.add_argument('--base-dir', default='/home/admin88/arxiv-downloader',
                       help='Base directory to search')
    parser.add_argument('--collections', nargs='+',
                       help='Specific collections to process (default: all)')
    parser.add_argument('--exclude', nargs='+', default=['progress', '.git'],
                       help='Directories to exclude')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Set logging level')
    parser.add_argument('--log-file', 
                       help='Save log to file (e.g., arxiv_organization.log)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose progress reporting')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Log startup information
    logging.info(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Command line arguments: {vars(args)}")
    
    try:
        check_and_move_papers(
            base_dir=args.base_dir,
            dry_run=not args.execute,
            collections_filter=args.collections,
            verbose=args.verbose
        )
    except KeyboardInterrupt:
        logging.warning("Script interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        logging.info("Script execution completed")

if __name__ == "__main__":
    main()