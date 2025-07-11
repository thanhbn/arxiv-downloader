#!/usr/bin/env python3
"""
ArXiv Duplicate Analyzer

This script analyzes all arxiv_links.txt files in the directory and its subdirectories to:
1. Find all arxiv_links.txt files
2. Extract all arXiv URLs from these files
3. Count total URLs found
4. Count unique URLs (deduplicated)
5. Count duplicate URLs and identify which ones are duplicated
6. Report summary statistics

Usage:
    python arxiv_duplicate_analyzer.py [--verbose] [--output-file FILE]
"""

import os
import re
import argparse
from collections import defaultdict, Counter
from pathlib import Path


def extract_arxiv_id(url):
    """Extract arXiv ID from URL using regex pattern."""
    # Pattern to match arXiv IDs: YYMM.NNNNN or YYMM.NNNN
    pattern = r'(\d{4}\.\d{4,5})'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def find_arxiv_links_files(root_dir):
    """Find all arxiv_links.txt files in the directory tree."""
    arxiv_files = []
    for root, dirs, files in os.walk(root_dir):
        if 'arxiv_links.txt' in files:
            arxiv_files.append(os.path.join(root, 'arxiv_links.txt'))
    return sorted(arxiv_files)


def read_arxiv_file(file_path):
    """Read URLs from an arxiv_links.txt file."""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle different formats: plain URL or numbered lines
                    if '→' in line:
                        # Format: "1→https://arxiv.org/pdf/1706.03762.pdf"
                        url = line.split('→', 1)[1].strip()
                    elif line.startswith('http'):
                        # Plain URL format
                        url = line
                    else:
                        continue
                    
                    if 'arxiv.org' in url:
                        urls.append(url)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return urls


def analyze_arxiv_files(root_dir, verbose=False):
    """Analyze all arxiv_links.txt files and find duplicates."""
    print("ArXiv Duplicate Analysis")
    print("=" * 50)
    
    # Find all arxiv_links.txt files
    arxiv_files = find_arxiv_links_files(root_dir)
    print(f"Found {len(arxiv_files)} arxiv_links.txt files")
    
    if verbose:
        print("\nFiles found:")
        for i, file_path in enumerate(arxiv_files, 1):
            rel_path = os.path.relpath(file_path, root_dir)
            print(f"  {i:3d}. {rel_path}")
    
    # Process all files
    all_urls = []
    file_url_counts = {}
    arxiv_id_to_collections = defaultdict(list)
    collection_stats = {}
    
    print(f"\nProcessing {len(arxiv_files)} files...")
    
    for file_path in arxiv_files:
        collection_name = os.path.basename(os.path.dirname(file_path))
        if collection_name == os.path.basename(root_dir):
            collection_name = "root"
        
        urls = read_arxiv_file(file_path)
        file_url_counts[file_path] = len(urls)
        collection_stats[collection_name] = len(urls)
        
        for url in urls:
            all_urls.append(url)
            arxiv_id = extract_arxiv_id(url)
            if arxiv_id:
                arxiv_id_to_collections[arxiv_id].append(collection_name)
        
        if verbose:
            rel_path = os.path.relpath(file_path, root_dir)
            print(f"  {rel_path}: {len(urls)} URLs")
    
    # Extract arXiv IDs
    arxiv_ids = []
    failed_extractions = []
    
    for url in all_urls:
        arxiv_id = extract_arxiv_id(url)
        if arxiv_id:
            arxiv_ids.append(arxiv_id)
        else:
            failed_extractions.append(url)
    
    # Count duplicates
    id_counts = Counter(arxiv_ids)
    unique_ids = set(arxiv_ids)
    duplicates = {arxiv_id: count for arxiv_id, count in id_counts.items() if count > 1}
    
    # Statistics
    total_urls = len(all_urls)
    total_unique_ids = len(unique_ids)
    total_duplicates = len(duplicates)
    total_duplicate_instances = sum(count - 1 for count in duplicates.values())
    
    print(f"\n" + "=" * 50)
    print("SUMMARY STATISTICS")
    print("=" * 50)
    print(f"Total arxiv_links.txt files found: {len(arxiv_files)}")
    print(f"Total URLs across all files: {total_urls:,}")
    print(f"Unique arXiv IDs: {total_unique_ids:,}")
    print(f"Duplicate arXiv IDs: {total_duplicates:,}")
    print(f"Total duplicate instances: {total_duplicate_instances:,}")
    if total_urls > 0:
        print(f"Deduplication savings: {total_duplicate_instances:,} URLs ({total_duplicate_instances/total_urls*100:.1f}%)")
    else:
        print(f"Deduplication savings: 0 URLs (0.0%)")
    
    if failed_extractions:
        print(f"Failed to extract arXiv ID from {len(failed_extractions)} URLs")
    
    # Top collections by number of papers
    print(f"\nTOP 10 COLLECTIONS BY SIZE:")
    print("-" * 40)
    sorted_collections = sorted(collection_stats.items(), key=lambda x: x[1], reverse=True)
    for i, (collection, count) in enumerate(sorted_collections[:10], 1):
        print(f"{i:2d}. {collection:<25} {count:4d} papers")
    
    # Duplicate analysis
    if duplicates:
        print(f"\nDUPLICATE arXiv IDs:")
        print("-" * 60)
        print(f"{'arXiv ID':<15} {'Count':<8} {'Collections'}")
        print("-" * 60)
        
        sorted_duplicates = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)
        
        for arxiv_id, count in sorted_duplicates[:50]:  # Show top 50 duplicates
            collections = list(set(arxiv_id_to_collections[arxiv_id]))
            collections_str = ', '.join(sorted(collections))
            if len(collections_str) > 40:
                collections_str = collections_str[:37] + "..."
            print(f"{arxiv_id:<15} {count:<8} {collections_str}")
        
        if len(sorted_duplicates) > 50:
            print(f"... and {len(sorted_duplicates) - 50} more duplicate IDs")
    
    # Most duplicated papers
    if duplicates:
        print(f"\nMOST DUPLICATED PAPERS:")
        print("-" * 60)
        top_duplicates = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for i, (arxiv_id, count) in enumerate(top_duplicates, 1):
            collections = sorted(set(arxiv_id_to_collections[arxiv_id]))
            print(f"{i:2d}. {arxiv_id} ({count} copies)")
            print(f"    Collections: {', '.join(collections)}")
    
    return {
        'total_files': len(arxiv_files),
        'total_urls': total_urls,
        'unique_ids': total_unique_ids,
        'duplicate_ids': total_duplicates,
        'duplicate_instances': total_duplicate_instances,
        'duplicates': duplicates,
        'collection_stats': collection_stats,
        'arxiv_id_to_collections': dict(arxiv_id_to_collections),
        'failed_extractions': failed_extractions
    }


