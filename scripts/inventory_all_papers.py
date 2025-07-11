#!/usr/bin/env python3
"""
Comprehensive inventory of all papers across all collections in arxiv-downloader.
Extracts paper titles, IDs, and creates a full catalog with special attention to
code review, programming, agents, efficiency, and integration related papers.
"""

import os
import re
import glob
from collections import defaultdict
import json
from datetime import datetime

def extract_arxiv_id(url):
    """Extract arxiv ID from URL."""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def get_paper_title(pdf_path):
    """Try to get paper title from corresponding TXT file if it exists."""
    txt_path = pdf_path.replace('.pdf', '.txt')
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first few lines to find title
                lines = f.readlines()[:10]
                for line in lines:
                    line = line.strip()
                    if len(line) > 10 and not line.startswith('arXiv:'):
                        return line
        except:
            pass
    return None

def analyze_collection(collection_path):
    """Analyze a single collection and return its inventory."""
    collection_name = os.path.basename(collection_path)
    arxiv_links_path = os.path.join(collection_path, 'arxiv_links.txt')
    
    result = {
        'name': collection_name,
        'path': collection_path,
        'expected_papers': [],
        'found_papers': [],
        'total_expected': 0,
        'total_found': 0,
        'completion_rate': 0.0,
        'relevant_papers': []  # Papers relevant to coding, agents, efficiency, integration
    }
    
    # Read expected papers from arxiv_links.txt
    if os.path.exists(arxiv_links_path):
        with open(arxiv_links_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    arxiv_id = extract_arxiv_id(line)
                    if arxiv_id:
                        result['expected_papers'].append({
                            'id': arxiv_id,
                            'url': line
                        })
    
    result['total_expected'] = len(result['expected_papers'])
    
    # Find actual PDF files in the collection
    pdf_files = glob.glob(os.path.join(collection_path, '*.pdf'))
    
    # Keywords for identifying relevant papers
    relevant_keywords = [
        'code', 'coding', 'program', 'software', 'agent', 'efficiency', 
        'integration', 'review', 'debug', 'test', 'compile', 'syntax',
        'api', 'tool', 'benchmark', 'performance', 'optimization',
        'generation', 'synthesis', 'repair', 'analysis', 'quality',
        'documentation', 'refactor', 'bug', 'error', 'fix'
    ]
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        arxiv_id = extract_arxiv_id(filename)
        title = get_paper_title(pdf_path)
        
        paper_info = {
            'id': arxiv_id,
            'filename': filename,
            'title': title or filename,
            'path': pdf_path
        }
        
        result['found_papers'].append(paper_info)
        
        # Check if paper is relevant to our focus areas
        title_lower = (title or filename).lower()
        if any(keyword in title_lower for keyword in relevant_keywords):
            result['relevant_papers'].append(paper_info)
    
    result['total_found'] = len(result['found_papers'])
    
    # Calculate completion rate
    if result['total_expected'] > 0:
        found_ids = {p['id'] for p in result['found_papers'] if p['id']}
        expected_ids = {p['id'] for p in result['expected_papers']}
        result['completion_rate'] = len(found_ids & expected_ids) / result['total_expected'] * 100
    
    return result

def main():
    """Create comprehensive inventory of all collections."""
    print("Creating comprehensive inventory of arxiv-downloader collections...")
    print("=" * 80)
    
    # Change to parent directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(parent_dir)
    
    # Find all collections
    collections = []
    for arxiv_links in glob.glob('*/arxiv_links.txt'):
        collection_path = os.path.dirname(arxiv_links)
        if collection_path and not collection_path.startswith('.'):
            collections.append(collection_path)
    
    collections.sort()
    
    # Analyze each collection
    inventory = {
        'generated_at': datetime.now().isoformat(),
        'total_collections': len(collections),
        'collections': {},
        'summary': {
            'total_papers_expected': 0,
            'total_papers_found': 0,
            'total_relevant_papers': 0,
            'collections_by_size': [],
            'collections_by_relevance': []
        }
    }
    
    # Collections particularly relevant to our focus areas
    focus_collections = [
        'coding', 'agent', 'benchmark', 'efficiency', 'integration',
        'code', 'programming', 'software', 'tool', 'debug', 'test'
    ]
    
    for collection_path in collections:
        print(f"\nAnalyzing collection: {collection_path}")
        result = analyze_collection(collection_path)
        
        inventory['collections'][result['name']] = result
        inventory['summary']['total_papers_expected'] += result['total_expected']
        inventory['summary']['total_papers_found'] += result['total_found']
        inventory['summary']['total_relevant_papers'] += len(result['relevant_papers'])
        
        # Print summary for this collection
        print(f"  - Expected papers: {result['total_expected']}")
        print(f"  - Found papers: {result['total_found']}")
        print(f"  - Completion rate: {result['completion_rate']:.1f}%")
        print(f"  - Relevant papers: {len(result['relevant_papers'])}")
        
        # Print some relevant paper titles if found
        if result['relevant_papers']:
            print("  - Sample relevant papers:")
            for paper in result['relevant_papers'][:3]:
                title = paper['title']
                if len(title) > 80:
                    title = title[:77] + "..."
                print(f"    • {title}")
    
    # Sort collections by size and relevance
    inventory['summary']['collections_by_size'] = sorted(
        [(name, data['total_found']) for name, data in inventory['collections'].items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]
    
    inventory['summary']['collections_by_relevance'] = sorted(
        [(name, len(data['relevant_papers'])) for name, data in inventory['collections'].items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]
    
    # Save inventory to JSON
    output_path = os.path.join(os.getcwd(), 'coding', 'paper_inventory.json')
    with open(output_path, 'w') as f:
        json.dump(inventory, f, indent=2)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("INVENTORY SUMMARY")
    print("=" * 80)
    print(f"Total collections analyzed: {inventory['summary']['total_collections']}")
    print(f"Total papers expected: {inventory['summary']['total_papers_expected']}")
    print(f"Total papers found: {inventory['summary']['total_papers_found']}")
    print(f"Total relevant papers: {inventory['summary']['total_relevant_papers']}")
    
    print("\nTop 10 Collections by Size:")
    for name, count in inventory['summary']['collections_by_size'][:10]:
        print(f"  - {name}: {count} papers")
    
    print("\nTop 10 Collections by Relevance (code/agent/efficiency/integration):")
    for name, count in inventory['summary']['collections_by_relevance'][:10]:
        if count > 0:
            print(f"  - {name}: {count} relevant papers")
    
    print(f"\nFull inventory saved to: {output_path}")
    
    # Create a focused report for key collections
    print("\n" + "=" * 80)
    print("FOCUSED ANALYSIS: Key Collections for Code Review & Programming")
    print("=" * 80)
    
    for collection_name in ['coding', 'agent', 'benchmark', 'rag', 'peft', 'multimodal', 'cot', 'icl']:
        if collection_name in inventory['collections']:
            data = inventory['collections'][collection_name]
            print(f"\n{collection_name.upper()} Collection:")
            print(f"  - Total papers: {data['total_found']}")
            print(f"  - Relevant papers: {len(data['relevant_papers'])}")
            if data['found_papers']:
                print("  - Sample papers:")
                for paper in data['found_papers'][:5]:
                    title = paper['title'] or paper['filename']
                    if len(title) > 70:
                        title = title[:67] + "..."
                    print(f"    • [{paper['id']}] {title}")

if __name__ == "__main__":
    main()