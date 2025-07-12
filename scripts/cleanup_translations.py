#!/usr/bin/env python3
"""
Vietnamese Translation Cleanup Script
===================================

This script cleans up Vietnamese translation files that fall below a specified
quality threshold and optionally requeues the corresponding English files for
re-translation.

Features:
- Identifies Vietnamese translations with low completion ratios
- Removes poor quality translations with backup option
- Automatically requeues English files for re-translation
- Comprehensive logging and progress tracking
- Safe operation with dry-run mode

Usage:
    python3 cleanup_translations.py --threshold 0.1
    python3 cleanup_translations.py --threshold 0.2 --backup
    python3 cleanup_translations.py --threshold 0.1 --requeue --execute
    python3 cleanup_translations.py --help
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import shutil
import re
from datetime import datetime
import json

class TranslationCleanup:
    """Handles cleanup and requeuing of Vietnamese translation files."""
    
    def __init__(self, threshold: float = 0.1, backup: bool = False, 
                 requeue: bool = False, execute: bool = False):
        self.threshold = threshold
        self.backup = backup
        self.requeue = requeue
        self.execute = execute
        self.base_dir = Path.cwd()
        self.backup_dir = self.base_dir / "backup" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.queue_file = self.base_dir / "translation_queue.txt"
        self.queue_backup_file = self.base_dir / "translation_queue_backup.txt"
        
        # Statistics
        self.stats = {
            'total_vi_files': 0,
            'low_quality_files': 0,
            'files_removed': 0,
            'files_backed_up': 0,
            'files_requeued': 0,
            'errors': 0
        }
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'cleanup_translations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text (simple word-based approximation)."""
        return len(text.split())
    
    def calculate_completion_ratio(self, en_file: Path, vi_file: Path) -> float:
        """Calculate completion ratio between English and Vietnamese files."""
        try:
            if not en_file.exists() or not vi_file.exists():
                return 0.0
            
            en_text = en_file.read_text(encoding='utf-8', errors='ignore')
            vi_text = vi_file.read_text(encoding='utf-8', errors='ignore')
            
            en_tokens = self.count_tokens(en_text)
            vi_tokens = self.count_tokens(vi_text)
            
            if en_tokens == 0:
                return 0.0
            
            return vi_tokens / en_tokens
            
        except Exception as e:
            self.logger.error(f"Error calculating completion ratio for {vi_file}: {e}")
            return 0.0
    
    def find_vietnamese_files(self) -> List[Path]:
        """Find all Vietnamese translation files."""
        vi_files = []
        
        # Search all directories for *_vi.txt files
        for vi_file in self.base_dir.rglob("*_vi.txt"):
            if vi_file.is_file():
                vi_files.append(vi_file)
        
        self.logger.info(f"Found {len(vi_files)} Vietnamese translation files")
        return vi_files
    
    def find_corresponding_english_file(self, vi_file: Path) -> Optional[Path]:
        """Find the corresponding English file for a Vietnamese translation."""
        # Extract arXiv ID from Vietnamese filename
        vi_name = vi_file.name
        if '_vi.txt' in vi_name:
            arxiv_id = vi_name.replace('_vi.txt', '')
            
            # Look for any English file starting with this arXiv ID in the same directory
            for en_file in vi_file.parent.glob(f"{arxiv_id}*.txt"):
                if not en_file.name.endswith('_vi.txt') and en_file.is_file():
                    return en_file
            
            # Also check for PDF files with same arXiv ID
            pdf_file = vi_file.parent / f"{arxiv_id}.pdf"
            if pdf_file.exists():
                # If PDF exists but no English txt, we could consider the VI file orphaned
                pass
        
        # Fallback to original simple matching
        en_filename = vi_file.name.replace('_vi.txt', '.txt')
        en_file = vi_file.parent / en_filename
        
        if en_file.exists():
            return en_file
        
        return None
    
    def identify_low_quality_translations(self) -> List[Tuple[Path, Path, float]]:
        """Identify Vietnamese translations below the quality threshold."""
        vi_files = self.find_vietnamese_files()
        low_quality = []
        
        self.stats['total_vi_files'] = len(vi_files)
        
        self.logger.info(f"Analyzing {len(vi_files)} Vietnamese files with threshold {self.threshold}")
        
        for vi_file in vi_files:
            en_file = self.find_corresponding_english_file(vi_file)
            
            if en_file:
                ratio = self.calculate_completion_ratio(en_file, vi_file)
                
                if ratio < self.threshold:
                    low_quality.append((vi_file, en_file, ratio))
                    self.logger.debug(f"Low quality: {vi_file.name} (ratio: {ratio:.3f})")
            else:
                self.logger.warning(f"No English file found for {vi_file}")
        
        self.stats['low_quality_files'] = len(low_quality)
        self.logger.info(f"Found {len(low_quality)} low quality translations (< {self.threshold})")
        
        return low_quality
    
    def backup_file(self, file_path: Path) -> bool:
        """Backup a file to the backup directory."""
        try:
            if self.backup:
                # Create backup directory structure
                relative_path = file_path.relative_to(self.base_dir)
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file to backup location
                shutil.copy2(file_path, backup_path)
                self.logger.debug(f"Backed up {file_path} to {backup_path}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error backing up {file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def remove_file(self, file_path: Path) -> bool:
        """Remove a file after optional backup."""
        try:
            # Backup if requested
            if self.backup:
                if self.backup_file(file_path):
                    self.stats['files_backed_up'] += 1
            
            # Remove file if in execute mode
            if self.execute:
                file_path.unlink()
                self.stats['files_removed'] += 1
                self.logger.info(f"Removed {file_path}")
                return True
            else:
                self.logger.info(f"Would remove {file_path} (dry run)")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing {file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def add_to_queue(self, en_file: Path) -> bool:
        """Add English file to translation queue."""
        try:
            if not self.requeue:
                return False
            
            # Backup existing queue
            if self.queue_file.exists() and not self.queue_backup_file.exists():
                shutil.copy2(self.queue_file, self.queue_backup_file)
            
            # Add to queue
            queue_entry = str(en_file.relative_to(self.base_dir))
            
            if self.execute:
                with open(self.queue_file, 'a', encoding='utf-8') as f:
                    f.write(f"{queue_entry}\n")
                
                self.stats['files_requeued'] += 1
                self.logger.info(f"Added to queue: {queue_entry}")
                return True
            else:
                self.logger.info(f"Would add to queue: {queue_entry} (dry run)")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding {en_file} to queue: {e}")
            self.stats['errors'] += 1
            return False
    
    def generate_report(self, low_quality_files: List[Tuple[Path, Path, float]]) -> str:
        """Generate a detailed report of the cleanup operation."""
        report = []
        report.append("Vietnamese Translation Cleanup Report")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Threshold: {self.threshold}")
        report.append(f"Backup: {'Yes' if self.backup else 'No'}")
        report.append(f"Requeue: {'Yes' if self.requeue else 'No'}")
        report.append(f"Execute: {'Yes' if self.execute else 'No (dry run)'}")
        report.append("")
        
        # Statistics
        report.append("Statistics:")
        report.append(f"  Total Vietnamese files: {self.stats['total_vi_files']}")
        report.append(f"  Low quality files: {self.stats['low_quality_files']}")
        report.append(f"  Files removed: {self.stats['files_removed']}")
        report.append(f"  Files backed up: {self.stats['files_backed_up']}")
        report.append(f"  Files requeued: {self.stats['files_requeued']}")
        report.append(f"  Errors: {self.stats['errors']}")
        report.append("")
        
        # Low quality files details
        if low_quality_files:
            report.append("Low Quality Files:")
            report.append("-" * 30)
            for vi_file, en_file, ratio in low_quality_files:
                report.append(f"  {vi_file.name} (ratio: {ratio:.3f})")
                report.append(f"    English: {en_file.name}")
                report.append(f"    Vietnamese: {vi_file.name}")
                report.append("")
        
        return "\n".join(report)
    
    def run(self):
        """Run the cleanup operation."""
        self.logger.info("Starting Vietnamese translation cleanup")
        self.logger.info(f"Threshold: {self.threshold}")
        self.logger.info(f"Backup: {self.backup}")
        self.logger.info(f"Requeue: {self.requeue}")
        self.logger.info(f"Execute: {self.execute}")
        
        # Find low quality translations
        low_quality_files = self.identify_low_quality_translations()
        
        if not low_quality_files:
            self.logger.info("No low quality translations found")
            return
        
        # Create backup directory if needed
        if self.backup and self.execute:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created backup directory: {self.backup_dir}")
        
        # Process each low quality file
        for vi_file, en_file, ratio in low_quality_files:
            self.logger.info(f"Processing {vi_file.name} (ratio: {ratio:.3f})")
            
            # Remove Vietnamese file
            self.remove_file(vi_file)
            
            # Add English file to queue for re-translation
            if self.requeue:
                self.add_to_queue(en_file)
        
        # Generate and save report
        report = self.generate_report(low_quality_files)
        
        report_file = self.base_dir / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"Report saved to: {report_file}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("CLEANUP SUMMARY")
        print("=" * 50)
        print(f"Total Vietnamese files: {self.stats['total_vi_files']}")
        print(f"Low quality files: {self.stats['low_quality_files']}")
        print(f"Files removed: {self.stats['files_removed']}")
        print(f"Files backed up: {self.stats['files_backed_up']}")
        print(f"Files requeued: {self.stats['files_requeued']}")
        print(f"Errors: {self.stats['errors']}")
        
        if not self.execute:
            print("\n⚠️  This was a dry run. Use --execute to perform actual cleanup.")
        
        if self.backup and self.execute:
            print(f"\n📁 Backup directory: {self.backup_dir}")
        
        print(f"\n📊 Full report: {report_file}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Clean up Vietnamese translation files below quality threshold",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 cleanup_translations.py --threshold 0.1
  python3 cleanup_translations.py --threshold 0.2 --backup
  python3 cleanup_translations.py --threshold 0.1 --requeue --execute
  python3 cleanup_translations.py --threshold 0.05 --backup --requeue --execute
        """
    )
    
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.1,
        help='Quality threshold (default: 0.1)'
    )
    
    parser.add_argument(
        '--backup', '-b',
        action='store_true',
        help='Backup files before removal'
    )
    
    parser.add_argument(
        '--requeue', '-r',
        action='store_true',
        help='Add corresponding English files to translation queue'
    )
    
    parser.add_argument(
        '--execute', '-e',
        action='store_true',
        help='Execute actual cleanup (default is dry run)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate threshold
    if not 0 < args.threshold < 1:
        print("Error: Threshold must be between 0 and 1")
        sys.exit(1)
    
    # Create and run cleanup
    cleanup = TranslationCleanup(
        threshold=args.threshold,
        backup=args.backup,
        requeue=args.requeue,
        execute=args.execute
    )
    
    cleanup.run()

if __name__ == "__main__":
    main()