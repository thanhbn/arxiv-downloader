#!/usr/bin/env python3
"""
Comprehensive inventory of expected papers across all collections in arxiv-downloader.
Analyzes arxiv_links.txt files to extract paper IDs and URLs, with special attention
to papers related to code review, programming, agents, efficiency, and integration.
"""

import os
import re
import glob
from collections import defaultdict
import json
from datetime import datetime
import requests
from time import sleep

def extract_arxiv_id(url):
    """Extract arxiv ID from URL."""
    match = re.search(r'(\d{4}\.\d{4,5})', url)
    return match.group(1) if match else None

def get_paper_info_from_arxiv(arxiv_id, max_retries=3):
    """Fetch paper title and abstract from arxiv API."""
    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # Extract title
                title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                    # Remove newlines and extra spaces
                    title = ' '.join(title.split())
                    
                    # Extract abstract
                    abstract_match = re.search(r'<summary>(.*?)</summary>', content, re.DOTALL)
                    abstract = ""
                    if abstract_match:
                        abstract = abstract_match.group(1).strip()
                        abstract = ' '.join(abstract.split())[:200] + "..."
                    
                    return title, abstract
            sleep(0.5)  # Rate limiting
        except:
            if attempt < max_retries - 1:
                sleep(1)
    
    return None, None

def analyze_collection(collection_path, fetch_titles=False):
    """Analyze a single collection's expected papers."""
    collection_name = os.path.basename(collection_path)
    arxiv_links_path = os.path.join(collection_path, 'arxiv_links.txt')
    
    result = {
        'name': collection_name,
        'path': collection_path,
        'papers': [],
        'total': 0,
        'relevant_papers': []  # Papers relevant to coding, agents, efficiency, integration
    }
    
    # Keywords for identifying relevant papers
    relevant_keywords = [
        'code', 'coding', 'program', 'software', 'agent', 'efficiency', 
        'integration', 'review', 'debug', 'test', 'compile', 'syntax',
        'api', 'tool', 'benchmark', 'performance', 'optimization',
        'generation', 'synthesis', 'repair', 'analysis', 'quality',
        'documentation', 'refactor', 'bug', 'error', 'fix', 'LLM',
        'language model', 'neural', 'transformer', 'GPT', 'BERT'
    ]
    
    # Read expected papers from arxiv_links.txt
    if os.path.exists(arxiv_links_path):
        with open(arxiv_links_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    arxiv_id = extract_arxiv_id(line)
                    if arxiv_id:
                        paper_info = {
                            'id': arxiv_id,
                            'url': line,
                            'title': None,
                            'abstract': None
                        }
                        
                        # Only fetch titles for smaller collections or specific ones
                        if fetch_titles and (collection_name in ['coding', 'agent', 'benchmark'] or result['total'] < 20):
                            title, abstract = get_paper_info_from_arxiv(arxiv_id)
                            paper_info['title'] = title
                            paper_info['abstract'] = abstract
                            
                            # Check relevance based on title/abstract
                            if title:
                                text_to_check = (title + " " + (abstract or "")).lower()
                                if any(keyword in text_to_check for keyword in relevant_keywords):
                                    result['relevant_papers'].append(paper_info)
                        
                        result['papers'].append(paper_info)
                        result['total'] += 1
    
    return result

def main():
    """Create comprehensive inventory of expected papers in all collections."""
    print("Creating comprehensive inventory of expected papers in arxiv-downloader...")
    print("=" * 80)
    
    # Change to parent directory to find all collections
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(parent_dir)  # Go up one more level
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
            'total_papers': 0,
            'collections_by_size': [],
            'key_collections': {}
        }
    }
    
    # Key collections to analyze in detail
    key_collections = ['coding', 'agent', 'benchmark', 'rag', 'peft', 'multimodal', 'cot', 'icl']
    
    for i, collection_path in enumerate(collections):
        print(f"\nAnalyzing collection {i+1}/{len(collections)}: {collection_path}")
        
        # Fetch titles only for key collections
        fetch_titles = collection_path in key_collections
        result = analyze_collection(collection_path, fetch_titles=fetch_titles)
        
        inventory['collections'][result['name']] = result
        inventory['summary']['total_papers'] += result['total']
        
        # Print summary for this collection
        print(f"  - Expected papers: {result['total']}")
        if result['relevant_papers']:
            print(f"  - Relevant papers found: {len(result['relevant_papers'])}")
    
    # Sort collections by size
    inventory['summary']['collections_by_size'] = sorted(
        [(name, data['total']) for name, data in inventory['collections'].items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Detailed analysis of key collections
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS OF KEY COLLECTIONS")
    print("=" * 80)
    
    for collection_name in key_collections:
        if collection_name in inventory['collections']:
            data = inventory['collections'][collection_name]
            inventory['summary']['key_collections'][collection_name] = {
                'total': data['total'],
                'sample_papers': data['papers'][:10],  # First 10 papers
                'relevant_count': len(data['relevant_papers'])
            }
            
            print(f"\n{collection_name.upper()} Collection:")
            print(f"  Total expected papers: {data['total']}")
            print(f"  Sample paper IDs:")
            for paper in data['papers'][:5]:
                print(f"    - {paper['id']}: {paper['url']}")
                if paper['title']:
                    print(f"      Title: {paper['title'][:80]}...")
    
    # Save inventory to JSON
    output_path = 'paper_inventory_expected.json'
    with open(output_path, 'w') as f:
        json.dump(inventory, f, indent=2)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("INVENTORY SUMMARY")
    print("=" * 80)
    print(f"Total collections: {inventory['summary']['total_collections']}")
    print(f"Total expected papers: {inventory['summary']['total_papers']}")
    
    print("\nTop 20 Collections by Expected Paper Count:")
    for name, count in inventory['summary']['collections_by_size'][:20]:
        print(f"  - {name}: {count} papers")
    
    print(f"\nFull inventory saved to: {output_path}")
    
    # Create focused summary
    print("\n" + "=" * 80)
    print("COLLECTIONS MOST RELEVANT TO CODE/AGENT/EFFICIENCY/INTEGRATION")
    print("=" * 80)
    
    relevant_collections = [
        ('coding', 'Code generation, synthesis, analysis, and quality'),
        ('agent', 'AI agents, tool use, and autonomous systems'),
        ('benchmark', 'Performance benchmarks and evaluation'),
        ('efficiency', 'Model efficiency and optimization'),
        ('tool', 'Tool use and integration (if exists)'),
        ('debug', 'Debugging and error handling (if exists)'),
        ('test', 'Testing and validation (if exists)'),
        ('integration', 'System integration (if exists)'),
        ('rag', 'Retrieval-augmented generation'),
        ('peft', 'Parameter-efficient fine-tuning'),
        ('prompt', 'Prompt engineering and optimization'),
        ('instruct', 'Instruction following and tuning'),
        ('evaluation', 'Model evaluation and metrics'),
        ('optimization', 'Various optimization techniques'),
        ('llm-architecture', 'LLM architectural improvements')
    ]
    
    for coll_name, description in relevant_collections:
        if coll_name in inventory['collections']:
            data = inventory['collections'][coll_name]
            print(f"\n{coll_name}: {description}")
            print(f"  - Papers: {data['total']}")

if __name__ == "__main__":
    main()