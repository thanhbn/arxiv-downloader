#!/usr/bin/env python3
"""
Translation Completeness Checker

This script compares token counts between English and Vietnamese versions of papers
to identify potentially incomplete translations. It extracts arXiv IDs from filenames
and generates a detailed report with completion ratios.

Usage:
    python check_translation_completeness.py [--threshold RATIO] [--output FILE] [--add-to-queue]
    
Options:
    --threshold RATIO       Minimum completion ratio to flag as incomplete (default: 0.7)
    --output FILE          Output markdown report file (default: translation_completeness_report.md)
    --root-dir DIR         Root directory to search for papers (default: current directory)
    --add-to-queue         Add incomplete translations to translation queue
    --queue-file FILE      Translation queue file (default: translation_queue.txt)
    --remove-big-papers FILE  Remove papers listed in specified file from the queue
"""

import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in text using word-based approximation."""
    # Approximation: 1.3 tokens per word for most languages
    # This is a reasonable estimate for both English and Vietnamese
    words = len(text.split())
    return int(words * 1.3)

def extract_arxiv_id(filename: str) -> Optional[str]:
    """Extract arXiv ID from filename."""
    # Match patterns like: 2310.10996, 1234.56789, etc.
    match = re.search(r'(\d{4}\.\d{4,5})', filename)
    return match.group(1) if match else None

def read_file_safely(file_path: str) -> str:
    """Read file content safely with multiple encoding attempts."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
    
    print(f"Could not read {file_path} with any encoding")
    return ""

def find_translation_pairs(root_dir: str) -> Dict[str, Dict[str, str]]:
    """Find pairs of English and Vietnamese files by arXiv ID."""
    papers = {}
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.txt'):
                arxiv_id = extract_arxiv_id(file)
                if not arxiv_id:
                    continue
                
                file_path = os.path.join(root, file)
                collection = os.path.basename(root)
                
                # Create unique key for each file location to handle duplicates
                unique_key = f"{arxiv_id}_{collection}"
                
                if unique_key not in papers:
                    papers[unique_key] = {
                        'arxiv_id': arxiv_id,
                        'english': None, 
                        'vietnamese': None, 
                        'collection': collection
                    }
                
                if file.endswith('_vi.txt'):
                    if papers[unique_key]['vietnamese'] is None:
                        papers[unique_key]['vietnamese'] = file_path
                    else:
                        # Handle multiple Vietnamese files - keep the newer/larger one
                        print(f"⚠️  Multiple Vietnamese files found for {arxiv_id} in {collection}")
                        print(f"   Existing: {papers[unique_key]['vietnamese']}")
                        print(f"   New: {file_path}")
                        # Keep the larger file (likely more complete)
                        try:
                            if os.path.getsize(file_path) > os.path.getsize(papers[unique_key]['vietnamese']):
                                papers[unique_key]['vietnamese'] = file_path
                                print(f"   → Using larger file: {file}")
                        except OSError:
                            pass  # Keep existing if size check fails
                else:
                    if papers[unique_key]['english'] is None:
                        papers[unique_key]['english'] = file_path
                    else:
                        # Handle multiple English files - keep the newer/larger one  
                        print(f"⚠️  Multiple English files found for {arxiv_id} in {collection}")
                        print(f"   Existing: {papers[unique_key]['english']}")
                        print(f"   New: {file_path}")
                        try:
                            if os.path.getsize(file_path) > os.path.getsize(papers[unique_key]['english']):
                                papers[unique_key]['english'] = file_path
                                print(f"   → Using larger file: {file}")
                        except OSError:
                            pass  # Keep existing if size check fails
    
    return papers

