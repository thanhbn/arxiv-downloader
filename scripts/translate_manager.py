#!/usr/bin/env python3
"""
Automated Paper Translation Manager with Local Claude Executable

This script manages automatic translation of papers using a local Claude executable.
It handles queue management, parallel processing, and automatic confirmation of prompts.

Usage:
    python translate_manager.py [--workers N] [--claude-path PATH] [--queue-file FILE]
    
Example:
    python translate_manager.py --workers 4 --claude-path /usr/local/bin/claude
"""

import os
import sys
import argparse
import subprocess
import multiprocessing
import time
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import fcntl
import tempfile
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import signal
import glob
import re
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translation_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TranslationQueueManager:
    """Manages the translation queue with file locking for thread safety."""
    
    def __init__(self, queue_file: str = "translation_queue.txt"):
        self.queue_file = Path(queue_file)
        self.lock_file = Path(f"{queue_file}.lock")
        self.stale_threshold = 30 * 60  # 30 minutes in seconds
        self.max_retries = 2  # Maximum retry attempts per file
        self.retry_cooldown = 60 * 60  # 1 hour cooldown for max-retry files
        self.lock_fd = None  # Initialize lock file descriptor
        
    def _generate_timestamp(self) -> str:
        """Generate timestamp in yyyymmdd-HH24Mi format."""
        return datetime.now().strftime("%Y%m%d-%H%M")
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from yyyymmdd-HH24Mi format."""
        try:
            return datetime.strptime(timestamp_str, "%Y%m%d-%H%M")
        except ValueError:
            return None
    
    def _is_stale_processing(self, processing_line: str) -> bool:
        """Check if a processing line is stale (older than 30 minutes)."""
        # Format: [Processing] timestamp filename
        parts = processing_line.split(' ', 2)
        if len(parts) >= 3 and parts[0] == '[Processing]':
            timestamp_dt = self._parse_timestamp(parts[1])
            if timestamp_dt:
                age_seconds = (datetime.now() - timestamp_dt).total_seconds()
                return age_seconds > self.stale_threshold
        return False
        
    def _extract_arxiv_id(self, filename: str) -> Optional[str]:
        """Extract arxiv ID from filename."""
        # Extract the directory and filename
        path = Path(filename)
        filename_only = path.name
        
        # Pattern to match arxiv ID (YYMM.NNNNN)
        match = re.match(r'(\d{4}\.\d{5})', filename_only)
        if match:
            return match.group(1)
        return None
        
    def _has_vietnamese_translation(self, filename: str) -> bool:
        """Check if file already has a Vietnamese translation."""
        path = Path(filename)
        
        if not path.exists():
            return False
            
        arxiv_id = self._extract_arxiv_id(filename)
        if not arxiv_id:
            return False
            
        # Check for any file with the pattern: arxiv_id*_vi.txt in the same directory
        parent_dir = path.parent
        pattern = f"{arxiv_id}*_vi.txt"
        
        # Use glob to find matching files
        matches = list(parent_dir.glob(pattern))
        
        if matches:
            logger.info(f"Found existing Vietnamese translation for {filename}: {[str(m) for m in matches]}")
            return True
        
        return False
        
    def _acquire_lock(self):
        """Acquire file lock for safe concurrent access."""
        try:
            # Close any existing lock file descriptor first
            if hasattr(self, 'lock_fd') and self.lock_fd and not self.lock_fd.closed:
                try:
                    self.lock_fd.close()
                except:
                    pass
            
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            # Clean up on failure
            if hasattr(self, 'lock_fd') and self.lock_fd:
                try:
                    self.lock_fd.close()
                except:
                    pass
                self.lock_fd = None
            return False
            
    def _release_lock(self):
        """Release file lock."""
        try:
            if hasattr(self, 'lock_fd') and self.lock_fd and not self.lock_fd.closed:
                try:
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                except:
                    pass  # Ignore unlock errors
                try:
                    self.lock_fd.close()
                except:
                    pass  # Ignore close errors
            self.lock_fd = None  # Reset the file descriptor
            
            # Clean up lock file
            try:
                if self.lock_file.exists():
                    self.lock_file.unlink()
            except:
                pass  # Ignore file deletion errors
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            # Ensure lock_fd is reset even on error
            self.lock_fd = None
    
    def clean_stale_processing(self) -> int:
        """Clean up stale processing entries (older than 30 minutes). Returns count of cleaned entries."""
        if not self._acquire_lock():
            return 0
            
        try:
            if not self.queue_file.exists():
                return 0
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            cleaned_count = 0
            updated_lines = []
            
            for line in lines:
                if line.startswith('[Processing]') and self._is_stale_processing(line):
                    # Remove timestamp and [Processing] prefix from stale entries
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        clean_line = parts[2].strip()  # Extract just the filename
                        updated_lines.append(clean_line)
                        cleaned_count += 1
                        logger.info(f"Cleaned stale processing entry: {clean_line}")
                    else:
                        # Malformed line, keep as-is but log warning
                        updated_lines.append(line)
                        logger.warning(f"Malformed processing line: {line}")
                else:
                    updated_lines.append(line)
            
            if cleaned_count > 0:
                self.queue_file.write_text('\n'.join(updated_lines) + '\n' if updated_lines else '')
                logger.info(f"Cleaned {cleaned_count} stale processing entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning stale processing entries: {e}")
            return 0
        finally:
            self._release_lock()
            
    def get_next_file(self, blocking: bool = True) -> Optional[str]:
        """Get the next file to process from the queue.
        
        Args:
            blocking: If True, marks file as processing. If False, just returns next available file.
        """
        if not self._acquire_lock():
            return None
            
        try:
            if not self.queue_file.exists():
                if blocking:
                    logger.warning(f"Queue file {self.queue_file} does not exist")
                return None
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            # Find first line without [Processing] tag
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('[Processing]'):
                    raw_filename = line.strip()
                    
                    # Parse retry count and timestamp from filename
                    filename, retry_count, timestamp = self._parse_retry_info(raw_filename)
                    
                    # Skip files in cooldown period (max retries reached recently)
                    if retry_count >= self.max_retries and timestamp and self._is_in_cooldown(timestamp):
                        if blocking:
                            logger.debug(f"Skipping {filename} - in cooldown period after max retries")
                        continue
                    
                    # Check if this file already has a Vietnamese translation
                    if self._has_vietnamese_translation(filename):
                        if blocking:
                            logger.info(f"Skipping {filename} - already has Vietnamese translation")
                            # Remove from queue since it's already translated
                            lines.pop(i)
                            self.queue_file.write_text('\n'.join(lines) + '\n' if lines else '')
                            # Recursively call to get next file
                            return self.get_next_file(blocking)
                        else:
                            # In non-blocking mode, just continue to next file
                            continue
                    
                    if blocking:
                        # Mark as processing with timestamp, preserving retry count info
                        timestamp = self._generate_timestamp()
                        lines[i] = f"[Processing] {timestamp} {raw_filename}"
                        # Write back to file
                        self.queue_file.write_text('\n'.join(lines) + '\n')
                    
                    return filename
                    
            return None
            
        except Exception as e:
            if blocking:
                logger.error(f"Error reading queue file: {e}")
            return None
        finally:
            self._release_lock()
            
    def mark_completed(self, filename: str) -> bool:
        """Remove completed file from queue."""
        if not self._acquire_lock():
            return False
            
        try:
            if not self.queue_file.exists():
                return False
                
            lines = self.queue_file.read_text().strip().split('\n')
            original_count = len(lines)
            
            # Remove lines containing this filename (with or without [Processing] and timestamp)
            filtered_lines = []
            for line in lines:
                if not line.strip():
                    continue
                    
                # For processing lines, extract the actual filename part
                if line.startswith('[Processing]'):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        # New format: [Processing] timestamp filename
                        raw_filename = parts[2].strip()
                    elif len(parts) == 2:
                        # Old format: [Processing] filename
                        raw_filename = parts[1].strip()
                    else:
                        raw_filename = ""
                    
                    # Parse retry count from the filename
                    actual_filename, _, _ = self._parse_retry_info(raw_filename)
                    
                    if actual_filename == filename or actual_filename.endswith(filename):
                        continue
                else:
                    # Regular queue line, parse retry count
                    actual_filename, _, _ = self._parse_retry_info(line.strip())
                    
                    # Check if line contains the filename
                    if actual_filename == filename or actual_filename.endswith(filename):
                        continue
                
                filtered_lines.append(line)
            
            lines = filtered_lines
            
            self.queue_file.write_text('\n'.join(lines) + '\n' if lines else '')
            
            removed_count = original_count - len(lines)
            logger.info(f"Removed {removed_count} entries for {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking file as completed: {e}")
            return False
        finally:
            self._release_lock()
            
    def get_queue_status(self) -> Tuple[int, int, int]:
        """Get queue status: (total, processing, pending)."""
        if not self._acquire_lock():
            return (0, 0, 0)
            
        try:
            if not self.queue_file.exists():
                return (0, 0, 0)
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            total = len(lines)
            processing = sum(1 for line in lines if line.startswith('[Processing]'))
            pending = total - processing
            
            return (total, processing, pending)
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return (0, 0, 0)
        finally:
            self._release_lock()
            
    def reset_processing_status(self) -> int:
        """Reset all [Processing] items back to pending. Returns count of items reset."""
        if not self._acquire_lock():
            return 0
            
        try:
            if not self.queue_file.exists():
                return 0
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            reset_count = 0
            updated_lines = []
            
            for line in lines:
                if line.startswith('[Processing]'):
                    # Remove [Processing] prefix and timestamp if present
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        # New format: [Processing] timestamp filename
                        clean_line = parts[2].strip()
                    elif len(parts) == 2:
                        # Old format: [Processing] filename
                        clean_line = parts[1].strip()
                    else:
                        # Malformed line, try basic replacement
                        clean_line = line.replace('[Processing] ', '').strip()
                    
                    updated_lines.append(clean_line)
                    reset_count += 1
                else:
                    updated_lines.append(line)
            
            if reset_count > 0:
                self.queue_file.write_text('\n'.join(updated_lines) + '\n')
                logger.info(f"Reset {reset_count} processing items back to pending")
            
            return reset_count
            
        except Exception as e:
            logger.error(f"Error resetting processing status: {e}")
            return 0
        finally:
            self._release_lock()
    
    def _parse_retry_count(self, line: str) -> Tuple[str, int]:
        """Parse retry count from queue line. Returns (filename, retry_count)."""
        line = line.strip()
        if line.startswith('[retry:') and ']:' in line:
            # Format: [retry:N]:filename
            try:
                retry_part, filename = line.split(']:', 1)
                retry_count = int(retry_part.split(':', 1)[1])
                return filename.strip(), retry_count
            except (ValueError, IndexError):
                # Invalid format, treat as retry count 0
                return line, 0
        return line, 0
    
    def _format_with_retry_count(self, filename: str, retry_count: int) -> str:
        """Format filename with retry count."""
        if retry_count > 0:
            if retry_count >= self.max_retries:
                # Add timestamp for max-retry files to track cooldown
                timestamp = self._generate_timestamp()
                return f"[retry:{retry_count}:{timestamp}]:{filename}"
            else:
                return f"[retry:{retry_count}]:{filename}"
        return filename
    
    def _parse_retry_info(self, line: str) -> Tuple[str, int, Optional[str]]:
        """Parse retry count and timestamp from queue line. Returns (filename, retry_count, timestamp)."""
        line = line.strip()
        if line.startswith('[retry:') and ']:' in line:
            # Format: [retry:N:timestamp]:filename or [retry:N]:filename
            try:
                retry_part, filename = line.split(']:', 1)
                retry_info = retry_part.split(':', 1)[1]  # Remove '[retry:'
                
                if ':' in retry_info:
                    # Has timestamp: retry:N:timestamp
                    retry_count_str, timestamp = retry_info.split(':', 1)
                    retry_count = int(retry_count_str)
                    return filename.strip(), retry_count, timestamp
                else:
                    # No timestamp: retry:N
                    retry_count = int(retry_info)
                    return filename.strip(), retry_count, None
            except (ValueError, IndexError):
                # Invalid format, treat as retry count 0
                return line, 0, None
        return line, 0, None
    
    def _is_in_cooldown(self, timestamp_str: str) -> bool:
        """Check if a max-retry file is still in cooldown period."""
        if not timestamp_str:
            return False
        
        timestamp_dt = self._parse_timestamp(timestamp_str)
        if timestamp_dt:
            age_seconds = (datetime.now() - timestamp_dt).total_seconds()
            return age_seconds < self.retry_cooldown
        return False
    
    def handle_translation_failure(self, filename: str) -> bool:
        """Handle translation failure by incrementing retry count or removing if max retries reached.
        Returns True if file should be retried, False if max retries reached and file removed."""
        if not self._acquire_lock():
            return False
            
        try:
            if not self.queue_file.exists():
                return False
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            updated_lines = []
            file_handled = False
            
            for line in lines:
                if line.startswith('[Processing]'):
                    # Check if this processing line contains our filename
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        # New format: [Processing] timestamp filename
                        actual_filename = parts[2].strip()
                    elif len(parts) == 2:
                        # Old format: [Processing] filename
                        actual_filename = parts[1].strip()
                    else:
                        actual_filename = ""
                    
                    # Parse retry count and timestamp from the actual filename
                    clean_filename, retry_count, timestamp = self._parse_retry_info(actual_filename)
                    
                    if clean_filename == filename or clean_filename.endswith(filename):
                        # This is our file, increment retry count
                        retry_count += 1
                        
                        if retry_count >= self.max_retries:
                            # Max retries reached, move to end of queue to avoid blocking others
                            logger.warning(f"Max retries ({self.max_retries}) reached for {filename}, moving to end of queue")
                            file_handled = True
                            # Don't add to updated_lines here - we'll add it at the end
                        else:
                            # Increment retry count and reset to pending
                            formatted_filename = self._format_with_retry_count(filename, retry_count)
                            updated_lines.append(formatted_filename)
                            logger.info(f"Translation failed for {filename}, retry attempt {retry_count}/{self.max_retries}")
                            file_handled = True
                    else:
                        # Keep other processing entries as-is
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            if file_handled:
                # Check if we need to move file to end (max retries reached)
                file_moved_to_end = False
                for line in lines:
                    if line.startswith('[Processing]'):
                        parts = line.split(' ', 2)
                        if len(parts) >= 3:
                            actual_filename = parts[2].strip()
                        elif len(parts) == 2:
                            actual_filename = parts[1].strip()
                        else:
                            actual_filename = ""
                        
                        clean_filename, retry_count, timestamp = self._parse_retry_info(actual_filename)
                        
                        if clean_filename == filename or clean_filename.endswith(filename):
                            if retry_count + 1 >= self.max_retries:
                                # Move to end of queue with max retry marker
                                formatted_filename = self._format_with_retry_count(filename, self.max_retries)
                                updated_lines.append(formatted_filename)
                                file_moved_to_end = True
                                break
                
                # Write updated queue
                self.queue_file.write_text('\n'.join(updated_lines) + '\n')
                
                # Return True if file should be retried (retry count < max_retries)
                # Return False if file was moved to end (max retries reached)
                if file_moved_to_end:
                    return False  # File moved to end, don't retry immediately
                
                # Find the file in updated_lines to check its retry count
                for line in updated_lines:
                    clean_filename, retry_count, timestamp = self._parse_retry_info(line)
                    if clean_filename == filename or clean_filename.endswith(filename):
                        return retry_count < self.max_retries
                
                # If file not found in updated_lines, something went wrong
                return False
            
            return False  # File not found in processing state
            
        except Exception as e:
            logger.error(f"Error handling translation failure for {filename}: {e}")
            return False
        finally:
            self._release_lock()
            
    def reset_specific_file_processing(self, filename: str) -> bool:
        """Reset a specific file's processing status back to pending."""
        if not self._acquire_lock():
            return False
            
        try:
            if not self.queue_file.exists():
                return False
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            updated_lines = []
            reset_found = False
            
            for line in lines:
                if line.startswith('[Processing]'):
                    # Check if this processing line contains our filename
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        # New format: [Processing] timestamp filename
                        actual_filename = parts[2].strip()
                    elif len(parts) == 2:
                        # Old format: [Processing] filename
                        actual_filename = parts[1].strip()
                    else:
                        actual_filename = ""
                    
                    if actual_filename == filename or actual_filename.endswith(filename):
                        # Reset this specific file back to pending
                        updated_lines.append(filename)
                        reset_found = True
                        logger.info(f"Reset processing status for specific file: {filename}")
                    else:
                        # Keep other processing entries as-is
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            if reset_found:
                self.queue_file.write_text('\n'.join(updated_lines) + '\n')
            
            return reset_found
            
        except Exception as e:
            logger.error(f"Error resetting specific file processing: {e}")
            return False
        finally:
            self._release_lock()
            
    def clean_duplicate_arxiv_ids(self) -> int:
        """Remove duplicate arxiv_id.txt entries from queue, keeping only the longer filename versions."""
        if not self._acquire_lock():
            return 0
            
        try:
            if not self.queue_file.exists():
                return 0
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            # Group lines by arxiv_id
            arxiv_groups = {}
            
            for line in lines:
                # Extract clean filename from line (handling both old and new formats)
                if line.startswith('[Processing]'):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        # New format: [Processing] timestamp filename
                        clean_line = parts[2].strip()
                    elif len(parts) == 2:
                        # Old format: [Processing] filename
                        clean_line = parts[1].strip()
                    else:
                        clean_line = line.replace('[Processing] ', '').strip()
                else:
                    clean_line = line.strip()
                
                arxiv_id = self._extract_arxiv_id(clean_line)
                
                if arxiv_id:
                    if arxiv_id not in arxiv_groups:
                        arxiv_groups[arxiv_id] = []
                    arxiv_groups[arxiv_id].append(line)
            
            # Keep only the longest filename for each arxiv_id
            cleaned_lines = []
            removed_count = 0
            
            for line in lines:
                # Extract clean filename from line (handling both old and new formats)
                if line.startswith('[Processing]'):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        # New format: [Processing] timestamp filename
                        clean_line = parts[2].strip()
                    elif len(parts) == 2:
                        # Old format: [Processing] filename
                        clean_line = parts[1].strip()
                    else:
                        clean_line = line.replace('[Processing] ', '').strip()
                else:
                    clean_line = line.strip()
                
                arxiv_id = self._extract_arxiv_id(clean_line)
                
                if arxiv_id and arxiv_id in arxiv_groups:
                    # Find the longest filename for this arxiv_id
                    group_lines = arxiv_groups[arxiv_id]
                    
                    def extract_filename(line):
                        if line.startswith('[Processing]'):
                            parts = line.split(' ', 2)
                            if len(parts) >= 3:
                                return parts[2].strip()
                            elif len(parts) == 2:
                                return parts[1].strip()
                            else:
                                return line.replace('[Processing] ', '').strip()
                        return line.strip()
                    
                    longest_line = max(group_lines, key=lambda x: len(extract_filename(x)))
                    
                    if line == longest_line:
                        cleaned_lines.append(line)
                    else:
                        removed_count += 1
                        logger.info(f"Removing duplicate: {clean_line}")
                    
                    # Mark this arxiv_id as processed to avoid duplicates
                    del arxiv_groups[arxiv_id]
                else:
                    # Keep lines that don't have arxiv_id (shouldn't happen, but safe)
                    cleaned_lines.append(line)
            
            if removed_count > 0:
                self.queue_file.write_text('\n'.join(cleaned_lines) + '\n' if cleaned_lines else '')
                logger.info(f"Removed {removed_count} duplicate arxiv_id entries from queue")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning duplicate arxiv_ids: {e}")
            return 0
        finally:
            self._release_lock()

