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
        
    def _acquire_lock(self):
        """Acquire file lock for safe concurrent access."""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
            
    def _release_lock(self):
        """Release file lock."""
        try:
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            self.lock_fd.close()
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            
    def get_next_file(self) -> Optional[str]:
        """Get the next file to process from the queue."""
        if not self._acquire_lock():
            return None
            
        try:
            if not self.queue_file.exists():
                logger.warning(f"Queue file {self.queue_file} does not exist")
                return None
                
            lines = self.queue_file.read_text().strip().split('\n')
            lines = [line for line in lines if line.strip()]
            
            # Find first line without [Processing] tag
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('[Processing]'):
                    # Mark as processing
                    lines[i] = f"[Processing] {line.strip()}"
                    
                    # Write back to file
                    self.queue_file.write_text('\n'.join(lines) + '\n')
                    
                    return line.strip()
                    
            return None
            
        except Exception as e:
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
            
            # Remove lines containing this filename (with or without [Processing])
            lines = [line for line in lines if line.strip() and 
                    not (filename in line or line.endswith(filename))]
            
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
                    # Remove [Processing] prefix
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

class ClaudeTranslator:
    """Handles translation using local Claude executable."""
    
    def __init__(self, claude_path: str = "claude"):
        self.claude_path = claude_path
        self.translation_prompt = self._build_translation_prompt()
        
    def _build_translation_prompt(self) -> str:
        """Build the translation prompt template."""
        return """{content}

Translate the above text to Vietnamese. Keep exact same structure, translate every sentence, every paragraph, every section. Do not summarize. Do not add explanations. Output only the direct translation."""
    
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
                            "configuration file",
                            "corrupted",
                            "Unexpected end of JSON input",
                            "Claude configuration file at",
                            "The corrupted file has been back"
                        ]
                        is_valid = (stdout and len(stdout.strip()) > 100 and 
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
                                    if retry_result.returncode == 0 and retry_result.stdout and len(retry_result.stdout.strip()) > 100:
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
                    
                    # Check if we're done
                    if pending == 0 and len(futures) == 0:
                        if total == 0:
                            logger.info("Queue is empty. Nothing to process.")
                        else:
                            logger.info("All files processed or currently processing.")
                        break
                    
                    # If we have pending work but no futures, something went wrong
                    if pending > 0 and len(futures) == 0:
                        logger.warning(f"No active workers but {pending} pending files. Attempting to start workers...")
                        # Try to start at least one worker before continuing
                        filename = self.queue_manager.get_next_file()
                        if filename:
                            future = executor.submit(translate_worker, (filename, self.claude_path))
                            futures[future] = filename
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
                        continue
                    
                    # Submit new jobs if we have capacity and pending files
                    while len(futures) < self.max_workers and pending > 0:
                        filename = self.queue_manager.get_next_file()
                        if filename:
                            future = executor.submit(translate_worker, (filename, self.claude_path))
                            futures[future] = filename
                            self.worker_start_times[future] = time.time()  # Track start time
                            logger.info(f"Submitted {filename} for translation")
                        else:
                            break
                    
                    # Check for long-running workers that need warmup
                    current_time = time.time()
                    long_running_futures = []
                    for future, start_time in self.worker_start_times.items():
                        if current_time - start_time > self.warmup_threshold:
                            long_running_futures.append(future)
                    
                    # If we have long-running workers and capacity, start warmup workers
                    if long_running_futures and len(futures) < self.max_workers and pending > 0:
                        logger.info(f"Found {len(long_running_futures)} workers running >5min, starting warmup workers")
                        warmup_count = min(len(long_running_futures), self.max_workers - len(futures))
                        for _ in range(warmup_count):
                            filename = self.queue_manager.get_next_file()
                            if filename:
                                future = executor.submit(translate_worker, (filename, self.claude_path))
                                futures[future] = filename
                                self.worker_start_times[future] = time.time()
                                logger.info(f"Started warmup worker for {filename}")
                            else:
                                break
                    
                    # Check completed jobs
                    completed_futures = []
                    try:
                        for future in as_completed(futures, timeout=1):
                            completed_futures.append(future)
                    except:
                        # No futures completed within timeout, continue
                        pass
                        
                    for future in completed_futures:
                        filename = futures[future]
                        try:
                            result_filename, success = future.result()
                            if success:
                                logger.info(f"Successfully completed: {result_filename}")
                                self.queue_manager.mark_completed(result_filename)
                                
                                # Start warmup worker immediately after completion if there's pending work
                                if pending > 1 and len(futures) <= self.max_workers:
                                    warmup_filename = self.queue_manager.get_next_file()
                                    if warmup_filename:
                                        warmup_future = executor.submit(translate_worker, (warmup_filename, self.claude_path))
                                        futures[warmup_future] = warmup_filename
                                        self.worker_start_times[warmup_future] = time.time()
                                        logger.info(f"Started immediate warmup worker for {warmup_filename}")
                            else:
                                logger.error(f"Failed to translate: {result_filename}")
                                # Note: We still remove failed files from queue to avoid infinite loops
                                # In production, you might want to move them to a failed queue
                                self.queue_manager.mark_completed(result_filename)
                        except Exception as e:
                            logger.error(f"Error processing result for {filename}: {e}")
                            self.queue_manager.mark_completed(filename)
                        
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
    
    # Run the translation process
    success = manager.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()