def analyze_translation_completeness(papers: Dict[str, Dict[str, str]], threshold: float = 0.7) -> List[Dict]:
    """Analyze translation completeness and return results."""
    results = []
    
    for unique_key, files in papers.items():
        if not files['english'] or not files['vietnamese']:
            continue
        
        # Read file contents
        english_content = read_file_safely(files['english'])
        vietnamese_content = read_file_safely(files['vietnamese'])
        
        if not english_content or not vietnamese_content:
            continue
        
        # Count tokens
        english_tokens = count_tokens(english_content)
        vietnamese_tokens = count_tokens(vietnamese_content)
        
        # Calculate completion ratio
        completion_ratio = vietnamese_tokens / english_tokens if english_tokens > 0 else 0
        
        # Determine status
        if completion_ratio < threshold:
            status = "Incomplete"
        elif completion_ratio > 1.2:  # Significantly longer than original
            status = "Over-translated"
        else:
            status = "Complete"
        
        results.append({
            'arxiv_id': files['arxiv_id'],
            'collection': files['collection'],
            'english_tokens': english_tokens,
            'vietnamese_tokens': vietnamese_tokens,
            'completion_ratio': completion_ratio,
            'status': status,
            'english_file': os.path.basename(files['english']),
            'vietnamese_file': os.path.basename(files['vietnamese']),
            'english_path': files['english'],  # Store full path for queue functionality
            'vietnamese_path': files['vietnamese']
        })
    
    return sorted(results, key=lambda x: x['completion_ratio'])

def generate_markdown_report(results: List[Dict], output_file: str, threshold: float):
    """Generate a detailed markdown report."""
    
    # Filter incomplete translations
    incomplete = [r for r in results if r['status'] == 'Incomplete']
    complete = [r for r in results if r['status'] == 'Complete']
    over_translated = [r for r in results if r['status'] == 'Over-translated']
    
    # Statistics
    total_pairs = len(results)
    incomplete_count = len(incomplete)
    complete_count = len(complete)
    over_translated_count = len(over_translated)
    
    avg_completion = sum(r['completion_ratio'] for r in results) / total_pairs if total_pairs > 0 else 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Translation Completeness Report\n\n")
        f.write(f"**Generated on:** {Path().absolute()}\n")
        f.write(f"**Threshold:** {threshold:.1%}\n\n")
        
        # Summary statistics
        f.write("## Summary Statistics\n\n")
        f.write(f"- **Total Translation Pairs:** {total_pairs}\n")
        f.write(f"- **Complete Translations:** {complete_count} ({complete_count/total_pairs:.1%})\n")
        f.write(f"- **Incomplete Translations:** {incomplete_count} ({incomplete_count/total_pairs:.1%})\n")
        f.write(f"- **Over-translated:** {over_translated_count} ({over_translated_count/total_pairs:.1%})\n")
        f.write(f"- **Average Completion Ratio:** {avg_completion:.1%}\n\n")
        
        # Incomplete translations table
        if incomplete:
            f.write("## Incomplete Translations\n\n")
            f.write("Papers with completion ratio below threshold:\n\n")
            f.write("| ArXiv ID | Collection | EN Tokens | VI Tokens | Ratio | Status |\n")
            f.write("|----------|------------|-----------|-----------|-------|--------|\n")
            
            for result in incomplete:
                f.write(f"| {result['arxiv_id']} | {result['collection']} | "
                       f"{result['english_tokens']:,} | {result['vietnamese_tokens']:,} | "
                       f"{result['completion_ratio']:.1%} | {result['status']} |\n")
            f.write("\n")
        
        # Over-translated papers
        if over_translated:
            f.write("## Over-translated Papers\n\n")
            f.write("Papers with significantly more Vietnamese content than English:\n\n")
            f.write("| ArXiv ID | Collection | EN Tokens | VI Tokens | Ratio | Status |\n")
            f.write("|----------|------------|-----------|-----------|-------|--------|\n")
            
            for result in over_translated:
                f.write(f"| {result['arxiv_id']} | {result['collection']} | "
                       f"{result['english_tokens']:,} | {result['vietnamese_tokens']:,} | "
                       f"{result['completion_ratio']:.1%} | {result['status']} |\n")
            f.write("\n")
        
        # Collection breakdown
        f.write("## Collection Breakdown\n\n")
        collections = {}
        for result in results:
            coll = result['collection']
            if coll not in collections:
                collections[coll] = {'total': 0, 'incomplete': 0, 'complete': 0, 'over_translated': 0}
            collections[coll]['total'] += 1
            collections[coll][result['status'].lower().replace('-', '_')] += 1
        
        f.write("| Collection | Total | Complete | Incomplete | Over-translated | Completion Rate |\n")
        f.write("|------------|-------|----------|------------|-----------------|----------------|\n")
        
        for coll, stats in sorted(collections.items()):
            completion_rate = stats['complete'] / stats['total'] if stats['total'] > 0 else 0
            f.write(f"| {coll} | {stats['total']} | {stats['complete']} | "
                   f"{stats['incomplete']} | {stats['over_translated']} | {completion_rate:.1%} |\n")
        
        f.write("\n")
        
        # All results table
        f.write("## All Translation Pairs\n\n")
        f.write("Complete listing of all translation pairs:\n\n")
        f.write("| ArXiv ID | Collection | EN Tokens | VI Tokens | Ratio | Status |\n")
        f.write("|----------|------------|-----------|-----------|-------|--------|\n")
        
        for result in results:
            f.write(f"| {result['arxiv_id']} | {result['collection']} | "
                   f"{result['english_tokens']:,} | {result['vietnamese_tokens']:,} | "
                   f"{result['completion_ratio']:.1%} | {result['status']} |\n")
        
        f.write("\n")
        
        # Detailed file information
        f.write("## Detailed File Information\n\n")
        f.write("### Incomplete Translations (Detailed)\n\n")
        for result in incomplete:
            f.write(f"#### {result['arxiv_id']} ({result['collection']})\n")
            f.write(f"- **English File:** `{result['english_file']}`\n")
            f.write(f"- **Vietnamese File:** `{result['vietnamese_file']}`\n")
            f.write(f"- **Token Counts:** {result['english_tokens']:,} EN → {result['vietnamese_tokens']:,} VI\n")
            f.write(f"- **Completion Ratio:** {result['completion_ratio']:.1%}\n\n")

