#!/usr/bin/env python3
"""
Test version of ArXiv Orchestrator to verify functionality with one collection
"""

import sys
import os
sys.path.append('/home/admin88/arxiv-downloader')

from arxiv_orchestrator import ArxivOrchestrator

def test_single_collection():
    """Test with a single collection"""
    try:
        orchestrator = ArxivOrchestrator()
        
        # Get collection URLs
        collection_urls = orchestrator.get_collection_urls()
        if not collection_urls:
            print("❌ No collection URLs found!")
            return
        
        # Test with the first collection that has fewer links
        test_url = None
        for url in collection_urls:
            collection_name = orchestrator.extract_collection_name(url)
            # Look for a collection with fewer links for testing
            if collection_name in ['perceiver', 'emergent', 'emotion', 'fashion']:
                test_url = url
                break
        
        if not test_url:
            test_url = collection_urls[0]  # Fallback to first collection
        
        print(f"🧪 Testing with single collection: {test_url}")
        print("="*80)
        
        # Process just this one collection
        result = orchestrator.process_collection(test_url)
        
        if result:
            print("✅ Test collection processed successfully!")
        else:
            print("❌ Test collection failed!")
        
        # Show progress file
        collection_name = orchestrator.extract_collection_name(test_url)
        progress = orchestrator.load_progress(collection_name)
        print(f"\n📊 Final progress for {collection_name}:")
        print(f"  Status: {progress.get('status', 'unknown')}")
        print(f"  Total links: {progress.get('total_links', 0)}")
        print(f"  Downloaded: {progress.get('downloaded_count', 0)}")
        if progress.get('error_message'):
            print(f"  Error: {progress['error_message']}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_collection()