class ClaudeTranslator:
    """Handles translation using local Claude executable."""
    
    def __init__(self, claude_path: str = "/home/admin88/.nvm/versions/node/v18.20.8/bin/claude", worker_id: Optional[int] = None):
        self.claude_path = claude_path
        self.worker_id = worker_id or os.getpid()
        self.translation_prompt = self._build_translation_prompt()
        self.worker_home_dir = self._get_worker_home_dir()
        self.auth_lock_file = "/tmp/claude_auth.lock"
        
    def _acquire_auth_lock(self, timeout: int = 30) -> bool:
        """Acquire lock for Claude authentication/initialization only."""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Try to create lock file exclusively
                    with open(self.auth_lock_file, 'x') as f:
                        f.write(f"{self.worker_id}:{os.getpid()}:{time.time()}")
                    return True
                except FileExistsError:
                    # Check if lock is stale (older than 10 seconds - much more aggressive)
                    try:
                        if os.path.exists(self.auth_lock_file):
                            stat = os.stat(self.auth_lock_file)
                            if time.time() - stat.st_mtime > 5:  # 5 seconds for more aggressive cleanup
                                os.unlink(self.auth_lock_file)
                                continue
                    except:
                        pass
                    time.sleep(0.5)  # Wait 0.5 seconds before retry
            return False
        except Exception as e:
            logger.error(f"Error acquiring auth lock: {e}")
            return False
    
    def _release_auth_lock(self):
        """Release Claude authentication lock."""
        try:
            if os.path.exists(self.auth_lock_file):
                os.unlink(self.auth_lock_file)
        except Exception as e:
            logger.warning(f"Error releasing auth lock: {e}")
        
    def _get_worker_home_dir(self) -> str:
        """Get worker-specific home directory with Claude config."""
        # Use original config (authenticated) with random delays to reduce conflicts
        return os.path.expanduser("~")
        
    
    def _build_translation_prompt(self) -> str:
        """Build the translation prompt template."""
        return """Translate this text to Vietnamese. Output ONLY the translation, no explanations, no summaries, no meta-commentary:

{content}

IMPORTANT: Output only the Vietnamese translation. Do not explain what you did. Do not summarize. Start with the first Vietnamese sentence immediately."""
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content to prevent prompt injection and parsing errors."""
        # Remove null bytes and normalize line endings
        content = content.replace('\x00', '').replace('\r', '\n')
        
        # Replace problematic Unicode characters that may break prompts
        unicode_replacements = {
            # Mathematical symbols
            'α': 'alpha',
            'β': 'beta', 
            'γ': 'gamma',
            'δ': 'delta',
            'ε': 'epsilon',
            'ζ': 'zeta',
            'η': 'eta',
            'θ': 'theta',
            'ι': 'iota',
            'κ': 'kappa',
            'λ': 'lambda',
            'μ': 'mu',
            'ν': 'nu',
            'ξ': 'xi',
            'ο': 'omicron',
            'π': 'pi',
            'ρ': 'rho',
            'σ': 'sigma',
            'τ': 'tau',
            'υ': 'upsilon',
            'φ': 'phi',
            'χ': 'chi',
            'ψ': 'psi',
            'ω': 'omega',
            
            # Punctuation and symbols
            '–': '-',    # en dash
            '—': '-',    # em dash
            ''': "'",    # left single quotation
            ''': "'",    # right single quotation
            '"': '"',    # left double quotation
            '"': '"',    # right double quotation
            '…': '...',  # horizontal ellipsis
            '∗': '*',    # asterisk operator
            '≥': '>=',   # greater than or equal
            '≤': '<=',   # less than or equal
            '≠': '!=',   # not equal
            '≈': '~=',   # approximately equal
            '∈': 'in',   # element of
            '∉': 'not in', # not element of
            '∀': 'for all', # universal quantifier
            '∃': 'exists',  # existential quantifier
            '∅': 'empty set', # empty set
            '∪': 'union',    # union
            '∩': 'intersection', # intersection
            '⊂': 'subset',   # subset
            '⊃': 'superset', # superset
        }
        
        # Apply replacements
        for unicode_char, replacement in unicode_replacements.items():
            content = content.replace(unicode_char, replacement)
        
        # Remove or replace other problematic characters that could break prompts
        # Replace control characters (except \n and \t)
        import re
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # Escape potential prompt injection patterns
        # Replace sequences that might confuse the AI model
        content = content.replace('```', '`‌`‌`')  # Insert zero-width non-joiner
        content = content.replace('IMPORTANT:', 'Important:')
        content = content.replace('SYSTEM:', 'System:')
        content = content.replace('USER:', 'User:')
        content = content.replace('ASSISTANT:', 'Assistant:')
        
        return content

    def translate_file(self, input_file: str) -> tuple[bool, str]:
        """Translate a single file using Claude executable.
        
        Returns:
            tuple: (success, failure_reason)
            - success: True if translation successful, False if failed
            - failure_reason: 'auth_lock' for auth lock failure, 'translation' for other failures, 'success' for success
        """
        input_path = Path(input_file)
        worker_pid = os.getpid()
        
        # Get worker-specific logger
        worker_logger = logging.getLogger(f"worker_{worker_pid}")
        if not worker_logger.handlers:
            worker_logger = logger  # Fallback to main logger
        
        if not input_path.exists():
            worker_logger.error(f"Input file does not exist: {input_file}")
            return False, 'translation'
            
        # Generate output filename
        if input_path.suffix == '.txt':
            output_path = input_path.with_stem(input_path.stem + '_vi').with_suffix('.txt')
        else:
            output_path = input_path.with_suffix(input_path.suffix + '_vi.txt')
        
        try:
            # Read input file content and sanitize thoroughly
            content = input_path.read_text(encoding='utf-8')
            
            # Apply comprehensive sanitization to prevent prompt issues
            content = self._sanitize_content(content)
            
            # Build full prompt
            full_prompt = self.translation_prompt.format(content=content)
            
            # Create temporary file for the prompt to avoid "argument list too long" error
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(full_prompt)
                temp_prompt_path = temp_file.name
            
            try:
                # Use Claude CLI with worker-specific config
                cmd = [
                    self.claude_path,
                    "--print",
                    "--dangerously-skip-permissions",
                    "--model", "sonnet"
                ]
                
                # Use default environment (shared config with auth lock)
                env = os.environ.copy()
                
                worker_logger.info(f"Translating {input_file} -> {output_path}")
                worker_logger.info(f"Running Claude CLI with stdin input and --dangerously-skip-permissions")
                
                # Run Claude with stdin input
                try:
                    worker_logger.info(f"Processing {len(content)} chars with Claude CLI")
                    
                    # Retry auth lock acquisition up to 10 times with exponential backoff
                    max_auth_retries = 10
                    auth_retry_count = 0
                    
                    while auth_retry_count < max_auth_retries:
                        # Acquire auth lock only during Claude initialization/auth phase
                        if self._acquire_auth_lock():
                            worker_logger.info("Starting Claude translation (auth lock acquired)...")
                            break
                        else:
                            auth_retry_count += 1
                            if auth_retry_count < max_auth_retries:
                                backoff_time = min(2 ** auth_retry_count, 30)  # Cap at 30 seconds max
                                worker_logger.warning(f"Failed to acquire auth lock (attempt {auth_retry_count}/{max_auth_retries}), retrying in {backoff_time}s...")
                                time.sleep(backoff_time)
                            else:
                                worker_logger.error(f"Failed to acquire auth lock after {max_auth_retries} attempts")
                                return False, 'auth_lock'
                    
                    # Start Claude process
                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env
                    )
                    
                    # Release auth lock immediately after Claude process starts (within 2-3 seconds)
                    time.sleep(2)  # Give Claude 2 seconds to initialize
                    self._release_auth_lock()
                    worker_logger.debug("Auth lock released after 2s - other workers can proceed")
                    
                    # Now wait for Claude to complete translation
                    try:
                        stdout, stderr = process.communicate(input=full_prompt, timeout=1800)  # 30 minute timeout
                        return_code = process.returncode
                        result = type('Result', (), {'stdout': stdout, 'stderr': stderr, 'returncode': return_code})()
                    except subprocess.TimeoutExpired:
                        process.kill()
                        worker_logger.error("Claude process timed out after 30 minutes")
                        return False, 'translation'
                    
                    stdout = result.stdout
                    stderr = result.stderr
                    return_code = result.returncode
                    
                    worker_logger.info(f"Claude process completed with return code: {return_code}")
                    if stderr:
                        worker_logger.error(f"Claude stderr (full): {stderr}")  # Log full stderr for debugging
                    
                    if return_code == 0 and stdout:
                        # Check if output is valid translation (not summary)
                        invalid_indicators = [
                            "Execution error",
                            "Tôi đã dịch toàn bộ",
                            "Đây là một bài báo",
                            "I've successfully translated",
                            "The translation maintains",
                            "translation covers all",
                            "The translation preserves",
                            "Here is the translation",
                            "configuration file",
                            "corrupted",
                            "Unexpected end of JSON input",
                            "Claude configuration file at",
                            "The corrupted file has been back"
                        ]
                        is_valid = (stdout and len(stdout.strip()) > 50 and 
                                  not any(indicator in stdout for indicator in invalid_indicators))
                        
                        if is_valid:
                            # Save translation to output file
                            output_path.write_text(stdout, encoding='utf-8')
                            worker_logger.info(f"Translation saved to {output_path} ({len(stdout)} chars)")
                            worker_logger.info(f"Successfully completed translation of {input_file}")
                            return True, 'success'
                        else:
                            # Check if it's a configuration corruption error
                            if any(indicator in stdout for indicator in ["configuration file", "corrupted", "Unexpected end of JSON input"]):
                                worker_logger.warning(f"Configuration corruption detected, retrying in 5 seconds...")
                                time.sleep(5)  # Wait for config file to be restored
                                # Try once more with simpler command using stdin
                                simple_cmd = [self.claude_path, "--print", "--dangerously-skip-permissions"]
                                try:
                                    retry_result = subprocess.run(simple_cmd, input=full_prompt, capture_output=True, text=True, timeout=1800, env=env)
                                    if retry_result.returncode == 0 and retry_result.stdout and len(retry_result.stdout.strip()) > 50:
                                        output_path.write_text(retry_result.stdout, encoding='utf-8')
                                        worker_logger.info(f"Retry successful: Translation saved to {output_path} ({len(retry_result.stdout)} chars)")
                                        return True, 'success'
                                except Exception as retry_e:
                                    worker_logger.error(f"Retry also failed: {retry_e}")
                            
                            worker_logger.error(f"Invalid translation output: {stdout[:200]}...")
                            worker_logger.error(f"Stderr: {stderr}")
                            return False, 'translation'
                    else:
                        worker_logger.error(f"Claude command failed with return code {return_code}")
                        worker_logger.error(f"Error output: {stderr}")
                        return False, 'translation'
                        
                except subprocess.TimeoutExpired:
                    worker_logger.error(f"Translation timeout (1800s) for {input_file}")
                    worker_logger.info(f"Claude CLI process timed out")
                    return False, 'translation'
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_prompt_path):
                    os.unlink(temp_prompt_path)
                    
        except Exception as e:
            worker_logger.error(f"Error translating {input_file}: {e}")
            import traceback
            worker_logger.error(f"Exception traceback: {traceback.format_exc()}")
            return False, 'translation'

def translate_worker(args: Tuple[str, str]) -> Tuple[str, bool, str]:
    """Worker function for multiprocessing translation.
    
    Returns:
        tuple: (filename, success, failure_reason)
        - filename: The file that was processed
        - success: True if translation successful, False if failed
        - failure_reason: 'auth_lock' for auth lock failure, 'translation' for other failures, 'success' for success
    """
    filename, claude_path = args
    worker_pid = os.getpid()
    
    # Set up worker-specific logger
    worker_logger = logging.getLogger(f"worker_{worker_pid}")
    worker_logger.setLevel(logging.INFO)
    
    # Create worker-specific handler if not exists
    if not worker_logger.handlers:
        worker_handler = logging.StreamHandler()
        worker_formatter = logging.Formatter(
            f'%(asctime)s - WORKER-{worker_pid} - %(levelname)s - %(message)s'
        )
        worker_handler.setFormatter(worker_formatter)
        worker_logger.addHandler(worker_handler)
        worker_logger.propagate = False
    
    worker_logger.info(f"Starting translation of {filename}")
    
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        worker_logger.info(f"Received shutdown signal for {filename}")
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        translator = ClaudeTranslator(claude_path, worker_pid)
        worker_logger.info(f"Translator initialized for {filename} with worker ID {worker_pid}")
        
        success, failure_reason = translator.translate_file(filename)
        
        if success:
            worker_logger.info(f"Successfully translated {filename}")
        else:
            worker_logger.error(f"Failed to translate {filename}")
            
        return (filename, success, failure_reason)
    except Exception as e:
        worker_logger.error(f"Worker exception for {filename}: {e}")
        import traceback
        worker_logger.error(f"Traceback: {traceback.format_exc()}")
        return (filename, False, 'translation')

def idle_worker(args: Tuple[str, str]) -> Tuple[Optional[str], bool, str]:
    """Idle worker function that polls for new files and processes them.
    
    Returns:
        tuple: (filename, success, failure_reason)
        - filename: The file that was processed (None if no work)
        - success: True if translation successful, False if failed
        - failure_reason: 'auth_lock' for auth lock failure, 'translation' for other failures, 'success' for success, 'no_work' for no files
    """
    queue_file, claude_path = args
    worker_pid = os.getpid()
    
    # Set up worker-specific logger
    worker_logger = logging.getLogger(f"idle_worker_{worker_pid}")
    worker_logger.setLevel(logging.INFO)
    
    # Create worker-specific handler if not exists
    if not worker_logger.handlers:
        worker_handler = logging.StreamHandler()
        worker_formatter = logging.Formatter(
            f'%(asctime)s - IDLE-WORKER-{worker_pid} - %(levelname)s - %(message)s'
        )
        worker_handler.setFormatter(worker_formatter)
        worker_logger.addHandler(worker_handler)
        worker_logger.propagate = False
    
    worker_logger.info("Idle worker started, waiting for files...")
    
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        worker_logger.info("Idle worker received shutdown signal")
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        queue_manager = TranslationQueueManager(queue_file)
        translator = ClaudeTranslator(claude_path, worker_pid)
        
        # Poll for files every 5 seconds
        poll_interval = 5
        max_idle_time = 300  # 5 minutes max idle time
        idle_start = time.time()
        
        while True:
            # Check if we've been idle too long
            if time.time() - idle_start > max_idle_time:
                worker_logger.info("Max idle time reached, shutting down idle worker")
                return (None, True, 'no_work')
            
            # Try to get a file (blocking mode to mark as processing)
            filename = queue_manager.get_next_file(blocking=True)
            
            if filename:
                worker_logger.info(f"Idle worker picked up file: {filename}")
                # Reset idle timer since we got work
                idle_start = time.time()
                
                # Process the file
                success, failure_reason = translator.translate_file(filename)
                
                if success:
                    worker_logger.info(f"Successfully translated {filename}")
                    queue_manager.mark_completed(filename)
                    return (filename, True, 'success')
                elif failure_reason == 'auth_lock':
                    worker_logger.warning(f"Auth lock failure for {filename} - keeping in queue for retry")
                    # Don't mark as completed - let it stay in queue for retry
                    # Instead, reset this specific file back to pending status
                    queue_manager.reset_specific_file_processing(filename)
                    return (filename, False, 'auth_lock')
                else:
                    worker_logger.error(f"Translation failed for {filename} - handling retry logic")
                    # Use proper retry handling instead of immediate reset
                    should_retry = queue_manager.handle_translation_failure(filename)
                    if should_retry:
                        worker_logger.info(f"File {filename} will be retried")
                    else:
                        worker_logger.warning(f"File {filename} moved to end of queue after max retries")
                    return (filename, False, failure_reason)
            else:
                # No files available, sleep and try again
                time.sleep(poll_interval)
                
    except Exception as e:
        worker_logger.error(f"Idle worker exception: {e}")
        import traceback
        worker_logger.error(f"Traceback: {traceback.format_exc()}")
        return (None, False, 'translation')

class TranslationManager:
    """Main translation manager orchestrating the entire process."""
    
    def __init__(self, queue_file: str = "translation_queue.txt", 
                 claude_path: str = "/home/admin88/.nvm/versions/node/v18.20.8/bin/claude", max_workers: int = 6):
        self.queue_manager = TranslationQueueManager(queue_file)
        self.claude_path = claude_path
        self.max_workers = max_workers
        self.active_workers = 0
        self.worker_start_times = {}  # Track when each worker started
        self.warmup_threshold = 300  # 5 minutes in seconds
        self.last_status = (0, 0, 0)  # Track last status to reduce logging
        self.last_status_log = 0  # Track when we last logged status
        self.last_stale_cleanup = 0  # Track when we last cleaned stale entries
        
    def verify_claude_executable(self) -> bool:
        """Verify that Claude executable is available."""
        try:
            result = subprocess.run([self.claude_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            try:
                # Try without --version flag
                result = subprocess.run([self.claude_path, "--help"], 
                                      capture_output=True, text=True, timeout=10)
                return result.returncode == 0
            except Exception:
                return False
                
    def run(self):
        """Main execution loop."""
        logger.info("Starting Translation Manager")
        
        if not self.verify_claude_executable():
            logger.error(f"Claude executable not found or not working: {self.claude_path}")
            logger.error("Please ensure Claude is installed and in PATH, or specify correct path with --claude-path")
            return False
            
        logger.info(f"Claude executable verified: {self.claude_path}")
        logger.info(f"Maximum workers: {self.max_workers}")
        
        # Clean duplicate arxiv_id entries from queue before starting
        logger.info("Cleaning duplicate arxiv_id entries from translation queue...")
        removed_count = self.queue_manager.clean_duplicate_arxiv_ids()
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate entries from queue")
        
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                
                while True:
                    # Get queue status
                    total, processing, pending = self.queue_manager.get_queue_status()
                    current_time = time.time()
                    
                    
                    # Only log status if it changed or 60 seconds have passed
                    status_changed = (total, processing, pending) != self.last_status
                    time_for_update = current_time - self.last_status_log > 60
                    
                    if status_changed or time_for_update:
                        logger.info(f"Queue status - Total: {total}, Processing: {processing}, Pending: {pending}")
                        self.last_status = (total, processing, pending)
                        self.last_status_log = current_time
                    
                    # Check if we're done (only if we have no processing items left)
                    if pending == 0 and processing == 0 and len(futures) == 0:
                        # Clean stale processing entries at the end when pending = 0
                        stale_cleaned = self.queue_manager.clean_stale_processing()
                        if stale_cleaned > 0:
                            logger.info(f"Final cleanup: cleaned {stale_cleaned} stale processing entries")
                            # Refresh queue status after cleaning
                            total, processing, pending = self.queue_manager.get_queue_status()
                            # Continue the loop to recheck status after stale cleanup
                            continue
                        
                        if total == 0:
                            logger.info("Queue is empty. Nothing to process.")
                        else:
                            logger.info("All files completed successfully.")
                        break
                    
                    # If we have pending work but no futures, something went wrong
                    if pending > 0 and len(futures) == 0:
                        logger.warning(f"No active workers but {pending} pending files. Attempting to start workers...")
                        
                        # Try to start at least one worker before continuing
                        filename = self.queue_manager.get_next_file()
                        if filename:
                            future = executor.submit(translate_worker, (filename, self.claude_path))
                            futures[future] = ('file', filename)
                            self.worker_start_times[future] = time.time()
                            logger.info(f"Emergency restart: submitted {filename} for translation")
                        else:
                            logger.error("Failed to get next file from queue - queue may be corrupted")
                            time.sleep(5)  # Prevent busy loop
                        continue
                    
                    # If we have orphaned processing items but no active workers, reset them
                    if processing > 0 and len(futures) == 0:
                        logger.warning(f"Found {processing} orphaned processing items with no active workers. Resetting...")
                        reset_count = self.queue_manager.reset_processing_status()
                        if reset_count > 0:
                            logger.info(f"Reset {reset_count} orphaned items back to pending status")
                            # Force refresh of queue status after reset
                            time.sleep(0.5)
                        continue
                    
                    # Submit new jobs if we have capacity
                    while len(futures) < self.max_workers:
                        if pending > 0:
                            # Try to get a file for immediate processing
                            filename = self.queue_manager.get_next_file()
                            if filename:
                                future = executor.submit(translate_worker, (filename, self.claude_path))
                                futures[future] = ('file', filename)  # Mark as file worker
                                self.worker_start_times[future] = time.time()
                                logger.info(f"Submitted {filename} for translation")
                                continue
                        
                        # No pending files, but we have worker capacity - start idle worker
                        future = executor.submit(idle_worker, (str(self.queue_manager.queue_file), self.claude_path))
                        futures[future] = ('idle', f'idle_worker_{len(futures)}')  # Mark as idle worker
                        self.worker_start_times[future] = time.time()
                        logger.info(f"Started idle worker {len(futures)} (total workers: {len(futures)})")
                        
                        # Only start one idle worker per loop iteration to avoid flooding
                        break
                    
                    # Monitor worker health - log long-running workers for visibility
                    current_time = time.time()
                    long_running_count = 0
                    for future, start_time in self.worker_start_times.items():
                        if current_time - start_time > self.warmup_threshold:
                            long_running_count += 1
                    
                    if long_running_count > 0 and current_time - self.last_status_log > 300:  # Log every 5 minutes
                        logger.info(f"Status: {long_running_count} workers running >5min, total active workers: {len(futures)}")
                    
                    # Check completed jobs
                    completed_futures = []
                    try:
                        for future in as_completed(futures, timeout=1):
                            completed_futures.append(future)
                    except:
                        # No futures completed within timeout, continue
                        pass
                        
                    for future in completed_futures:
                        worker_type, worker_id = futures[future]
                        try:
                            result_filename, success, failure_reason = future.result()
                            
                            if worker_type == 'file':
                                # File worker completed
                                if success and result_filename:
                                    logger.info(f"Successfully completed: {result_filename}")
                                    self.queue_manager.mark_completed(result_filename)
                                elif result_filename and failure_reason == 'auth_lock':
                                    logger.warning(f"Auth lock failure for: {result_filename} - keeping in queue for retry")
                                    # Don't remove from queue - let another worker retry
                                    # Reset this specific file's processing status so it becomes available again
                                    self.queue_manager.reset_specific_file_processing(result_filename)
                                elif result_filename:
                                    logger.error(f"Translation failed for: {result_filename} (reason: {failure_reason}) - handling retry logic")
                                    # Use proper retry handling instead of immediate reset
                                    should_retry = self.queue_manager.handle_translation_failure(result_filename)
                                    if should_retry:
                                        logger.info(f"File {result_filename} will be retried")
                                    else:
                                        logger.warning(f"File {result_filename} moved to end of queue after max retries")
                            elif worker_type == 'idle':
                                # Idle worker completed
                                if success and result_filename:
                                    logger.info(f"Idle worker successfully completed: {result_filename}")
                                elif result_filename and failure_reason == 'auth_lock':
                                    logger.warning(f"Idle worker auth lock failure for: {result_filename} - kept in queue for retry")
                                elif result_filename:
                                    logger.error(f"Idle worker failed to translate: {result_filename} (reason: {failure_reason}) - kept in queue for retry")
                                else:
                                    logger.info(f"Idle worker {worker_id} shut down (no work or timeout)")
                                    
                        except Exception as e:
                            logger.error(f"Error processing result for {worker_id}: {e}")
                            # For file workers, try to clean up if we know the filename
                            # Reset processing status instead of removing from queue
                            if worker_type == 'file':
                                try:
                                    # If we can't determine the failure reason, reset to pending for retry
                                    self.queue_manager.reset_specific_file_processing(worker_id)
                                except:
                                    pass
                        
                        # Clean up tracking
                        if future in self.worker_start_times:
                            del self.worker_start_times[future]
                        del futures[future]
                    
                    # Brief pause to avoid busy waiting
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            # Wait for remaining futures to complete
            if futures:
                logger.info(f"Waiting for {len(futures)} remaining workers to complete...")
                for future in futures:
                    try:
                        future.result(timeout=30)  # Wait up to 30 seconds per future
                    except Exception as e:
                        logger.warning(f"Error waiting for future completion: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            # Wait for remaining futures to complete
            if futures:
                logger.info(f"Waiting for {len(futures)} remaining workers to complete...")
                for future in futures:
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        logger.warning(f"Error waiting for future completion: {e}")
            return False
            
        logger.info("Translation Manager completed successfully")
        return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Automated Paper Translation Manager")
    parser.add_argument("--workers", type=int, default=6,
                       help="Number of parallel workers (default: 6)")
    parser.add_argument("--claude-path", type=str, default="/home/admin88/.nvm/versions/node/v18.20.8/bin/claude",
                       help="Path to Claude executable (default: npm-global claude)")
    parser.add_argument("--queue-file", type=str, default="translation_queue.txt",
                       help="Path to translation queue file (default: translation_queue.txt)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--clean-only", action="store_true",
                       help="Only clean duplicates and already-translated files from queue, don't start translation")
    parser.add_argument("--clean-stale", action="store_true",
                       help="Only clean stale processing entries (>30 minutes) from queue, don't start translation")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate workers count
    if args.workers < 1 or args.workers > 16:
        logger.error("Number of workers must be between 1 and 16")
        sys.exit(1)
    
    # Create translation manager
    manager = TranslationManager(
        queue_file=args.queue_file,
        claude_path=args.claude_path,
        max_workers=args.workers
    )
    
    # If clean-only mode, just clean and exit
    if args.clean_only:
        logger.info("Running in clean-only mode...")
        logger.info("Cleaning duplicate arxiv_id entries from translation queue...")
        removed_count = manager.queue_manager.clean_duplicate_arxiv_ids()
        logger.info(f"Removed {removed_count} duplicate entries from queue")
        
        # Also scan and mark already-translated files
        logger.info("Scanning for files with existing Vietnamese translations...")
        scanned_count = 0
        skipped_count = 0
        
        while True:
            filename = manager.queue_manager.get_next_file()
            if not filename:
                break
            scanned_count += 1
            # The get_next_file method already handles skipping translated files
            # If we reach here, it means the file was skipped (already translated)
            # So we need to mark it as completed to remove it from queue
            manager.queue_manager.mark_completed(filename)
            skipped_count += 1
        
        logger.info(f"Scanned {scanned_count} files, marked {skipped_count} as already translated")
        logger.info("Queue cleanup completed successfully")
        sys.exit(0)
    
    # If clean-stale mode, just clean stale entries and exit
    if args.clean_stale:
        logger.info("Running in clean-stale mode...")
        logger.info("Cleaning stale processing entries (>30 minutes) from translation queue...")
        stale_cleaned = manager.queue_manager.clean_stale_processing()
        logger.info(f"Cleaned {stale_cleaned} stale processing entries")
        
        # Show queue status after cleaning
        total, processing, pending = manager.queue_manager.get_queue_status()
        logger.info(f"Queue status after cleanup - Total: {total}, Processing: {processing}, Pending: {pending}")
        logger.info("Stale cleanup completed successfully")
        sys.exit(0)
    
    # Run the translation process
    success = manager.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()