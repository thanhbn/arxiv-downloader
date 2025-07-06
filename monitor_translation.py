#!/usr/bin/env python3
"""
Translation Progress Monitor

Real-time monitoring tool for the translation manager.
Shows live progress, queue status, and worker activity.

Usage:
    python monitor_translation.py [--queue-file FILE] [--refresh-rate SECONDS]
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import psutil

class TranslationMonitor:
    """Monitor translation progress in real-time."""
    
    def __init__(self, queue_file: str = "translation_queue.txt", refresh_rate: int = 5):
        self.queue_file = Path(queue_file)
        self.log_file = Path("translation_manager.log")
        self.refresh_rate = refresh_rate
        self.start_time = datetime.now()
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def get_queue_status(self):
        """Get current queue status."""
        if not self.queue_file.exists():
            return {"total": 0, "processing": 0, "pending": 0, "completed": 0}
            
        try:
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            total = len(lines)
            processing = sum(1 for line in lines if line.startswith('[Processing]'))
            pending = total - processing
            
            return {
                "total": total,
                "processing": processing, 
                "pending": pending,
                "completed": 0  # Will be calculated from initial total
            }
        except Exception:
            return {"total": 0, "processing": 0, "pending": 0, "completed": 0}
    
    def get_translation_processes(self):
        """Get list of active translation processes."""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                try:
                    if 'claude' in proc.info['name'] or any('claude' in arg for arg in (proc.info['cmdline'] or [])):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline'] or []),
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_mb': proc.info['memory_info'].rss / 1024 / 1024 if proc.info['memory_info'] else 0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return processes
    
    def get_recent_log_entries(self, num_lines: int = 10):
        """Get recent log entries."""
        if not self.log_file.exists():
            return []
            
        try:
            lines = self.log_file.read_text().strip().split('\n')
            return lines[-num_lines:] if lines else []
        except Exception:
            return []
    
    def format_duration(self, seconds: int):
        """Format duration in human readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def display_status(self):
        """Display current translation status."""
        self.clear_screen()
        
        # Header
        print("=" * 80)
        print("🔄 TRANSLATION MANAGER MONITOR")
        print("=" * 80)
        
        # Runtime info
        runtime = datetime.now() - self.start_time
        print(f"⏱️  Monitor Runtime: {self.format_duration(int(runtime.total_seconds()))}")
        print(f"🔄 Refresh Rate: {self.refresh_rate}s")
        print(f"📁 Queue File: {self.queue_file}")
        print()
        
        # Queue status
        status = self.get_queue_status()
        print("📊 QUEUE STATUS")
        print("-" * 40)
        print(f"Total Files:      {status['total']:>6}")
        print(f"Currently Processing: {status['processing']:>2}")
        print(f"Pending:          {status['pending']:>6}")
        
        if status['total'] > 0:
            progress_percent = ((status['total'] - status['pending']) / status['total']) * 100
            progress_bar = "█" * int(progress_percent // 2) + "░" * (50 - int(progress_percent // 2))
            print(f"Progress:         [{progress_bar}] {progress_percent:.1f}%")
        print()
        
        # Active processes
        processes = self.get_translation_processes()
        print(f"🖥️  ACTIVE CLAUDE PROCESSES ({len(processes)})")
        print("-" * 40)
        if processes:
            for proc in processes[:5]:  # Show max 5 processes
                print(f"PID {proc['pid']:>6}: {proc['name']:<15} CPU: {proc['cpu_percent']:>5.1f}% MEM: {proc['memory_mb']:>6.1f}MB")
                if len(proc['cmdline']) > 60:
                    print(f"         {proc['cmdline'][:60]}...")
                else:
                    print(f"         {proc['cmdline']}")
        else:
            print("No active Claude processes found")
        print()
        
        # Recent log entries
        log_entries = self.get_recent_log_entries(8)
        print("📝 RECENT LOG ENTRIES")
        print("-" * 40)
        if log_entries:
            for entry in log_entries:
                if len(entry) > 76:
                    print(f"{entry[:76]}...")
                else:
                    print(entry)
        else:
            print("No log entries found")
        print()
        
        # File system info
        try:
            disk_usage = psutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            total_gb = disk_usage.total / (1024**3)
            used_percent = ((disk_usage.total - disk_usage.free) / disk_usage.total) * 100
            print(f"💾 Disk Space: {free_gb:.1f}GB free / {total_gb:.1f}GB total ({used_percent:.1f}% used)")
        except Exception:
            print("💾 Disk Space: Unable to determine")
        
        # Memory info
        try:
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            print(f"🧠 Memory: {memory_used_gb:.1f}GB / {memory_gb:.1f}GB ({memory.percent:.1f}% used)")
        except Exception:
            print("🧠 Memory: Unable to determine")
        
        print()
        print("Press Ctrl+C to exit monitor")
        print("=" * 80)
    
    def run(self):
        """Run the monitoring loop."""
        print("Starting Translation Monitor...")
        print(f"Monitoring queue file: {self.queue_file}")
        print(f"Refresh rate: {self.refresh_rate} seconds")
        print()
        
        try:
            while True:
                self.display_status()
                time.sleep(self.refresh_rate)
        except KeyboardInterrupt:
            print("\n\nMonitor stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"\nMonitor error: {e}")
            sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Translation Progress Monitor")
    parser.add_argument("--queue-file", type=str, default="translation_queue.txt",
                       help="Path to translation queue file (default: translation_queue.txt)")
    parser.add_argument("--refresh-rate", type=int, default=5,
                       help="Screen refresh rate in seconds (default: 5)")
    parser.add_argument("--log-lines", type=int, default=8,
                       help="Number of recent log lines to show (default: 8)")
    
    args = parser.parse_args()
    
    # Validate refresh rate
    if args.refresh_rate < 1 or args.refresh_rate > 60:
        print("Refresh rate must be between 1 and 60 seconds")
        sys.exit(1)
    
    # Create and run monitor
    monitor = TranslationMonitor(
        queue_file=args.queue_file,
        refresh_rate=args.refresh_rate
    )
    
    monitor.run()

if __name__ == "__main__":
    main()