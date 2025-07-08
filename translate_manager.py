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
                    filename = line.strip()
                    
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
                        # Mark as processing with timestamp
                        timestamp = self._generate_timestamp()
                        lines[i] = f"[Processing] {timestamp} {filename}"
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
                # Check if line contains the filename
                if filename in line or line.endswith(filename):
                    continue
                # For processing lines, extract the actual filename part
                if line.startswith('[Processing]'):
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
    
    def __init__(self, claude_path: str = "claude"):
        self.claude_path = claude_path
        self.translation_prompt = self._build_translation_prompt()
        
    def _build_translation_prompt(self) -> str:
        """Build the translation prompt template."""
        return """Translate this text to Vietnamese. Output ONLY the translation, no explanations, no summaries, no meta-commentary:

{content}

IMPORTANT: Output only the Vietnamese translation. Do not explain what you did. Do not summarize. Start with the first Vietnamese sentence immediately."""
    
    def translate_file(self, input_file: str) -> bool:
        """Translate a single file using Claude executable."""
        input_path = Path(input_file)
        worker_pid = os.getpid()
        
        # Get worker-specific logger
        worker_logger = logging.getLogger(f"worker_{worker_pid}")
        if not worker_logger.handlers:
            worker_logger = logger  # Fallback to main logger
        
        if not input_path.exists():
            worker_logger.error(f"Input file does not exist: {input_file}")
            return False
            
        # Generate output filename
        if input_path.suffix == '.txt':
            output_path = input_path.with_stem(input_path.stem + '_vi').with_suffix('.txt')
        else:
            output_path = input_path.with_suffix(input_path.suffix + '_vi.txt')
        
        try:
            # Read input file content and sanitize
            content = input_path.read_text(encoding='utf-8')
            
            # Remove null bytes and other problematic characters
            content = content.replace('\x00', '').replace('\r', '\n')
            
            # Build full prompt
            full_prompt = self.translation_prompt.format(content=content)
            
            # Create temporary file for the prompt to avoid "argument list too long" error
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(full_prompt)
                temp_prompt_path = temp_file.name
            
            try:
                # Use Claude CLI with stdin to avoid argument length limits
                cmd = [
                    self.claude_path,
                    "--print",
                    "--dangerously-skip-permissions",
                    "--model", "sonnet"
                ]
                
                worker_logger.info(f"Translating {input_file} -> {output_path}")
                worker_logger.info(f"Running Claude CLI with stdin input and --dangerously-skip-permissions")
                
                # Run Claude with stdin input
                try:
                    worker_logger.info(f"Processing {len(content)} chars with Claude CLI")
                    worker_logger.info("Starting Claude translation...")
                    
                    result = subprocess.run(
                        cmd,
                        input=full_prompt,
                        capture_output=True,
                        text=True,
                        timeout=1200  # 20 minute timeout
                    )
                    
                    stdout = result.stdout
                    stderr = result.stderr
                    return_code = result.returncode
                    
                    worker_logger.info(f"Claude process completed with return code: {return_code}")
                    if stderr:
                        worker_logger.warning(f"Claude stderr: {stderr[:500]}...")  # Log first 500 chars of stderr
                    
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
                            return True
                        else:
                            # Check if it's a configuration corruption error
                            if any(indicator in stdout for indicator in ["configuration file", "corrupted", "Unexpected end of JSON input"]):
                                worker_logger.warning(f"Configuration corruption detected, retrying in 5 seconds...")
                                time.sleep(5)  # Wait for config file to be restored
                                # Try once more with simpler command using stdin
                                simple_cmd = [self.claude_path, "--print", "--dangerously-skip-permissions"]
                                try:
                                    retry_result = subprocess.run(simple_cmd, input=full_prompt, capture_output=True, text=True, timeout=1200)
                                    if retry_result.returncode == 0 and retry_result.stdout and len(retry_result.stdout.strip()) > 50:
                                        output_path.write_text(retry_result.stdout, encoding='utf-8')
                                        worker_logger.info(f"Retry successful: Translation saved to {output_path} ({len(retry_result.stdout)} chars)")
                                        return True
                                except Exception as retry_e:
                                    worker_logger.error(f"Retry also failed: {retry_e}")
                            
                            worker_logger.error(f"Invalid translation output: {stdout[:200]}...")
                            worker_logger.error(f"Stderr: {stderr}")
                            return False
                    else:
                        worker_logger.error(f"Claude command failed with return code {return_code}")
                        worker_logger.error(f"Error output: {stderr}")
                        return False
                        
                except subprocess.TimeoutExpired:
                    worker_logger.error(f"Translation timeout (1200s) for {input_file}")
                    worker_logger.info(f"Claude CLI process timed out")
                    return False
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_prompt_path):
                    os.unlink(temp_prompt_path)
                    
        except Exception as e:
            worker_logger.error(f"Error translating {input_file}: {e}")
            import traceback
            worker_logger.error(f"Exception traceback: {traceback.format_exc()}")
            return False

