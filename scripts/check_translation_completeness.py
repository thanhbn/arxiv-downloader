#!/usr/bin/env python3
"""
Translation Completeness Checker

This script compares token counts between English and Vietnamese versions of papers
to identify potentially incomplete translations. It extracts arXiv IDs from filenames
and generates a detailed report with completion ratios.

Usage:
    python check_translation_completeness.py [--threshold RATIO] [--output FILE]
    
Options:
    --threshold RATIO   Minimum completion ratio to flag as incomplete (default: 0.7)
    --output FILE      Output markdown report file (default: translation_completeness_report.md)
"""

import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
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
                
                if arxiv_id not in papers:
                    papers[arxiv_id] = {'english': None, 'vietnamese': None, 'collection': os.path.basename(root)}
                
                if file.endswith('_vi.txt'):
                    papers[arxiv_id]['vietnamese'] = file_path
                else:
                    papers[arxiv_id]['english'] = file_path
    
    return papers

def analyze_translation_completeness(papers: Dict[str, Dict[str, str]], threshold: float = 0.7) -> List[Dict]:
    """Analyze translation completeness and return results."""
    results = []
    
    for arxiv_id, files in papers.items():
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
            'arxiv_id': arxiv_id,
            'collection': files['collection'],
            'english_tokens': english_tokens,
            'vietnamese_tokens': vietnamese_tokens,
            'completion_ratio': completion_ratio,
            'status': status,
            'english_file': os.path.basename(files['english']),
            'vietnamese_file': os.path.basename(files['vietnamese'])
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

def main():
    parser = argparse.ArgumentParser(description="Check translation completeness by comparing token counts")
    parser.add_argument("--threshold", type=float, default=0.7, 
                       help="Minimum completion ratio to flag as incomplete (default: 0.7)")
    parser.add_argument("--output", type=str, default="translation_completeness_report.md",
                       help="Output markdown report file")
    parser.add_argument("--root-dir", type=str, default=".",
                       help="Root directory to search for papers")
    
    args = parser.parse_args()
    
    print("🔍 Finding translation pairs...")
    papers = find_translation_pairs(args.root_dir)
    
    print(f"📊 Found {len(papers)} papers with potential translations")
    
    print("📈 Analyzing translation completeness...")
    results = analyze_translation_completeness(papers, args.threshold)
    
    print(f"📝 Generating report: {args.output}")
    generate_markdown_report(results, args.output, args.threshold)
    
    # Print summary to console
    incomplete_count = len([r for r in results if r['status'] == 'Incomplete'])
    total_count = len(results)
    
    print(f"\n✅ Analysis complete!")
    print(f"📋 Total translation pairs analyzed: {total_count}")
    print(f"⚠️  Incomplete translations found: {incomplete_count}")
    print(f"📄 Detailed report saved to: {args.output}")

if __name__ == "__main__":
    main()