def add_to_translation_queue(incomplete_papers: List[Dict], queue_file: str = "translation_queue.txt"):
    """Add incomplete translations to the translation queue."""
    existing_files = set()
    
    # Read existing queue if it exists
    if os.path.exists(queue_file):
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                existing_files = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        except Exception as e:
            print(f"Warning: Could not read existing queue file: {e}")
    
    # Collect new files to add (use stored English paths)
    new_files = []
    duplicate_count = 0
    
    for paper in incomplete_papers:
        english_file = paper.get('english_path')
        if english_file:
            if english_file not in existing_files:
                new_files.append(english_file)
            else:
                duplicate_count += 1
        else:
            print(f"⚠️  No English file path found for ArXiv ID: {paper['arxiv_id']}")
    
    if new_files:
        # Append new files to queue
        with open(queue_file, 'a', encoding='utf-8') as f:
            if not existing_files:  # New file
                f.write("# Translation Queue - Papers needing translation/re-translation\n")
                f.write("# Generated by check_translation_completeness.py\n")
                f.write(f"# Incomplete translations (threshold < {incomplete_papers[0].get('threshold', 'N/A')})\n\n")
            
            for file_path in new_files:
                f.write(f"{file_path}\n")
        
        print(f"📝 Added {len(new_files)} incomplete translations to {queue_file}")
        if duplicate_count > 0:
            print(f"📋 Skipped {duplicate_count} duplicates already in queue")
        return len(new_files)
    else:
        if duplicate_count > 0:
            print(f"📝 No new incomplete translations to add (all {duplicate_count} already in queue)")
        else:
            print("📝 No incomplete translations found to add to queue")
        return 0

def extract_clean_path(line: str) -> str:
    """Extract clean file path from a line that might have processing timestamps."""
    line = line.strip()
    if not line or line.startswith('#'):
        return ""
    
    # Remove processing timestamps like "[Processing] 20250708-1025 "
    pattern = r'^\[Processing\]\s+\d{8}-\d{4}(?:\s+\d{8}-\d{4})?\s+'
    clean_line = re.sub(pattern, '', line)
    
    return clean_line.strip()

