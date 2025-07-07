# ArXiv Downloader and Translation System - Complete Usage Guide

This guide provides step-by-step instructions for using the ArXiv paper downloader and translation system from start to finish.

## Overview

This system allows you to:
1. Download academic papers from ArXiv in bulk
2. Convert PDFs to text format
3. Translate papers to Vietnamese using Claude AI
4. Organize papers by research topics

## Prerequisites

- Python 3.7+
- Claude CLI installed and configured
- Internet connection for downloading papers
- Sufficient disk space for papers and translations

## Complete Workflow

### Step 1: Create Collection Lists

**Purpose**: Define which papers to download for each research topic.

**Scripts Used**: Manual creation or existing files

**Process**:
```bash
# Create or edit collection files (one URL per line)
# Example: Create CoT.txt for Chain of Thought papers
nano CoT.txt

# Add ArXiv PDF URLs like:
# https://arxiv.org/pdf/2101.06804.pdf
# https://arxiv.org/pdf/2201.11903.pdf
```

**Key Files**:
- `CoT.txt` - Chain of Thought papers
- `RAG.txt` - Retrieval-Augmented Generation papers
- `Benchmark.txt` - Benchmarking papers
- `icl.txt` - In-Context Learning papers
- `collection_name/arxiv_links.txt` - Links for specific collections

### Step 2: Download Papers

**Purpose**: Download PDF files from ArXiv URLs.

**Scripts Used**: 
- `arxiv_downloader.py` (primary, optimized)
- `arxiv_orchestrator.py` (for multiple collections)
- `download_arxiv.sh` (fallback)

**Process**:
```bash
# Download papers from a single collection (RECOMMENDED)
python3 arxiv_downloader.py CoT.txt 1

# Download to specific directory
python3 arxiv_downloader.py multimodal/arxiv_links.txt 1 multimodal

# Download multiple collections with orchestrator
python3 arxiv_orchestrator.py 1 1

# Using shell script (fallback)
./download_arxiv.sh CoT.txt ./CoT_papers
```

**⚠️ Important**: Always use `1` worker to comply with ArXiv rate limits (3+ second delays required).

### Step 3: Create/Organize Collection Folders

**Purpose**: Ensure papers are in correct collection-specific directories.

**Scripts Used**: 
- `check_and_move_papers_enhanced.py`
- Manual folder creation

**Process**:
```bash
# Check current organization (dry run)
python3 check_and_move_papers_enhanced.py

# Move misplaced papers to correct collections
python3 check_and_move_papers_enhanced.py --execute

# Create folders manually if needed
mkdir collection_name
```

### Step 4: Convert PDFs to Text

**Purpose**: Extract text content from PDF files for translation.

**Scripts Used**: `pdf_to_txt_converter.py`

**Process**:
```bash
# Convert all PDFs to text with proper naming
python3 pdf_to_txt_converter.py --all

# Convert specific collection
python3 pdf_to_txt_converter.py --both --collection pruning

# Only convert (no renaming)
python3 pdf_to_txt_converter.py --convert --collection clarify

# Only rename existing text files
python3 pdf_to_txt_converter.py --rename --collection pruning
```

### Step 5: Scan and Create/Update Translation Queue

**Purpose**: Build list of text files that need Vietnamese translation.

**Scripts Used**: `translate_manager.py` with `--clean-only` option

**Process**:
```bash
# Scan all files and build translation queue
python3 translate_manager.py --clean-only

# Manual rebuild if needed (Python script)
python3 -c "
import glob
from pathlib import Path
from translate_manager import TranslationQueueManager

queue_manager = TranslationQueueManager('translation_queue.txt')
txt_files = []

# Find all .txt files (excluding _vi.txt)
for pattern in ['*/*.txt', '*/*/*.txt']:
    files = glob.glob(pattern)
    for file in files:
        if not file.endswith('_vi.txt') and not file.endswith('translation_queue.txt'):
            txt_files.append(file)

# Filter files that need translation
files_to_translate = [f for f in txt_files if not queue_manager._has_vietnamese_translation(f)]

# Write queue file
with open('translation_queue.txt', 'w') as f:
    for file in sorted(files_to_translate):
        f.write(file + '\n')

print(f'Created translation queue with {len(files_to_translate)} files')
"
```

### Step 6: Run Translation with Multiple Workers

**Purpose**: Translate text files to Vietnamese using Claude AI.

**Scripts Used**: `translate_manager.py`

**Process**:
```bash
# Start translation with 4 workers (recommended)
python3 translate_manager.py --workers 4

# Start with 6 workers (maximum safe)
python3 translate_manager.py --workers 6

# Use custom Claude path if needed
python3 translate_manager.py --workers 4 --claude-path /usr/local/bin/claude

# Verbose mode for debugging
python3 translate_manager.py --workers 4 --verbose
```

**Features**:
- ✅ Automatic timestamp tracking (`[Processing] 20250708-0615 filename.txt`)
- ✅ Stale cleanup (>30 minutes automatically reset to pending)
- ✅ Duplicate detection and removal
- ✅ Already-translated file detection
- ✅ Robust error handling and recovery

### Step 7: Monitor Translation Progress

