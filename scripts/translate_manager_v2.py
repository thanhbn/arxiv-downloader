#!/usr/bin/env python3
"""
Automated Paper Translation Manager v2 with Chunking Support

This version adds intelligent chunking for large files to prevent timeout errors.
Large files are automatically split into manageable chunks, translated separately,
and then merged back together.

Key improvements over v1:
- Automatic chunking for files > 40KB or ~12,000 tokens
- Smart splitting by sections/paragraphs to preserve context
- Per-chunk timeout (10 min) vs per-file timeout (30 min)
- Progress tracking for chunked translations
- Graceful handling of partial translations

Usage:
    python translate_manager_v2.py [--workers N] [--claude-path PATH] [--queue-file FILE]

Example:
    python translate_manager_v2.py --workers 4 --claude-path /usr/local/bin/claude
"""

import os
import sys
import argparse
import subprocess
import multiprocessing
import time
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import fcntl
import tempfile
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import signal
import glob
import re
from datetime import datetime
import json

# ============================================================================
# CHUNKING CONFIGURATION
# ============================================================================
# Thresholds for chunking large files
CHUNK_SIZE_THRESHOLD = 40000  # Characters - files larger than this will be chunked
CHUNK_TOKEN_THRESHOLD = 12000  # Approximate tokens (chars / 3.5)
MAX_CHUNK_SIZE = 35000  # Maximum characters per chunk
MIN_CHUNK_SIZE = 5000   # Minimum characters per chunk (avoid too small chunks)
CHUNK_TIMEOUT = 600     # 10 minutes timeout per chunk (vs 30 min for full file)
FULL_FILE_TIMEOUT = 1800  # 30 minutes for non-chunked files

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


# ============================================================================
# CHUNKING UTILITIES
# ============================================================================

def estimate_tokens(text: str) -> int:
    """Estimate token count from text. Roughly 1 token per 3.5 characters for English."""
    return int(len(text) / 3.5)


def should_chunk_file(content: str) -> bool:
    """Determine if a file should be chunked based on size."""
    char_count = len(content)
    token_estimate = estimate_tokens(content)

    return char_count > CHUNK_SIZE_THRESHOLD or token_estimate > CHUNK_TOKEN_THRESHOLD


def find_section_boundaries(content: str) -> List[int]:
    """Find natural section boundaries in academic papers.

    Looks for:
    - Section headers (1. Introduction, 2. Methods, etc.)
    - Page markers (--- Page X ---)
    - Double newlines (paragraph breaks)
    - Figure/Table captions
    """
    boundaries = [0]  # Start of document

    # Pattern for section headers
    section_patterns = [
        r'\n\d+\.\s+[A-Z][A-Za-z\s]+\n',  # 1. Introduction
        r'\n[A-Z][A-Z\s]+\n',  # INTRODUCTION (all caps)
        r'\n#{1,3}\s+',  # Markdown headers
        r'\n-{3,}\s*Page\s*\d+\s*-{3,}',  # Page markers
        r'\n\n\n+',  # Multiple newlines
    ]

    for pattern in section_patterns:
        for match in re.finditer(pattern, content):
            boundaries.append(match.start())

    # Sort and deduplicate
    boundaries = sorted(set(boundaries))

    return boundaries