def save_detailed_report(results, output_file):
    """Save detailed analysis results to a file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("ArXiv Duplicate Analysis - Detailed Report\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total arxiv_links.txt files: {results['total_files']}\n")
        f.write(f"Total URLs: {results['total_urls']:,}\n")
        f.write(f"Unique arXiv IDs: {results['unique_ids']:,}\n")
        f.write(f"Duplicate arXiv IDs: {results['duplicate_ids']:,}\n")
        f.write(f"Total duplicate instances: {results['duplicate_instances']:,}\n")
        f.write(f"Deduplication savings: {results['duplicate_instances']/results['total_urls']*100:.1f}%\n\n")
        
        f.write("ALL COLLECTIONS\n")
        f.write("-" * 30 + "\n")
        sorted_collections = sorted(results['collection_stats'].items(), key=lambda x: x[1], reverse=True)
        for collection, count in sorted_collections:
            f.write(f"{collection:<30} {count:4d} papers\n")
        
        f.write("\nALL DUPLICATE IDs\n")
        f.write("-" * 30 + "\n")
        f.write(f"{'arXiv ID':<15} {'Count':<8} {'Collections'}\n")
        f.write("-" * 60 + "\n")
        
        sorted_duplicates = sorted(results['duplicates'].items(), key=lambda x: x[1], reverse=True)
        for arxiv_id, count in sorted_duplicates:
            collections = sorted(set(results['arxiv_id_to_collections'][arxiv_id]))
            collections_str = ', '.join(collections)
            f.write(f"{arxiv_id:<15} {count:<8} {collections_str}\n")
        
        if results['failed_extractions']:
            f.write(f"\nFAILED EXTRACTIONS ({len(results['failed_extractions'])} URLs)\n")
            f.write("-" * 50 + "\n")
            for url in results['failed_extractions']:
                f.write(f"{url}\n")
    
    print(f"\nDetailed report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Analyze arXiv URL duplicates across collections')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Show verbose output including all files processed')
    parser.add_argument('--output-file', '-o', 
                       help='Save detailed report to file')
    parser.add_argument('--directory', '-d', default='.',
                       help='Root directory to search (default: current directory)')
    
    args = parser.parse_args()
    
    root_dir = os.path.abspath(args.directory)
    
    if not os.path.exists(root_dir):
        print(f"Error: Directory {root_dir} does not exist")
        return 1
    
    results = analyze_arxiv_files(root_dir, verbose=args.verbose)
    
    if args.output_file:
        save_detailed_report(results, args.output_file)
    
    return 0


if __name__ == "__main__":
    exit(main())