**Purpose**: Check how many papers have been translated and monitor progress.

**Commands**:
```bash
# Count total Vietnamese translations
find . -name "*_vi.txt" | wc -l

# Check queue status
python3 -c "
from translate_manager import TranslationQueueManager
qm = TranslationQueueManager('translation_queue.txt')
total, processing, pending = qm.get_queue_status()
print(f'Queue Status: Total={total}, Processing={processing}, Pending={pending}')
"

# List translated files by collection
find . -name "*_vi.txt" | sort

# Check for specific collection
find pruning/ -name "*_vi.txt" | wc -l
```

### Step 8: Maintenance and Troubleshooting

**Purpose**: Handle issues and maintain the translation system.

#### Clean Stale Processing Entries
```bash
# Clean entries stuck in processing >30 minutes
python3 translate_manager.py --clean-stale
```

#### Reset All Processing to Pending
```bash
python3 -c "
from translate_manager import TranslationQueueManager
qm = TranslationQueueManager('translation_queue.txt')
reset_count = qm.reset_processing_status()
print(f'Reset {reset_count} processing entries to pending')
"
```

#### Rebuild Translation Queue (Manual)
```bash
# If translation_queue.txt is empty or corrupted
python3 translate_manager.py --clean-only

# Or manual rebuild (see Step 5)
```

#### Check for Missing Translations
```bash
# Find text files without Vietnamese translations
python3 -c "
import glob
from translate_manager import TranslationQueueManager

qm = TranslationQueueManager('translation_queue.txt')
txt_files = glob.glob('*/*.txt') + glob.glob('*/*/*.txt')
missing = []

for file in txt_files:
    if not file.endswith('_vi.txt') and not file.endswith('translation_queue.txt'):
        if not qm._has_vietnamese_translation(file):
            missing.append(file)

print(f'Files missing Vietnamese translation: {len(missing)}')
for file in missing[:10]:  # Show first 10
    print(f'  {file}')
if len(missing) > 10:
    print(f'  ... and {len(missing) - 10} more')
"
```

## Directory Structure

```
arxiv-downloader-clean/
├── collection_name/           # Downloaded papers by topic
│   ├── arxiv_links.txt       # URLs for this collection
│   ├── paper1.pdf            # Downloaded PDF
│   ├── paper1.txt            # Extracted text
│   └── paper1_vi.txt         # Vietnamese translation
├── translation_queue.txt     # Files awaiting translation
├── translation_manager.log   # Translation logs
├── arxiv_downloader.py       # Main download script
├── translate_manager.py      # Translation orchestrator
├── pdf_to_txt_converter.py   # PDF to text converter
└── check_and_move_papers_enhanced.py  # Organization tool
```

## Command Reference

### Quick Commands
```bash
# Get help for any script
./cheatsheet.sh

# Download papers (1 worker for ArXiv compliance)
python3 arxiv_downloader.py collection.txt 1

# Convert PDFs to text
python3 pdf_to_txt_converter.py --all

# Build translation queue
python3 translate_manager.py --clean-only

# Start translation
python3 translate_manager.py --workers 4

# Check progress
find . -name "*_vi.txt" | wc -l
```

### Emergency Recovery
```bash
# Reset stuck translations
python3 translate_manager.py --clean-stale

# Rebuild everything
python3 translate_manager.py --clean-only
python3 translate_manager.py --workers 4
```

## Best Practices

1. **ArXiv Compliance**: Always use 1 worker for downloads to respect rate limits
2. **Regular Monitoring**: Check queue status and translation progress regularly
3. **Backup**: Keep backups of important queue files and logs
4. **Gradual Processing**: Start with small collections to test the workflow
5. **Resource Management**: Monitor disk space as translations can be large
6. **Error Handling**: Use verbose mode when troubleshooting issues

## Troubleshooting

### Common Issues

1. **Empty translation_queue.txt**:
   - Run: `python3 translate_manager.py --clean-only`
   - Manual rebuild if needed (see Step 5)

2. **Files stuck in processing**:
   - Run: `python3 translate_manager.py --clean-stale`

3. **Download failures**:
   - Check internet connection
   - Verify ArXiv URLs are correct
   - Use 1 worker to avoid rate limiting

4. **Translation errors**:
   - Check Claude CLI is installed and working
   - Verify Claude configuration
   - Use `--verbose` for detailed error messages

5. **Lock file errors**:
   - Fixed in latest version
   - Delete `.lock` files if they persist

### Getting Help

- Use `./cheatsheet.sh` for quick command reference
- Check log files for detailed error information
- Run scripts with `--help` for usage information
- Use `--verbose` flag for debugging

## Performance Notes

- **Translation Speed**: ~2-4 papers per minute with 4 workers
- **Disk Usage**: Allow ~10-20MB per paper (PDF + text + translation)
- **Memory Usage**: Translation manager uses moderate memory for queuing
- **Network**: Downloads respect ArXiv 3-second delay requirement

## Success Metrics

- Papers downloaded: Check folder contents
- Papers converted: Count `.txt` files
- Papers translated: `find . -name "*_vi.txt" | wc -l`
- Queue health: Processing items should not stay >30 minutes