def split_into_chunks(content: str, max_chunk_size: int = MAX_CHUNK_SIZE) -> List[Dict]:
    """Split content into chunks at natural boundaries.

    Returns list of dicts with:
    - 'text': chunk content
    - 'start': start position in original
    - 'end': end position in original
    - 'chunk_num': chunk number (1-indexed)
    """
    if len(content) <= max_chunk_size:
        return [{
            'text': content,
            'start': 0,
            'end': len(content),
            'chunk_num': 1,
            'total_chunks': 1
        }]

    boundaries = find_section_boundaries(content)
    chunks = []
    current_pos = 0
    chunk_num = 1

    while current_pos < len(content):
        # Find the best boundary within max_chunk_size
        chunk_end = min(current_pos + max_chunk_size, len(content))

        # Look for a natural boundary before chunk_end
        best_boundary = chunk_end
        for boundary in reversed(boundaries):
            if current_pos < boundary <= chunk_end:
                # Ensure minimum chunk size
                if boundary - current_pos >= MIN_CHUNK_SIZE:
                    best_boundary = boundary
                    break

        # If no good boundary found and we're not at the end, try paragraph breaks
        if best_boundary == chunk_end and chunk_end < len(content):
            # Look for double newline
            last_para = content.rfind('\n\n', current_pos, chunk_end)
            if last_para > current_pos + MIN_CHUNK_SIZE:
                best_boundary = last_para + 2  # Include the newlines

        chunk_text = content[current_pos:best_boundary].strip()

        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                'text': chunk_text,
                'start': current_pos,
                'end': best_boundary,
                'chunk_num': chunk_num
            })
            chunk_num += 1

        current_pos = best_boundary

    # Update total_chunks for all
    total = len(chunks)
    for chunk in chunks:
        chunk['total_chunks'] = total

    return chunks


