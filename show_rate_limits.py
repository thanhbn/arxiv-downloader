#!/usr/bin/env python3
"""
Display current rate limiting configuration and estimated download times
"""

import subprocess
import sys
import os

def show_rate_limits():
    """Show current rate limiting settings and time estimates"""
    print("🚦 ARXIV DOWNLOAD RATE LIMITING CONFIGURATION")
    print("="*80)
    
    # Show bash configuration
    try:
        result = subprocess.run([
            'bash', '-c', 
            'source ./download_config.sh && show_config'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Error loading configuration")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n⏱️ TIME ESTIMATES FOR COLLECTIONS")
    print("-"*80)
    
    # Calculate estimates for different collection sizes
    base_delay = 10  # Conservative mode: 5s * 2
    random_delay = 2  # Average of 1-3s
    batch_break = 60  # Conservative mode: 30s * 2
    batch_size = 10
    
    collection_sizes = [1, 5, 10, 25, 50, 100, 200, 252]  # Including largest collection
    
    for size in collection_sizes:
        # Calculate time per file
        time_per_file = base_delay + random_delay
        
        # Calculate batch breaks
        num_batches = (size - 1) // batch_size
        total_batch_breaks = num_batches * batch_break
        
        # Total time in seconds
        total_seconds = (size * time_per_file) + total_batch_breaks
        
        # Convert to minutes
        total_minutes = total_seconds / 60
        
        print(f"📁 {size:>3} files → {total_minutes:>5.1f} minutes")
    
    print(f"\n📊 COLLECTION SUMMARY")
    print("-"*80)
    
    # Analyze actual collections
    try:
        sys.path.append('.')
        from arxiv_orchestrator import ArxivOrchestrator
        
        orchestrator = ArxivOrchestrator()
        collection_urls = orchestrator.get_collection_urls()
        
        total_files = 0
        largest_collection = 0
        collections_over_100 = 0
        
        for url in collection_urls:
            collection_name = orchestrator.extract_collection_name(url)
            links_file = f"./{collection_name}/arxiv_links.txt"
            
            try:
                with open(links_file, 'r') as f:
                    link_count = len([line for line in f if line.strip()])
                total_files += link_count
                
                if link_count > largest_collection:
                    largest_collection = link_count
                    
                if link_count > 100:
                    collections_over_100 += 1
                    
            except:
                pass
        
        # Calculate total estimated time
        avg_time_per_file = base_delay + random_delay + (batch_break / batch_size)
        total_estimated_hours = (total_files * avg_time_per_file) / 3600
        
        # Add inter-collection delays (30 seconds between collections)
        inter_collection_time = (len(collection_urls) - 1) * 30 / 3600  # hours
        
        total_estimated_hours += inter_collection_time
        
        print(f"📋 Total collections: {len(collection_urls)}")
        print(f"📁 Total files to download: {total_files}")
        print(f"📊 Largest collection: {largest_collection} files")
        print(f"🔢 Collections with >100 files: {collections_over_100}")
        print(f"⏱️  Estimated total time: {total_estimated_hours:.1f} hours")
        print(f"📅 Estimated completion: ~{total_estimated_hours/8:.1f} working days (8hrs/day)")
        
    except Exception as e:
        print(f"❌ Error analyzing collections: {e}")
    
    print(f"\n🛡️ SAFETY MEASURES")
    print("-"*80)
    print("✅ User-Agent identifies as academic research bot")
    print("✅ Random delays between downloads (10-13 seconds)")
    print("✅ Extended breaks every 10 downloads (60 seconds)")
    print("✅ 30-second delays between collections")
    print("✅ Conservative retry delays (30 seconds)")
    print("✅ Daily limit warning at 500 files")
    print("✅ Respects ArXiv robots.txt and terms of service")

if __name__ == "__main__":
    show_rate_limits()