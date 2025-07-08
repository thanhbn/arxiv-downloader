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
from typing import List, Optional, Tuple, Dict, Any
import fcntl
import tempfile
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import signal
import glob
import re
from datetime import datetime
import json
import uuid
import threading

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

class ChunkStateManager:
    """Manages state and assembly of parallel chunk translations."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.translation_id = str(uuid.uuid4())[:8]
        self.state_dir = Path(f".translation_state_{self.translation_id}")
        self.state_file = self.state_dir / "chunks.json"
        self.lock = threading.Lock()
        
        # Create state directory
        self.state_dir.mkdir(exist_ok=True)
        
        # Initialize state
        self.state = {
            "file_path": str(file_path),
            "translation_id": self.translation_id,
            "total_chunks": 0,
            "completed_chunks": 0,
            "failed_chunks": [],
            "chunks": {},  # chunk_id -> {status, file, order, size, timestamp}
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self._save_state()
    
    def register_chunks(self, chunks: List[str]) -> List[str]:
        """Register chunks and return chunk IDs for processing."""
        with self.lock:
            chunk_ids = []
            self.state["total_chunks"] = len(chunks)
            
            for i, chunk_content in enumerate(chunks):
                chunk_id = f"chunk_{i+1:03d}"
                chunk_file = self.state_dir / f"{chunk_id}.txt"
                
                # Save chunk content to file
                chunk_file.write_text(chunk_content, encoding='utf-8')
                
                # Register in state
                self.state["chunks"][chunk_id] = {
                    "status": "pending",
                    "order": i + 1,
                    "content_file": str(chunk_file),
                    "translation_file": str(self.state_dir / f"{chunk_id}_translation.txt"),
                    "size": len(chunk_content),
                    "created_at": datetime.now().isoformat()
                }
                chunk_ids.append(chunk_id)
            
            self._save_state()
            return chunk_ids
    
    def start_chunk(self, chunk_id: str) -> Optional[str]:
        """Mark chunk as processing and return content."""
        with self.lock:
            if chunk_id not in self.state["chunks"]:
                return None
            
            chunk_info = self.state["chunks"][chunk_id]
            if chunk_info["status"] != "pending":
                return None
            
            chunk_info["status"] = "processing"
            chunk_info["started_at"] = datetime.now().isoformat()
            self._save_state()
            
            # Return chunk content
            content_file = Path(chunk_info["content_file"])
            if content_file.exists():
                return content_file.read_text(encoding='utf-8')
            return None
    
    def complete_chunk(self, chunk_id: str, translation: str) -> bool:
        """Mark chunk as completed and save translation."""
        with self.lock:
            if chunk_id not in self.state["chunks"]:
                return False
            
            chunk_info = self.state["chunks"][chunk_id]
            if chunk_info["status"] != "processing":
                return False
            
            # Save translation
            translation_file = Path(chunk_info["translation_file"])
            translation_file.write_text(translation, encoding='utf-8')
            
            # Update state
            chunk_info["status"] = "completed"
            chunk_info["completed_at"] = datetime.now().isoformat()
            chunk_info["translation_size"] = len(translation)
            
            self.state["completed_chunks"] += 1
            self._save_state()
            return True
    
    def fail_chunk(self, chunk_id: str, error: str) -> bool:
        """Mark chunk as failed."""
        with self.lock:
            if chunk_id not in self.state["chunks"]:
                return False
            
            chunk_info = self.state["chunks"][chunk_id]
            chunk_info["status"] = "failed"
            chunk_info["failed_at"] = datetime.now().isoformat()
            chunk_info["error"] = error
            
            if chunk_id not in self.state["failed_chunks"]:
                self.state["failed_chunks"].append(chunk_id)
            
            self._save_state()
            return True
    
    def get_assembly_order(self) -> List[Tuple[str, str]]:
        """Get chunks in correct order for assembly. Returns [(chunk_id, status), ...]"""
        with self.lock:
            chunks_by_order = sorted(
                self.state["chunks"].items(),
                key=lambda x: x[1]["order"]
            )
            return [(chunk_id, info["status"]) for chunk_id, info in chunks_by_order]
    
    def assemble_translation(self) -> Tuple[str, List[str]]:
        """Assemble final translation from completed chunks."""
        with self.lock:
            translation_parts = []
            failed_chunks = []
            
            # Get chunks in order
            chunks_by_order = sorted(
                self.state["chunks"].items(),
                key=lambda x: x[1]["order"]
            )
            
            for chunk_id, chunk_info in chunks_by_order:
                if chunk_info["status"] == "completed":
                    translation_file = Path(chunk_info["translation_file"])
                    if translation_file.exists():
                        translation = translation_file.read_text(encoding='utf-8')
                        translation_parts.append(translation)
                    else:
                        failed_chunks.append(chunk_id)
                        translation_parts.append(f"[MISSING TRANSLATION FOR CHUNK {chunk_id}]")
                elif chunk_info["status"] == "failed":
                    failed_chunks.append(chunk_id)
                    translation_parts.append(f"[TRANSLATION FAILED FOR CHUNK {chunk_id}]")
                else:
                    # Still pending or processing
                    failed_chunks.append(chunk_id)
                    translation_parts.append(f"[INCOMPLETE TRANSLATION FOR CHUNK {chunk_id}]")
            
            return "\n\n".join(translation_parts), failed_chunks
    
    def get_status(self) -> Dict[str, Any]:
        """Get current translation status."""
        with self.lock:
            pending = sum(1 for info in self.state["chunks"].values() if info["status"] == "pending")
            processing = sum(1 for info in self.state["chunks"].values() if info["status"] == "processing")
            completed = sum(1 for info in self.state["chunks"].values() if info["status"] == "completed")
            failed = sum(1 for info in self.state["chunks"].values() if info["status"] == "failed")
            
            return {
                "total_chunks": self.state["total_chunks"],
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "success_rate": (completed / self.state["total_chunks"] * 100) if self.state["total_chunks"] > 0 else 0
            }
    
    def cleanup(self):
        """Clean up temporary state files."""
        try:
            if self.state_dir.exists():
                shutil.rmtree(self.state_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup state directory {self.state_dir}: {e}")
    
    def _save_state(self):
        """Save current state to JSON file."""
        self.state["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

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
            
    def is_all_processing_state(self) -> bool:
        """Check if queue has no pending items but has processing items (indicating potential stale entries)."""
        if not self._acquire_lock():
            return False
            
        try:
            total, processing, pending = self.get_queue_status()
            return pending == 0 and processing > 0
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
        self.chunk_translation_prompt = self._build_chunk_translation_prompt()
        self.emergency_chunk_prompt = self._build_emergency_chunk_prompt()
        
        # Token-aware chunking thresholds
        # Claude Sonnet 4: 200K tokens total (input + output combined)
        self.claude_max_tokens = 200000
        self.claude_max_output_tokens = 64000  # Claude Sonnet 4 output limit
        self.chars_per_token = 0.75  # Conservative estimate for English text
        
        # Vietnamese translation characteristics (based on analysis)
        self.vietnamese_expansion_ratio = 1.3  # Conservative estimate (1.3x expansion)
        self.vietnamese_chars_per_token = 0.6  # Vietnamese text is more token-dense
        
        # Calculate safe input limits accounting for output tokens
        # Total budget: 200K tokens
        # Reserve tokens for output: estimated_input_tokens * expansion_ratio / chars_per_token
        self.output_token_overhead_ratio = 1.5  # Conservative multiplier for output tokens
        self.max_safe_input_tokens = int(self.claude_max_tokens * 0.6)  # Use 60% for input, 40% for output
        self.max_input_chars = int(self.max_safe_input_tokens * self.chars_per_token)  # ~90K chars safe limit
        
        # Chunking configuration (accounting for input + output tokens)
        self.max_chars_per_chunk = 25000  # Reduced from 40KB to account for output tokens
        self.large_file_threshold = 40000  # Reduced threshold for safety
        self.emergency_chunk_size = int(self.max_input_chars * 0.4)  # Even more conservative for emergency mode
        
        # Enhanced boundary handling
        self.sentence_overlap_count = 2  # Number of sentences to overlap between chunks
        self.context_window_sentences = 3  # Additional sentences for context
        self.min_chunk_sentences = 5  # Minimum sentences per chunk
        
        # Safety margins
        self.prompt_overhead = 500  # Estimated chars for prompt template
        self.safety_margin = 0.9  # Use 90% of available space
        
        # Debug info
        logger.info(f"Token-aware chunking initialized:")
        logger.info(f"  Max safe input chars: {self.max_input_chars:,}")
        logger.info(f"  Standard chunk size: {self.max_chars_per_chunk:,} chars")
        logger.info(f"  Emergency chunk size: {self.emergency_chunk_size:,} chars")
        logger.info(f"  Vietnamese expansion ratio: {self.vietnamese_expansion_ratio}x")
        
    def _build_translation_prompt(self) -> str:
        """Build the translation prompt template."""
        return """Translate this text to Vietnamese. Output ONLY the translation, no explanations, no summaries, no meta-commentary:

{content}

IMPORTANT: Output only the Vietnamese translation. Do not explain what you did. Do not summarize. Start with the first Vietnamese sentence immediately."""
    
    def _build_chunk_translation_prompt(self) -> str:
        """Build the translation prompt template for file chunks."""
        return """Translate this chunk of text to Vietnamese. This is part {chunk_num} of {total_chunks} from a larger document.

{content}

IMPORTANT INSTRUCTIONS:
- If you see [CONTEXT from previous chunk - for reference only], use this for understanding but DO NOT translate it
- Only translate the content under [NEW CONTENT to translate] section
- If there are no context markers, translate the entire content
- Output only the Vietnamese translation of the NEW content
- Maintain terminology consistency with any context provided
- Preserve original structure and formatting
- Start immediately with the Vietnamese translation"""
    
    def _build_emergency_chunk_prompt(self) -> str:
        """Build a minimal prompt for emergency ultra-small chunks."""
        return """Translate to Vietnamese:

{content}

Vietnamese:"""
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (conservative)."""
        return int(len(text) / self.chars_per_token)
    
    def _is_chunk_safe_for_context(self, chunk: str, prompt_template: str) -> bool:
        """Check if chunk + prompt + expected output will fit within Claude's context limit."""
        # Estimate input tokens (prompt + content)
        full_prompt = prompt_template.format(content=chunk, chunk_num=1, total_chunks=1)
        input_tokens = self._estimate_tokens(full_prompt)
        
        # Estimate output tokens (Vietnamese translation)
        vietnamese_content_chars = len(chunk) * self.vietnamese_expansion_ratio
        output_tokens = int(vietnamese_content_chars / self.vietnamese_chars_per_token)
        
        # Total token usage
        total_tokens = input_tokens + output_tokens
        
        # Safety check: must be under 90% of Claude's total limit
        return total_tokens < (self.claude_max_tokens * 0.9)
    
    def _detect_sentences(self, text: str) -> List[str]:
        """Detect sentence boundaries in text with academic paper awareness."""
        import re
        
        # Simple but effective sentence detection for academic papers
        # Replace problematic patterns first
        text = re.sub(r'\bet al\.', 'et al', text)  # Handle et al.
        text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Fig|Table|Eq|Ref|vs|i\.e|e\.g|etc|cf|pp|vol|no|sec|ch|dept|univ|inst|corp|inc|ltd)\.', r'\1', text)
        
        # Split on sentence endings followed by whitespace and capital letter
        sentence_pattern = r'[.!?]+\s+(?=[A-Z])'
        
        # Split text into sentences
        sentences = re.split(sentence_pattern, text)
        
        # Clean up and reassemble sentences
        cleaned_sentences = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                # Add period if missing and not the last sentence
                if i < len(sentences) - 1 and not sentence.endswith(('.', '!', '?')):
                    sentence += '.'
                cleaned_sentences.append(sentence)
        
        # Filter out very short "sentences" that are likely fragments
        final_sentences = []
        for sentence in cleaned_sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Minimum sentence length
                # Restore abbreviations
                sentence = re.sub(r'\bet al\b', 'et al.', sentence)
                sentence = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Fig|Table|Eq|Ref|vs|i\.e|e\.g|etc|cf|pp|vol|no|sec|ch|dept|univ|inst|corp|inc|ltd)\b', r'\1.', sentence)
                final_sentences.append(sentence)
        
        return final_sentences
    
    def _find_optimal_chunk_boundary(self, sentences: List[str], target_size: int, start_idx: int) -> int:
        """Find the best place to end a chunk, prioritizing sentence boundaries."""
        current_size = 0
        best_boundary = start_idx
        
        for i in range(start_idx, len(sentences)):
            sentence_size = len(sentences[i]) + 1  # +1 for space/newline
            
            if current_size + sentence_size > target_size:
                # If we haven't included minimum sentences, continue
                if i - start_idx < self.min_chunk_sentences and i < len(sentences) - 1:
                    current_size += sentence_size
                    continue
                else:
                    break
            
            current_size += sentence_size
            best_boundary = i + 1  # +1 because we want to include this sentence
        
        return min(best_boundary, len(sentences))
    
    def _split_content_into_chunks(self, content: str, emergency_mode: bool = False) -> List[str]:
        """Split content into manageable chunks with sentence-aware boundaries and context preservation."""
        # First try sentence-aware chunking
        try:
            return self._split_by_sentences(content, emergency_mode)
        except Exception as e:
            # Fallback to line-based chunking if sentence detection fails
            logger.warning(f"Sentence-aware chunking failed, falling back to line-based: {e}")
            return self._split_by_lines_fallback(content, emergency_mode)
    
    def _split_by_sentences(self, content: str, emergency_mode: bool = False) -> List[str]:
        """Split content by sentences with proper context preservation."""
        sentences = self._detect_sentences(content)
        
        if len(sentences) < self.min_chunk_sentences:
            # Content too short for sentence-based chunking
            return [content]
        
        chunks = []
        target_chunk_size = self.emergency_chunk_size if emergency_mode else self.max_chars_per_chunk
        
        i = 0
        while i < len(sentences):
            # Find optimal boundary for this chunk
            end_idx = self._find_optimal_chunk_boundary(sentences, target_chunk_size, i)
            
            # Add context from previous chunk (except for first chunk)
            if i > 0 and not emergency_mode:
                # Include some sentences from previous chunk for context
                context_start = max(0, i - self.context_window_sentences)
                chunk_sentences = sentences[context_start:end_idx]
                
                # Mark context vs new content for translation
                context_marker = f"[CONTEXT from previous chunk - for reference only]\n"
                context_part = " ".join(sentences[context_start:i])
                new_content_marker = f"\n[NEW CONTENT to translate]\n"
                new_part = " ".join(sentences[i:end_idx])
                
                chunk_text = context_marker + context_part + new_content_marker + new_part
            else:
                # First chunk or emergency mode - no context needed
                chunk_text = " ".join(sentences[i:end_idx])
            
            # Verify chunk safety
            prompt_template = self.emergency_chunk_prompt if emergency_mode else self.chunk_translation_prompt
            if not self._is_chunk_safe_for_context(chunk_text, prompt_template):
                if emergency_mode:
                    # Ultra-emergency: force smaller chunks
                    mini_chunk_size = max(1, (end_idx - i) // 2)
                    end_idx = i + mini_chunk_size
                    chunk_text = " ".join(sentences[i:end_idx])
                else:
                    # Fall back to emergency mode
                    emergency_chunks = self._split_by_sentences(chunk_text, emergency_mode=True)
                    chunks.extend(emergency_chunks)
                    i = end_idx
                    continue
            
            chunks.append(chunk_text)
            
            # Move to next chunk with overlap
            if not emergency_mode:
                # Overlap by moving back slightly
                i = max(i + 1, end_idx - self.sentence_overlap_count)
            else:
                i = end_idx
        
        return chunks
    
    def _split_by_lines_fallback(self, content: str, emergency_mode: bool = False) -> List[str]:
        """Fallback line-based chunking when sentence detection fails."""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        target_chunk_size = self.emergency_chunk_size if emergency_mode else self.max_chars_per_chunk
        
        for line in lines:
            line_size = len(line) + 1
            
            if current_size + line_size > target_chunk_size and current_chunk:
                chunk_text = '\n'.join(current_chunk)
                chunks.append(chunk_text)
                
                # Simple overlap for fallback mode
                if not emergency_mode and len(current_chunk) > 3:
                    current_chunk = current_chunk[-2:]  # Keep last 2 lines
                    current_size = sum(len(l) + 1 for l in current_chunk)
                else:
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(line)
            current_size += line_size
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _split_oversized_chunk(self, chunk: str) -> List[str]:
        """Ultra-aggressive splitting for chunks that exceed even emergency limits."""
        # Split by sentences first
        sentences = chunk.replace('.', '.\n').replace('!', '!\n').replace('?', '?\n').split('\n')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        mini_chunks = []
        current_mini = []
        current_size = 0
        max_mini_size = int(self.emergency_chunk_size * 0.5)  # Even smaller chunks
        
        for sentence in sentences:
            sentence_size = len(sentence) + 1
            
            if current_size + sentence_size > max_mini_size and current_mini:
                mini_chunks.append('\n'.join(current_mini))
                current_mini = []
                current_size = 0
            
            current_mini.append(sentence)
            current_size += sentence_size
        
        if current_mini:
            mini_chunks.append('\n'.join(current_mini))
        
        return mini_chunks
    
    def _is_large_file(self, content: str) -> bool:
        """Check if file is too large for single translation."""
        return len(content) > self.large_file_threshold
    
    def _translate_chunk(self, chunk: str, chunk_num: int, total_chunks: int, worker_logger, emergency_mode: bool = False) -> str:
        """Translate a single chunk of content."""
        # Choose appropriate prompt based on mode
        if emergency_mode:
            prompt = self.emergency_chunk_prompt.format(content=chunk)
            worker_logger.warning(f"Using emergency mode for chunk {chunk_num}/{total_chunks}")
        else:
            prompt = self.chunk_translation_prompt.format(
                content=chunk,
                chunk_num=chunk_num,
                total_chunks=total_chunks
            )
        
        # Final safety check (input + expected output)
        input_tokens = self._estimate_tokens(prompt)
        vietnamese_chars = len(chunk) * self.vietnamese_expansion_ratio
        output_tokens = int(vietnamese_chars / self.vietnamese_chars_per_token)
        total_tokens = input_tokens + output_tokens
        
        if total_tokens > self.claude_max_tokens * 0.95:
            worker_logger.error(f"Chunk {chunk_num}/{total_chunks} still too large: {input_tokens} input + {output_tokens} output = {total_tokens} total tokens")
            return None
        
        worker_logger.debug(f"Chunk {chunk_num}/{total_chunks} token usage: {input_tokens} input + {output_tokens} output = {total_tokens} total")
        
        cmd = [
            self.claude_path,
            "--print", 
            "--dangerously-skip-permissions",
            "--model", "sonnet"
        ]
        
        worker_logger.info(f"Translating chunk {chunk_num}/{total_chunks} ({len(chunk)} chars)")
        
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=900  # 15 minutes per chunk
            )
            
            if result.returncode == 0 and result.stdout:
                # Validate chunk translation
                stdout = result.stdout.strip()
                invalid_indicators = [
                    "Execution error", "configuration file", "corrupted",
                    "Unexpected end of JSON input", "Claude configuration file"
                ]
                
                if stdout and len(stdout) > 20 and not any(indicator in stdout for indicator in invalid_indicators):
                    worker_logger.info(f"Chunk {chunk_num}/{total_chunks} translated successfully ({len(stdout)} chars)")
                    return stdout
                else:
                    worker_logger.error(f"Invalid chunk translation: {stdout[:100]}...")
                    return None
            else:
                worker_logger.error(f"Chunk translation failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            worker_logger.error(f"Chunk {chunk_num}/{total_chunks} translation timeout")
            return None
        except Exception as e:
            worker_logger.error(f"Error translating chunk {chunk_num}/{total_chunks}: {e}")
            return None
    
    def _translate_large_file(self, input_path: Path, output_path: Path, content: str, worker_logger) -> bool:
        """Translate a large file using parallel chunk processing with state management."""
        estimated_tokens = self._estimate_tokens(content)
        worker_logger.info(f"File size: {len(content)} chars, estimated {estimated_tokens} tokens")
        
        # Choose chunking strategy based on file size
        if estimated_tokens > self.claude_max_tokens * 5:
            worker_logger.warning("Extremely large file detected. Using emergency chunking mode.")
            chunks = self._split_content_into_chunks(content, emergency_mode=True)
            emergency_mode = True
        else:
            chunks = self._split_content_into_chunks(content, emergency_mode=False)
            emergency_mode = False
        
        total_chunks = len(chunks)
        worker_logger.info(f"Split large file into {total_chunks} chunks (emergency_mode={emergency_mode})")
        
        # Initialize chunk state manager
        chunk_manager = ChunkStateManager(str(input_path))
        
        try:
            # Register all chunks
            chunk_ids = chunk_manager.register_chunks(chunks)
            worker_logger.info(f"Registered {len(chunk_ids)} chunks for parallel processing")
            
            # Process chunks in parallel using ProcessPoolExecutor
            max_chunk_workers = min(4, total_chunks)  # Limit concurrent chunks to avoid overwhelming Claude
            worker_logger.info(f"Using {max_chunk_workers} parallel chunk workers")
            
            with ProcessPoolExecutor(max_workers=max_chunk_workers) as executor:
                # Submit all chunks for processing
                chunk_futures = {}
                for chunk_id in chunk_ids:
                    future = executor.submit(
                        chunk_worker, 
                        (chunk_id, str(chunk_manager.state_dir), self.claude_path, 
                         self.max_chars_per_chunk, self.large_file_threshold)
                    )
                    chunk_futures[future] = chunk_id
                
                # Process completed chunks as they finish
                completed_count = 0
                for future in as_completed(chunk_futures):
                    chunk_id = chunk_futures[future]
                    try:
                        chunk_id_result, success, result_or_error = future.result()
                        
                        if success:
                            chunk_manager.complete_chunk(chunk_id_result, result_or_error)
                            completed_count += 1
                            worker_logger.info(f"Chunk {chunk_id_result} completed ({completed_count}/{total_chunks})")
                        else:
                            chunk_manager.fail_chunk(chunk_id_result, result_or_error)
                            worker_logger.error(f"Chunk {chunk_id_result} failed: {result_or_error}")
                            
                    except Exception as e:
                        chunk_manager.fail_chunk(chunk_id, f"Future exception: {e}")
                        worker_logger.error(f"Exception processing chunk {chunk_id}: {e}")
                    
                    # Report progress
                    status = chunk_manager.get_status()
                    if status["completed"] % 5 == 0 or status["completed"] == total_chunks:
                        worker_logger.info(f"Progress: {status['completed']}/{total_chunks} completed, "
                                         f"{status['failed']} failed ({status['success_rate']:.1f}% success)")
            
            # Assemble final translation
            worker_logger.info("Assembling final translation from completed chunks...")
            full_translation, failed_chunk_ids = chunk_manager.assemble_translation()
            
            # Save the complete translation
            output_path.write_text(full_translation, encoding='utf-8')
            
            # Report final status
            final_status = chunk_manager.get_status()
            worker_logger.info(f"Parallel chunk translation completed: {len(full_translation)} chars "
                             f"across {total_chunks} chunks ({final_status['success_rate']:.1f}% success)")
            
            if failed_chunk_ids:
                worker_logger.warning(f"Translation completed with {len(failed_chunk_ids)} failed chunks: {failed_chunk_ids}")
                worker_logger.warning("Check output for [TRANSLATION FAILED] markers")
            else:
                worker_logger.info(f"Successfully completed parallel translation of {input_path}")
            
            return len(failed_chunk_ids) == 0
            
        except Exception as e:
            worker_logger.error(f"Error in parallel chunk processing: {e}")
            return False
        finally:
            # Clean up state files
            chunk_manager.cleanup()
    
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
            
            # Check if file is too large for single translation
            if self._is_large_file(content):
                worker_logger.info(f"Large file detected ({len(content)} chars). Using chunked translation.")
                return self._translate_large_file(input_path, output_path, content, worker_logger)
            
            # Standard single-file translation for smaller files
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

def chunk_worker(args: Tuple[str, str, str, int, int]) -> Tuple[str, bool, str]:
    """Worker function for processing individual chunks with state management."""
    chunk_id, state_dir, claude_path, chunk_size, large_file_threshold = args
    worker_pid = os.getpid()
    
    # Set up worker-specific logger
    worker_logger = logging.getLogger(f"chunk_worker_{worker_pid}")
    worker_logger.setLevel(logging.INFO)
    
    if not worker_logger.handlers:
        worker_handler = logging.StreamHandler()
        worker_formatter = logging.Formatter(
            f'%(asctime)s - CHUNK-WORKER-{worker_pid} - %(levelname)s - %(message)s'
        )
        worker_handler.setFormatter(worker_formatter)
        worker_logger.addHandler(worker_handler)
        worker_logger.propagate = False
    
    worker_logger.info(f"Starting chunk worker for {chunk_id}")
    
    try:
        # Load state and get chunk content
        state_file = Path(state_dir) / "chunks.json"
        if not state_file.exists():
            return (chunk_id, False, "State file not found")
        
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        if chunk_id not in state["chunks"]:
            return (chunk_id, False, "Chunk not found in state")
        
        chunk_info = state["chunks"][chunk_id]
        content_file = Path(chunk_info["content_file"])
        
        if not content_file.exists():
            return (chunk_id, False, "Chunk content file not found")
        
        # Read chunk content
        chunk_content = content_file.read_text(encoding='utf-8')
        worker_logger.info(f"Processing chunk {chunk_id}: {len(chunk_content)} chars")
        
        # Set up translator
        translator = ClaudeTranslator(claude_path)
        translator.max_chars_per_chunk = chunk_size
        translator.large_file_threshold = large_file_threshold
        
        # Translate the chunk
        # Extract chunk number from chunk_id for display
        chunk_num = int(chunk_id.split('_')[-1])
        total_chunks = state["total_chunks"]
        
        translation = translator._translate_chunk(
            chunk_content, 
            chunk_num, 
            total_chunks, 
            worker_logger, 
            emergency_mode=False
        )
        
        if translation:
            # Save translation directly to state managed file
            translation_file = Path(chunk_info["translation_file"])
            translation_file.write_text(translation, encoding='utf-8')
            
            worker_logger.info(f"Successfully translated chunk {chunk_id} ({len(translation)} chars)")
            return (chunk_id, True, translation)
        else:
            worker_logger.error(f"Failed to translate chunk {chunk_id}")
            return (chunk_id, False, "Translation failed")
            
    except Exception as e:
        worker_logger.error(f"Chunk worker error for {chunk_id}: {e}")
        import traceback
        worker_logger.error(f"Traceback: {traceback.format_exc()}")
        return (chunk_id, False, str(e))

def translate_worker(args: Tuple[str, str, int, int]) -> Tuple[str, bool]:
    """Worker function for multiprocessing translation."""
    filename, claude_path, chunk_size, large_file_threshold = args
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
        # Configure chunking parameters
        translator.max_chars_per_chunk = chunk_size
        translator.large_file_threshold = large_file_threshold
        worker_logger.info(f"Translator initialized for {filename} (chunk_size={chunk_size}, threshold={large_file_threshold})")
        
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

def idle_worker(args: Tuple[str, str, int, int]) -> Tuple[Optional[str], bool]:
    """Idle worker function that polls for new files and processes them."""
    queue_file, claude_path, chunk_size, large_file_threshold = args
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
        # Configure chunking parameters
        translator.max_chars_per_chunk = chunk_size
        translator.large_file_threshold = large_file_threshold
        
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
                 claude_path: str = "claude", max_workers: int = 6,
                 chunk_size: int = 40000, large_file_threshold: int = 60000):
        self.queue_manager = TranslationQueueManager(queue_file)
        self.claude_path = claude_path
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.large_file_threshold = large_file_threshold
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
                    
                    # Check for stale processing state (pending=0, processing>0, no active workers)
                    if pending == 0 and processing > 0 and len(futures) == 0:
                        logger.warning(f"Detected all-processing state: 0 pending, {processing} processing, 0 active workers")
                        logger.info("Cleaning stale processing entries...")
                        stale_cleaned = self.queue_manager.clean_stale_processing()
                        if stale_cleaned > 0:
                            logger.info(f"Cleaned {stale_cleaned} stale processing entries")
                            # Refresh queue status after cleaning
                            total, processing, pending = self.queue_manager.get_queue_status()
                            logger.info(f"Updated queue status - Total: {total}, Processing: {processing}, Pending: {pending}")
                        else:
                            logger.warning("No stale entries found, but all items are still processing - may indicate a system issue")
                        continue
                    
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
                            future = executor.submit(translate_worker, (filename, self.claude_path, self.chunk_size, self.large_file_threshold))
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
                                future = executor.submit(translate_worker, (filename, self.claude_path, self.chunk_size, self.large_file_threshold))
                                futures[future] = ('file', filename)  # Mark as file worker
                                self.worker_start_times[future] = time.time()
                                logger.info(f"Submitted {filename} for translation")
                                continue
                        
                        # No pending files, but we have worker capacity - start idle worker
                        future = executor.submit(idle_worker, (str(self.queue_manager.queue_file), self.claude_path, self.chunk_size, self.large_file_threshold))
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
    parser.add_argument("--chunk-size", type=int, default=40000,
                       help="Maximum characters per chunk for large files (default: 40000)")
    parser.add_argument("--large-file-threshold", type=int, default=60000,
                       help="File size threshold in characters for chunking (default: 60000)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate workers count
    if args.workers < 1 or args.workers > 16:
        logger.error("Number of workers must be between 1 and 16")
        sys.exit(1)
    
    # Create translation manager with chunking configuration
    manager = TranslationManager(
        queue_file=args.queue_file,
        claude_path=args.claude_path,
        max_workers=args.workers,
        chunk_size=args.chunk_size,
        large_file_threshold=args.large_file_threshold
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