def merge_translated_chunks(chunks: List[Dict], translations: Dict[int, str]) -> str:
    """Merge translated chunks back into a single document.

    Args:
        chunks: Original chunk info from split_into_chunks
        translations: Dict mapping chunk_num to translated text

    Returns:
        Merged translation text
    """
    merged_parts = []

    for chunk in sorted(chunks, key=lambda x: x['chunk_num']):
        chunk_num = chunk['chunk_num']
        if chunk_num in translations and translations[chunk_num]:
            # Add separator comment for debugging (optional)
            if len(chunks) > 1:
                merged_parts.append(f"\n\n--- [Phan {chunk_num}/{chunk['total_chunks']}] ---\n\n")
            merged_parts.append(translations[chunk_num])
        else:
            # Chunk translation failed - mark it
            merged_parts.append(f"\n\n[CHUA DICH - Phan {chunk_num}/{chunk['total_chunks']}]\n\n")

    return ''.join(merged_parts)


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
    """Handles translation using local Claude executable with chunking support."""

    def __init__(self, claude_path: str = "/home/ngocthanh/.nvm/versions/node/v24.11.0/bin/claude", worker_id: Optional[int] = None):
        self.claude_path = claude_path
        self.worker_id = worker_id or os.getpid()
        self.translation_prompt = self._build_translation_prompt()
        self.chunk_prompt = self._build_chunk_prompt()
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
        """Build the translation prompt template for full files."""
        return """Translate this text to Vietnamese. Output ONLY the translation, no explanations, no summaries, no meta-commentary:

{content}

IMPORTANT: Output only the Vietnamese translation. Do not explain what you did. Do not summarize. Start with the first Vietnamese sentence immediately."""

    def _build_chunk_prompt(self) -> str:
        """Build the translation prompt template for chunks."""
        return """Translate this text to Vietnamese. This is part {chunk_num} of {total_chunks} of a larger document.

Output ONLY the translation, no explanations, no summaries, no meta-commentary:

{content}

IMPORTANT:
- Output only the Vietnamese translation
- Do not explain what you did
- Do not summarize
- Do not add headers like "Part X translation"
- Start with the first Vietnamese sentence immediately"""

    def _sanitize_content(self, content: str) -> str:
        """Sanitize content to prevent prompt injection and parsing errors."""
        # Remove null bytes and normalize line endings
        content = content.replace('\x00', '').replace('\r', '\n')

        # Replace problematic Unicode characters that may break prompts
        unicode_replacements = {
            # Mathematical symbols
            'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
            'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
            'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
            'ν': 'nu', 'ξ': 'xi', 'ο': 'omicron', 'π': 'pi',
            'ρ': 'rho', 'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon',
            'φ': 'phi', 'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',

            # Punctuation and symbols
            '–': '-', '—': '-', ''': "'", ''': "'",
            '"': '"', '"': '"', '…': '...', '∗': '*',
            '≥': '>=', '≤': '<=', '≠': '!=', '≈': '~=',
            '∈': 'in', '∉': 'not in', '∀': 'for all',
            '∃': 'exists', '∅': 'empty set', '∪': 'union',
            '∩': 'intersection', '⊂': 'subset', '⊃': 'superset',
        }

        # Apply replacements
        for unicode_char, replacement in unicode_replacements.items():
            content = content.replace(unicode_char, replacement)

        # Remove or replace other problematic characters that could break prompts
        # Replace control characters (except \n and \t)
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)

        # Escape potential prompt injection patterns
        content = content.replace('```', '`‌`‌`')  # Insert zero-width non-joiner
        content = content.replace('IMPORTANT:', 'Important:')
        content = content.replace('SYSTEM:', 'System:')
        content = content.replace('USER:', 'User:')
        content = content.replace('ASSISTANT:', 'Assistant:')

        return content

    def _translate_single_chunk(self, chunk: Dict, worker_logger) -> Tuple[bool, str]:
        """Translate a single chunk of text.

        Returns:
            tuple: (success, translated_text or error_message)
        """
        chunk_num = chunk['chunk_num']
        total_chunks = chunk['total_chunks']
        content = chunk['text']

        worker_logger.info(f"Translating chunk {chunk_num}/{total_chunks} ({len(content)} chars)")

        # Build prompt for this chunk
        if total_chunks > 1:
            full_prompt = self.chunk_prompt.format(
                content=content,
                chunk_num=chunk_num,
                total_chunks=total_chunks
            )
        else:
            full_prompt = self.translation_prompt.format(content=content)

        # Create temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(full_prompt)
            temp_prompt_path = temp_file.name

        try:
            cmd = [
                self.claude_path,
                "--print",
                "--dangerously-skip-permissions",
                "--model", "sonnet"
            ]

            env = os.environ.copy()

            # Use chunk timeout for chunks, full timeout for single chunks
            timeout = CHUNK_TIMEOUT if total_chunks > 1 else FULL_FILE_TIMEOUT

            # Acquire auth lock
            max_auth_retries = 10
            auth_retry_count = 0

            while auth_retry_count < max_auth_retries:
                if self._acquire_auth_lock():
                    break
                auth_retry_count += 1
                if auth_retry_count < max_auth_retries:
                    backoff_time = min(2 ** auth_retry_count, 30)
                    worker_logger.warning(f"Failed to acquire auth lock (attempt {auth_retry_count}), retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                else:
                    return False, 'auth_lock_failed'

            # Start Claude process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )

            # Release auth lock after initialization
            time.sleep(2)
            self._release_auth_lock()

            try:
                stdout, stderr = process.communicate(input=full_prompt, timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                worker_logger.error(f"Chunk {chunk_num} timed out after {timeout}s")
                return False, f'timeout_chunk_{chunk_num}'

            if return_code == 0 and stdout:
                # Validate output
                invalid_indicators = [
                    "Execution error", "Tôi đã dịch toàn bộ",
                    "Đây là một bài báo", "I've successfully translated",
                    "The translation maintains", "translation covers all",
                    "The translation preserves", "Here is the translation",
                    "configuration file", "corrupted",
                    "Unexpected end of JSON input"
                ]

                is_valid = (stdout and len(stdout.strip()) > 50 and
                          not any(indicator in stdout for indicator in invalid_indicators))

                if is_valid:
                    worker_logger.info(f"Chunk {chunk_num} translated successfully ({len(stdout)} chars)")
                    return True, stdout
                else:
                    worker_logger.error(f"Invalid translation output for chunk {chunk_num}")
                    return False, f'invalid_output_chunk_{chunk_num}'
            else:
                worker_logger.error(f"Claude failed for chunk {chunk_num}: {stderr[:200]}")
                return False, f'claude_error_chunk_{chunk_num}'

        finally:
            if os.path.exists(temp_prompt_path):
                os.unlink(temp_prompt_path)

    def translate_file(self, input_file: str) -> tuple[bool, str]:
        """Translate a single file using Claude executable with chunking support.

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
            content = self._sanitize_content(content)

            # Check if chunking is needed
            if should_chunk_file(content):
                worker_logger.info(f"Large file detected ({len(content)} chars, ~{estimate_tokens(content)} tokens). Using chunking strategy.")
                return self._translate_with_chunking(content, output_path, worker_logger)
            else:
                worker_logger.info(f"Normal file ({len(content)} chars). Using standard translation.")
                return self._translate_without_chunking(content, output_path, worker_logger, input_file)

        except Exception as e:
            worker_logger.error(f"Error translating {input_file}: {e}")
            import traceback
            worker_logger.error(f"Exception traceback: {traceback.format_exc()}")
            return False, 'translation'

    def _translate_with_chunking(self, content: str, output_path: Path, worker_logger) -> Tuple[bool, str]:
        """Translate content using chunking strategy."""

        # Split into chunks
        chunks = split_into_chunks(content)
        total_chunks = len(chunks)
        worker_logger.info(f"Split into {total_chunks} chunks")

        # Translate each chunk
        translations = {}
        failed_chunks = []

        for chunk in chunks:
            chunk_num = chunk['chunk_num']
            success, result = self._translate_single_chunk(chunk, worker_logger)

            if success:
                translations[chunk_num] = result
            else:
                failed_chunks.append(chunk_num)
                worker_logger.warning(f"Chunk {chunk_num} failed: {result}")

                # For critical failures, abort early
                if 'auth_lock' in result:
                    worker_logger.error("Auth lock failure - aborting chunked translation")
                    return False, 'auth_lock'

        # Check if we have enough successful chunks
        success_rate = len(translations) / total_chunks
        worker_logger.info(f"Translation complete: {len(translations)}/{total_chunks} chunks successful ({success_rate:.1%})")

        if success_rate < 0.5:
            worker_logger.error(f"Too many chunks failed ({len(failed_chunks)}/{total_chunks}). Aborting.")
            return False, 'translation'

        # Merge translations
        merged_text = merge_translated_chunks(chunks, translations)

        # Save to output file
        output_path.write_text(merged_text, encoding='utf-8')
        worker_logger.info(f"Merged translation saved to {output_path} ({len(merged_text)} chars)")

        if failed_chunks:
            worker_logger.warning(f"Note: Chunks {failed_chunks} failed and are marked as [CHUA DICH]")

        return True, 'success'

    def _translate_without_chunking(self, content: str, output_path: Path, worker_logger, input_file: str) -> Tuple[bool, str]:
        """Translate content without chunking (original method)."""

        # Build full prompt
        full_prompt = self.translation_prompt.format(content=content)

        # Create temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(full_prompt)
            temp_prompt_path = temp_file.name

        try:
            cmd = [
                self.claude_path,
                "--print",
                "--dangerously-skip-permissions",
                "--model", "sonnet"
            ]

            env = os.environ.copy()

            worker_logger.info(f"Translating {input_file} -> {output_path}")

            # Retry auth lock acquisition
            max_auth_retries = 10
            auth_retry_count = 0

            while auth_retry_count < max_auth_retries:
                if self._acquire_auth_lock():
                    worker_logger.info("Starting Claude translation (auth lock acquired)...")
                    break
                auth_retry_count += 1
                if auth_retry_count < max_auth_retries:
                    backoff_time = min(2 ** auth_retry_count, 30)
                    worker_logger.warning(f"Failed to acquire auth lock (attempt {auth_retry_count}), retrying in {backoff_time}s...")
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

            # Release auth lock after initialization
            time.sleep(2)
            self._release_auth_lock()

            try:
                stdout, stderr = process.communicate(input=full_prompt, timeout=FULL_FILE_TIMEOUT)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                worker_logger.error("Claude process timed out after 30 minutes")
                return False, 'translation'

            if return_code == 0 and stdout:
                # Validate output
                invalid_indicators = [
                    "Execution error", "Tôi đã dịch toàn bộ",
                    "Đây là một bài báo", "I've successfully translated",
                    "The translation maintains", "translation covers all",
                    "The translation preserves", "Here is the translation",
                    "configuration file", "corrupted",
                    "Unexpected end of JSON input",
                    "Claude configuration file at",
                    "The corrupted file has been back"
                ]

                is_valid = (stdout and len(stdout.strip()) > 50 and
                          not any(indicator in stdout for indicator in invalid_indicators))

                if is_valid:
                    output_path.write_text(stdout, encoding='utf-8')
                    worker_logger.info(f"Translation saved to {output_path} ({len(stdout)} chars)")
                    return True, 'success'
                else:
                    worker_logger.error(f"Invalid translation output: {stdout[:200]}...")
                    return False, 'translation'
            else:
                worker_logger.error(f"Claude command failed with return code {return_code}")
                worker_logger.error(f"Error output: {stderr}")
                return False, 'translation'

        finally:
            if os.path.exists(temp_prompt_path):
                os.unlink(temp_prompt_path)


def translate_worker(args: Tuple[str, str]) -> Tuple[str, bool, str]:
    """Worker function for multiprocessing translation.

    Returns:
        tuple: (filename, success, failure_reason)
    """
    filename, claude_path = args
    worker_pid = os.getpid()

    # Set up worker-specific logger
    worker_logger = logging.getLogger(f"worker_{worker_pid}")
    worker_logger.setLevel(logging.INFO)

    if not worker_logger.handlers:
        worker_handler = logging.StreamHandler()
        worker_formatter = logging.Formatter(
            f'%(asctime)s - WORKER-{worker_pid} - %(levelname)s - %(message)s'
        )
        worker_handler.setFormatter(worker_formatter)
        worker_logger.addHandler(worker_handler)
        worker_logger.propagate = False

    worker_logger.info(f"Starting translation of {filename}")

    # Set up signal handler
    def signal_handler(signum, frame):
        worker_logger.info(f"Received shutdown signal for {filename}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        translator = ClaudeTranslator(claude_path, worker_pid)
        worker_logger.info(f"Translator initialized for {filename}")

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
    """Idle worker function that polls for new files and processes them."""
    queue_file, claude_path = args
    worker_pid = os.getpid()

    # Set up worker-specific logger
    worker_logger = logging.getLogger(f"idle_worker_{worker_pid}")
    worker_logger.setLevel(logging.INFO)

    if not worker_logger.handlers:
        worker_handler = logging.StreamHandler()
        worker_formatter = logging.Formatter(
            f'%(asctime)s - IDLE-WORKER-{worker_pid} - %(levelname)s - %(message)s'
        )
        worker_handler.setFormatter(worker_formatter)
        worker_logger.addHandler(worker_handler)
        worker_logger.propagate = False

    worker_logger.info("Idle worker started, waiting for files...")

    # Set up signal handler
    def signal_handler(signum, frame):
        worker_logger.info("Idle worker received shutdown signal")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        queue_manager = TranslationQueueManager(queue_file)
        translator = ClaudeTranslator(claude_path, worker_pid)

        poll_interval = 5
        max_idle_time = 300  # 5 minutes
        idle_start = time.time()

        while True:
            if time.time() - idle_start > max_idle_time:
                worker_logger.info("Max idle time reached, shutting down idle worker")
                return (None, True, 'no_work')

            filename = queue_manager.get_next_file(blocking=True)

            if filename:
                worker_logger.info(f"Idle worker picked up file: {filename}")
                idle_start = time.time()

                success, failure_reason = translator.translate_file(filename)

                if success:
                    worker_logger.info(f"Successfully translated {filename}")
                    queue_manager.mark_completed(filename)
                    return (filename, True, 'success')
                elif failure_reason == 'auth_lock':
                    worker_logger.warning(f"Auth lock failure for {filename}")
                    queue_manager.reset_specific_file_processing(filename)
                    return (filename, False, 'auth_lock')
                else:
                    worker_logger.error(f"Translation failed for {filename}")
                    should_retry = queue_manager.handle_translation_failure(filename)
                    if should_retry:
                        worker_logger.info(f"File {filename} will be retried")
                    else:
                        worker_logger.warning(f"File {filename} moved to end of queue after max retries")
                    return (filename, False, failure_reason)
            else:
                time.sleep(poll_interval)

    except Exception as e:
        worker_logger.error(f"Idle worker exception: {e}")
        import traceback
        worker_logger.error(f"Traceback: {traceback.format_exc()}")
        return (None, False, 'translation')


class TranslationManager:
    """Main translation manager orchestrating the entire process."""

    def __init__(self, queue_file: str = "translation_queue.txt",
                 claude_path: str = "/home/ngocthanh/.nvm/versions/node/v24.11.0/bin/claude", max_workers: int = 6):
        self.queue_manager = TranslationQueueManager(queue_file)
        self.claude_path = claude_path
        self.max_workers = max_workers
        self.active_workers = 0
        self.worker_start_times = {}
        self.warmup_threshold = 300  # 5 minutes
        self.last_status = (0, 0, 0)
        self.last_status_log = 0
        self.last_stale_cleanup = 0

    def verify_claude_executable(self) -> bool:
        """Verify that Claude executable is available."""
        try:
            result = subprocess.run([self.claude_path, "--version"],
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            try:
                result = subprocess.run([self.claude_path, "--help"],
                                      capture_output=True, text=True, timeout=10)
                return result.returncode == 0
            except Exception:
                return False

    def run(self):
        """Main execution loop."""
        logger.info("Starting Translation Manager v2 with Chunking Support")
        logger.info(f"Chunking config: threshold={CHUNK_SIZE_THRESHOLD} chars, max_chunk={MAX_CHUNK_SIZE} chars")

        if not self.verify_claude_executable():
            logger.error(f"Claude executable not found or not working: {self.claude_path}")
            return False

        logger.info(f"Claude executable verified: {self.claude_path}")
        logger.info(f"Maximum workers: {self.max_workers}")

        # Clean duplicate entries
        logger.info("Cleaning duplicate arxiv_id entries from translation queue...")
        removed_count = self.queue_manager.clean_duplicate_arxiv_ids()
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate entries from queue")

        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}

                while True:
                    total, processing, pending = self.queue_manager.get_queue_status()
                    current_time = time.time()

                    # Log status changes
                    status_changed = (total, processing, pending) != self.last_status
                    time_for_update = current_time - self.last_status_log > 60

                    if status_changed or time_for_update:
                        logger.info(f"Queue status - Total: {total}, Processing: {processing}, Pending: {pending}")
                        self.last_status = (total, processing, pending)
                        self.last_status_log = current_time

                    # Check if done
                    if pending == 0 and processing == 0 and len(futures) == 0:
                        stale_cleaned = self.queue_manager.clean_stale_processing()
                        if stale_cleaned > 0:
                            logger.info(f"Final cleanup: cleaned {stale_cleaned} stale processing entries")
                            continue

                        if total == 0:
                            logger.info("Queue is empty. Nothing to process.")
                        else:
                            logger.info("All files completed successfully.")
                        break

                    # Handle edge cases
                    if pending > 0 and len(futures) == 0:
                        logger.warning(f"No active workers but {pending} pending files. Attempting to start workers...")
                        filename = self.queue_manager.get_next_file()
                        if filename:
                            future = executor.submit(translate_worker, (filename, self.claude_path))
                            futures[future] = ('file', filename)
                            self.worker_start_times[future] = time.time()
                            logger.info(f"Emergency restart: submitted {filename} for translation")
                        else:
                            time.sleep(5)
                        continue

                    if processing > 0 and len(futures) == 0:
                        logger.warning(f"Found {processing} orphaned processing items. Resetting...")
                        reset_count = self.queue_manager.reset_processing_status()
                        if reset_count > 0:
                            logger.info(f"Reset {reset_count} orphaned items")
                            time.sleep(0.5)
                        continue

                    # Submit new jobs
                    while len(futures) < self.max_workers:
                        if pending > 0:
                            filename = self.queue_manager.get_next_file()
                            if filename:
                                future = executor.submit(translate_worker, (filename, self.claude_path))
                                futures[future] = ('file', filename)
                                self.worker_start_times[future] = time.time()
                                logger.info(f"Submitted {filename} for translation")
                                continue

                        future = executor.submit(idle_worker, (str(self.queue_manager.queue_file), self.claude_path))
                        futures[future] = ('idle', f'idle_worker_{len(futures)}')
                        self.worker_start_times[future] = time.time()
                        logger.info(f"Started idle worker {len(futures)}")
                        break

                    # Check completed jobs
                    completed_futures = []
                    try:
                        for future in as_completed(futures, timeout=1):
                            completed_futures.append(future)
                    except:
                        pass

                    for future in completed_futures:
                        worker_type, worker_id = futures[future]
                        try:
                            result_filename, success, failure_reason = future.result()

                            if worker_type == 'file':
                                if success and result_filename:
                                    logger.info(f"Successfully completed: {result_filename}")
                                    self.queue_manager.mark_completed(result_filename)
                                elif result_filename and failure_reason == 'auth_lock':
                                    logger.warning(f"Auth lock failure for: {result_filename}")
                                    self.queue_manager.reset_specific_file_processing(result_filename)
                                elif result_filename:
                                    logger.error(f"Translation failed for: {result_filename} (reason: {failure_reason})")
                                    should_retry = self.queue_manager.handle_translation_failure(result_filename)
                                    if should_retry:
                                        logger.info(f"File {result_filename} will be retried")
                                    else:
                                        logger.warning(f"File {result_filename} moved to end of queue")
                            elif worker_type == 'idle':
                                if success and result_filename:
                                    logger.info(f"Idle worker completed: {result_filename}")
                                elif result_filename and failure_reason == 'auth_lock':
                                    logger.warning(f"Idle worker auth lock failure for: {result_filename}")
                                elif result_filename:
                                    logger.error(f"Idle worker failed: {result_filename}")
                                else:
                                    logger.info(f"Idle worker {worker_id} shut down")

                        except Exception as e:
                            logger.error(f"Error processing result for {worker_id}: {e}")
                            if worker_type == 'file':
                                try:
                                    self.queue_manager.reset_specific_file_processing(worker_id)
                                except:
                                    pass

                        if future in self.worker_start_times:
                            del self.worker_start_times[future]
                        del futures[future]

                    time.sleep(2)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            if futures:
                logger.info(f"Waiting for {len(futures)} remaining workers...")
                for future in futures:
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        logger.warning(f"Error waiting for future: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if futures:
                logger.info(f"Waiting for {len(futures)} remaining workers...")
                for future in futures:
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        logger.warning(f"Error waiting for future: {e}")
            return False

        logger.info("Translation Manager v2 completed successfully")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Automated Paper Translation Manager v2 with Chunking")
    parser.add_argument("--workers", type=int, default=6,
                       help="Number of parallel workers (default: 6)")
    parser.add_argument("--claude-path", type=str, default="/home/ngocthanh/.nvm/versions/node/v24.11.0/bin/claude",
                       help="Path to Claude executable")
    parser.add_argument("--queue-file", type=str, default="translation_queue.txt",
                       help="Path to translation queue file")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--clean-only", action="store_true",
                       help="Only clean duplicates and already-translated files")
    parser.add_argument("--clean-stale", action="store_true",
                       help="Only clean stale processing entries")

    # Chunking options
    parser.add_argument("--chunk-threshold", type=int, default=40000,
                       help="Character threshold for chunking (default: 40000)")
    parser.add_argument("--max-chunk-size", type=int, default=35000,
                       help="Maximum chunk size in characters (default: 35000)")

    args = parser.parse_args()

    # Store chunking config in a way that can be passed to workers
    chunking_config = {
        'chunk_threshold': args.chunk_threshold,
        'max_chunk_size': args.max_chunk_size
    }

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.workers < 1 or args.workers > 16:
        logger.error("Number of workers must be between 1 and 16")
        sys.exit(1)

    manager = TranslationManager(
        queue_file=args.queue_file,
        claude_path=args.claude_path,
        max_workers=args.workers
    )

    if args.clean_only:
        logger.info("Running in clean-only mode...")
        removed_count = manager.queue_manager.clean_duplicate_arxiv_ids()
        logger.info(f"Removed {removed_count} duplicate entries")
        logger.info("Queue cleanup completed")
        sys.exit(0)

    if args.clean_stale:
        logger.info("Running in clean-stale mode...")
        stale_cleaned = manager.queue_manager.clean_stale_processing()
        logger.info(f"Cleaned {stale_cleaned} stale processing entries")
        total, processing, pending = manager.queue_manager.get_queue_status()
        logger.info(f"Queue status - Total: {total}, Processing: {processing}, Pending: {pending}")
        sys.exit(0)

    success = manager.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
