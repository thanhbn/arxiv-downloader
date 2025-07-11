#!/usr/bin/env python3
"""
Quick status checker for all collections
"""

import sys
sys.path.append('.')

from arxiv_orchestrator import ArxivOrchestratorOptimized

def check_all_status():
    """Check status of all collections"""
    try:
        orchestrator = ArxivOrchestratorOptimized()
        
        # Get collection URLs
        collection_urls = orchestrator.get_collection_urls()
        print(f"📋 Found {len(collection_urls)} total collections")
        print("="*80)
        
        completed = 0
        pending = 0
        has_links = 0
        
        for i, url in enumerate(collection_urls, 1):
            collection_name = orchestrator.extract_collection_name(url)
            progress = orchestrator.load_progress(collection_name)
            
            # Check if arxiv_links.txt exists and count links
            links_file = f"./{collection_name}/arxiv_links.txt"
            try:
                with open(links_file, 'r') as f:
                    link_count = len([line for line in f if line.strip()])
                has_links += 1
            except:
                link_count = 0
            
            status = progress.get('status', 'pending')
            if status == 'completed':
                completed += 1
            else:
                pending += 1
                
            status_icon = "✅" if status == "completed" else "⏳"
            print(f"{status_icon} {collection_name:<30} | {link_count:>3} links | {status}")
        
        print("\n" + "="*80)
        print(f"📊 SUMMARY:")
        print(f"  ✅ Completed: {completed}")
        print(f"  ⏳ Pending: {pending}")
        print(f"  📁 Collections with links: {has_links}")
        print(f"  📋 Total collections: {len(collection_urls)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_status()