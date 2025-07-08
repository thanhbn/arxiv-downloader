#!/usr/bin/env python3
"""
Quick inventory of all expected papers across collections without fetching from ArXiv.
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

def analyze_collection(collection_path):
    """Analyze a single collection's expected papers."""
    collection_name = os.path.basename(collection_path)
    arxiv_links_path = os.path.join(collection_path, 'arxiv_links.txt')
    
    papers = []
    
    # Read expected papers from arxiv_links.txt
    if os.path.exists(arxiv_links_path):
        with open(arxiv_links_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    arxiv_id = extract_arxiv_id(line)
                    if arxiv_id:
                        papers.append({
                            'id': arxiv_id,
                            'url': line
                        })
    
    return {
        'name': collection_name,
        'total': len(papers),
        'papers': papers[:5]  # Just first 5 for sample
    }

def main():
    """Create quick inventory of all collections."""
    # Change to parent directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(parent_dir)
    
    # Find all collections
    collections = []
    for arxiv_links in sorted(glob.glob('*/arxiv_links.txt')):
        collection_path = os.path.dirname(arxiv_links)
        if collection_path and not collection_path.startswith('.'):
            collections.append(collection_path)
    
    # Analyze each collection
    results = []
    total_papers = 0
    
    print("COMPREHENSIVE INVENTORY OF ARXIV-DOWNLOADER COLLECTIONS")
    print("=" * 80)
    
    for collection_path in collections:
        result = analyze_collection(collection_path)
        results.append(result)
        total_papers += result['total']
    
    # Sort by paper count
    results.sort(key=lambda x: x['total'], reverse=True)
    
    # Print summary
    print(f"\nTotal Collections: {len(collections)}")
    print(f"Total Expected Papers: {total_papers}")
    print("\n" + "=" * 80)
    
    # Print all collections with counts
    print("\nALL COLLECTIONS (sorted by paper count):")
    print("-" * 80)
    
    for result in results:
        print(f"\n{result['name'].upper()}:")
        print(f"  Total papers: {result['total']}")
        if result['papers']:
            print("  Sample paper IDs:")
            for paper in result['papers']:
                print(f"    - {paper['id']}")
    
    # Special focus on key collections
    print("\n" + "=" * 80)
    print("KEY COLLECTIONS FOR CODE REVIEW/PROGRAMMING/AGENTS/EFFICIENCY")
    print("=" * 80)
    
    key_collections = {
        'coding': 'Code generation, synthesis, and analysis',
        'agent': 'AI agents and autonomous systems',
        'benchmark': 'Performance benchmarks and evaluation',
        'rag': 'Retrieval-Augmented Generation',
        'peft': 'Parameter-Efficient Fine-Tuning',
        'multimodal': 'Multimodal AI research',
        'cot': 'Chain of Thought reasoning',
        'icl': 'In-Context Learning',
        'efficiency': 'Model efficiency and optimization',
        'evaluation': 'Model evaluation and metrics',
        'prompt': 'Prompt engineering',
        'instruct': 'Instruction following',
        'llm-architecture': 'LLM architectural improvements',
        'optimization': 'Optimization techniques',
        'integration': 'System integration',
        'tool': 'Tool use and integration',
        'debug': 'Debugging and error handling',
        'test': 'Testing and validation'
    }
    
    for coll_name, description in key_collections.items():
        matching = [r for r in results if r['name'] == coll_name]
        if matching:
            result = matching[0]
            print(f"\n{coll_name.upper()}: {description}")
            print(f"  Papers: {result['total']}")
            if result['papers']:
                print("  First 5 papers:")
                for i, paper in enumerate(result['papers'], 1):
                    print(f"    {i}. {paper['id']} - {paper['url']}")
    
    # Save to JSON
    output = {
        'generated_at': datetime.now().isoformat(),
        'total_collections': len(collections),
        'total_papers': total_papers,
        'collections': results
    }
    
    with open('paper_inventory.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nInventory saved to: paper_inventory.json")

if __name__ == "__main__":
    main()