def load_big_files(big_file_path: str) -> Set[str]:
    """Load the list of big files to remove."""
    big_files = set()
    
    try:
        with open(big_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                clean_path = extract_clean_path(line)
                if clean_path:
                    big_files.add(clean_path)
    except FileNotFoundError:
        print(f"❌ Big file list not found: {big_file_path}")
        return set()
    except Exception as e:
        print(f"❌ Error reading big file list: {e}")
        return set()
    
    print(f"📋 Loaded {len(big_files)} big files to remove from queue")
    return big_files

def remove_big_papers_from_queue(queue_file: str, big_files: Set[str]) -> int:
    """Remove big papers from translation queue."""
    if not os.path.exists(queue_file):
        print(f"⚠️  Queue file not found: {queue_file}")
        return 0
    
    removed_count = 0
    kept_lines = []
    
    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            for line in f:
                original_line = line.rstrip('\n\r')
                clean_path = extract_clean_path(line)
                
                if not clean_path or clean_path.startswith('#'):
                    # Keep comments and empty lines
                    kept_lines.append(original_line)
                elif clean_path in big_files:
                    # Remove this file
                    removed_count += 1
                    print(f"🗑️  Removing big paper: {clean_path}")
                else:
                    # Keep this file
                    kept_lines.append(original_line)
        
        # Write cleaned queue back
        with open(queue_file, 'w', encoding='utf-8') as f:
            for line in kept_lines:
                f.write(line + '\n')
        
        print(f"✅ Removed {removed_count} big papers from queue")
        print(f"📊 Queue now contains {len([l for l in kept_lines if l and not l.startswith('#')])} files")
        
        return removed_count
        
    except Exception as e:
        print(f"❌ Error processing queue file: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Check translation completeness by comparing token counts")
    parser.add_argument("--threshold", type=float, default=0.7, 
                       help="Minimum completion ratio to flag as incomplete (default: 0.7)")
    parser.add_argument("--output", type=str, default="translation_completeness_report.md",
                       help="Output markdown report file")
    parser.add_argument("--root-dir", type=str, default=".",
                       help="Root directory to search for papers")
    parser.add_argument("--add-to-queue", action="store_true",
                       help="Add incomplete translations to translation queue")
    parser.add_argument("--queue-file", type=str, default="translation_queue.txt",
                       help="Translation queue file (default: translation_queue.txt)")
    parser.add_argument("--remove-big-papers", type=str, metavar="BIG_FILE_LIST",
                       help="Remove papers listed in specified file from the queue")
    
    args = parser.parse_args()
    
    print("🔍 Finding translation pairs...")
    papers = find_translation_pairs(args.root_dir)
    
    print(f"📊 Found {len(papers)} papers with potential translations")
    
    print("📈 Analyzing translation completeness...")
    results = analyze_translation_completeness(papers, args.threshold)
    
    # Filter incomplete translations
    incomplete_results = [r for r in results if r['status'] == 'Incomplete']
    
    print(f"📝 Generating report: {args.output}")
    generate_markdown_report(results, args.output, args.threshold)
    
    # Add to queue if requested
    if args.add_to_queue and incomplete_results:
        print("\n📋 Adding incomplete translations to queue...")
        added_count = add_to_translation_queue(incomplete_results, args.queue_file)
        if added_count > 0:
            print(f"✅ Added {added_count} papers to translation queue: {args.queue_file}")
    
    # Print summary to console
    incomplete_count = len(incomplete_results)
    total_count = len(results)
    
    print(f"\n✅ Analysis complete!")
    print(f"📋 Total translation pairs analyzed: {total_count}")
    print(f"⚠️  Incomplete translations found: {incomplete_count}")
    print(f"📄 Detailed report saved to: {args.output}")
    
    if args.add_to_queue:
        print(f"📝 Translation queue: {args.queue_file}")
    
    # Remove big papers if requested
    if args.remove_big_papers:
        print(f"\n🗑️  Removing big papers from queue...")
        big_files = load_big_files(args.remove_big_papers)
        if big_files:
            removed_count = remove_big_papers_from_queue(args.queue_file, big_files)
            if removed_count > 0:
                print(f"✅ Successfully cleaned {removed_count} big papers from queue")
        else:
            print("⚠️  No big papers loaded for removal")

if __name__ == "__main__":
    main()