def translate_worker(args: Tuple[str, str]) -> Tuple[str, bool]:
    """Worker function for multiprocessing translation."""
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
        translator = ClaudeTranslator(claude_path)
        worker_logger.info(f"Translator initialized for {filename}")
        
        result = translator.translate_file(filename)
        
        if result:
            worker_logger.info(f"Successfully translated {filename}")
        else:
            worker_logger.error(f"Failed to translate {filename}")
            
        return (filename, result)
    except Exception as e:
        worker_logger.error(f"Worker exception for {filename}: {e}")
        import traceback
        worker_logger.error(f"Traceback: {traceback.format_exc()}")
        return (filename, False)

def idle_worker(args: Tuple[str, str]) -> Tuple[Optional[str], bool]:
    """Idle worker function that polls for new files and processes them."""
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
        translator = ClaudeTranslator(claude_path)
        
        # Poll for files every 5 seconds
        poll_interval = 5
        max_idle_time = 300  # 5 minutes max idle time
        idle_start = time.time()
        
        while True:
            # Check if we've been idle too long
            if time.time() - idle_start > max_idle_time:
                worker_logger.info("Max idle time reached, shutting down idle worker")
                return (None, True)
            
            # Try to get a file (blocking mode to mark as processing)
            filename = queue_manager.get_next_file(blocking=True)
            
            if filename:
                worker_logger.info(f"Idle worker picked up file: {filename}")
                # Reset idle timer since we got work
                idle_start = time.time()
                
                # Process the file
                result = translator.translate_file(filename)
                
                if result:
                    worker_logger.info(f"Successfully translated {filename}")
                    queue_manager.mark_completed(filename)
                    return (filename, True)
                else:
                    worker_logger.error(f"Failed to translate {filename}")
                    queue_manager.mark_completed(filename)
                    return (filename, False)
            else:
                # No files available, sleep and try again
                time.sleep(poll_interval)
                
    except Exception as e:
        worker_logger.error(f"Idle worker exception: {e}")
        import traceback
        worker_logger.error(f"Traceback: {traceback.format_exc()}")
        return (None, False)

class TranslationManager:
    """Main translation manager orchestrating the entire process."""
    
    def __init__(self, queue_file: str = "translation_queue.txt", 
                 claude_path: str = "claude", max_workers: int = 6):
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
                    
                    # Periodically clean stale processing entries (every 5 minutes)
                    if current_time - self.last_stale_cleanup > 300:  # 5 minutes
                        stale_cleaned = self.queue_manager.clean_stale_processing()
                        if stale_cleaned > 0:
                            logger.info(f"Cleaned {stale_cleaned} stale processing entries")
                            # Refresh queue status after cleaning
                            total, processing, pending = self.queue_manager.get_queue_status()
                        self.last_stale_cleanup = current_time
                    
                    # Only log status if it changed or 60 seconds have passed
                    status_changed = (total, processing, pending) != self.last_status
                    time_for_update = current_time - self.last_status_log > 60
                    
                    if status_changed or time_for_update:
                        logger.info(f"Queue status - Total: {total}, Processing: {processing}, Pending: {pending}")
                        self.last_status = (total, processing, pending)
                        self.last_status_log = current_time
                    
                    # Check if we're done (only if we have no processing items left)
                    if pending == 0 and processing == 0 and len(futures) == 0:
                        if total == 0:
                            logger.info("Queue is empty. Nothing to process.")
                        else:
                            logger.info("All files completed successfully.")
                        break
                    
                    # If we have pending work but no futures, something went wrong
                    if pending > 0 and len(futures) == 0:
                        logger.warning(f"No active workers but {pending} pending files. Checking for stale entries and attempting to start workers...")
                        # Clean stale entries first
                        stale_cleaned = self.queue_manager.clean_stale_processing()
                        if stale_cleaned > 0:
                            logger.info(f"Cleaned {stale_cleaned} additional stale processing entries")
                            # Refresh queue status after cleaning
                            total, processing, pending = self.queue_manager.get_queue_status()
                        
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
                            result_filename, success = future.result()
                            
                            if worker_type == 'file':
                                # File worker completed
                                if success and result_filename:
                                    logger.info(f"Successfully completed: {result_filename}")
                                    # No need to mark completed here - worker already did it
                                elif result_filename:
                                    logger.error(f"Failed to translate: {result_filename}")
                                    # No need to mark completed here - worker already did it
                            elif worker_type == 'idle':
                                # Idle worker completed
                                if success and result_filename:
                                    logger.info(f"Idle worker successfully completed: {result_filename}")
                                elif result_filename:
                                    logger.error(f"Idle worker failed to translate: {result_filename}")
                                else:
                                    logger.info(f"Idle worker {worker_id} shut down (no work or timeout)")
                                    
                        except Exception as e:
                            logger.error(f"Error processing result for {worker_id}: {e}")
                            # For file workers, try to clean up if we know the filename
                            if worker_type == 'file':
                                try:
                                    self.queue_manager.mark_completed(worker_id)
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
    parser.add_argument("--claude-path", type=str, default="claude",
                       help="Path to Claude executable (default: claude)")
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