# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Download Papers (Optimized - Parallel Processing)
```bash
# Download papers using optimized Python script (8 workers default)
python scripts/arxiv_downloader.py <url_file>

# Examples:
python scripts/arxiv_downloader.py CoT.txt
python scripts/arxiv_downloader.py RAG.txt
python scripts/arxiv_downloader.py Benchmark.txt

# WARNING: ArXiv allows only 1 concurrent connection and 3 second delays!
# Only use 1 worker to comply with ArXiv rate limits
python scripts/arxiv_downloader.py CoT.txt 1

# Download to custom directory (FIXED)
python scripts/arxiv_downloader.py multimodal/arxiv_links.txt 1 multimodal

# Orchestrator (respects ArXiv rate limits) - FIXED to save to correct folders
python scripts/arxiv_orchestrator.py

# CAUTION: Multiple concurrent connections may get blocked by ArXiv
python scripts/arxiv_orchestrator.py 1 1

# Download using shell script (fallback option)
./scripts/download_arxiv.sh <links_file> <destination_directory>
```

### Testing Downloads
```bash
# Test with small collection (fast with parallel processing)
python scripts/arxiv_downloader.py icl.txt

# Test with custom worker count
python scripts/arxiv_downloader.py icl.txt 4

# Check downloaded files
ls -la multimodal_papers/
ls -la CoT/
ls -la RAG/
```

### PDF to TXT Conversion
```bash
# Convert all PDFs in a collection to TXT format with proper naming
python3 scripts/pdf_to_txt_converter.py --all

# Convert PDFs in specific collection
python3 scripts/pdf_to_txt_converter.py --both --collection pruning

# Only convert PDFs to TXT (no renaming)
python3 scripts/pdf_to_txt_converter.py --convert --collection clarify

# Only rename existing TXT files with paper titles (recheck functionality)
python3 scripts/pdf_to_txt_converter.py --rename --collection pruning

# Interactive mode - choose options manually
python3 scripts/pdf_to_txt_converter.py

# Process specific collection with both conversion and renaming
python3 scripts/pdf_to_txt_converter.py --collection multimodal

# Get help with all available options
python3 scripts/pdf_to_txt_converter.py --help
```

### Paper Organization & Management
```bash
# Check paper organization against arxiv_links.txt files (dry run)
python3 scripts/check_and_move_papers_enhanced.py

# Actually move misplaced papers to correct collections
python3 scripts/check_and_move_papers_enhanced.py --execute

# Process specific collections only
python3 scripts/check_and_move_papers_enhanced.py --collections multimodal rag peft

# Enhanced logging with different levels
python3 scripts/check_and_move_papers_enhanced.py --log-level DEBUG --verbose

# Save detailed log to file
python3 scripts/check_and_move_papers_enhanced.py --log-file organization.log --execute

# Full featured run with comprehensive logging
python3 scripts/check_and_move_papers_enhanced.py --execute --verbose --log-level INFO --log-file full_organization.log
```

### Command Reference & Help
```bash
# Show comprehensive command cheatsheet with all available scripts
./cheatsheet.sh

# List all available scripts without descriptions
./cheatsheet.sh -l

# Get detailed help for specific script
./cheatsheet.sh --help-for pdf_to_txt_converter.py
./cheatsheet.sh --help-for arxiv_downloader.py

# Show cheatsheet usage options
./cheatsheet.sh --help

# Quick access to any script help (alternative method)
./cheatsheet.sh pdf_to_txt_converter.py
```

### CLI Tool (Easy Access)
```bash
# ArXiv Downloader CLI - Direct access from root directory
python3 arxivdl_cli.py --help

# Use CLI tool for interactive downloading
python3 arxivdl_cli.py

# CLI tool with specific options
python3 arxivdl_cli.py --file CoT.txt --workers 1
```

## Architecture Overview

This is an ArXiv paper downloader tool designed for academic research paper collection with the following components:

### Core Components

#### Python Downloader (arxiv_downloader.py) - OPTIMIZED
- **Parallel Processing**: Downloads up to 8 papers simultaneously using ThreadPoolExecutor
- **Smart Rate Limiting**: Random delays (0.3-0.8s) to avoid overwhelming servers
- **Enhanced Error Handling**: Robust retry logic and temp file protection
- **Real-time Statistics**: Progress tracking with download summaries
- **Configurable Workers**: Adjustable parallelism (1-16 workers)
- **File Integrity**: Uses temporary files to prevent corruption

#### Orchestrator (arxiv_orchestrator.py) - OPTIMIZED  
- **Async Processing**: Handles multiple collections concurrently
- **JSON Progress Tracking**: Persistent progress with timestamps and recovery
- **Performance Metrics**: Detailed reports comparing sequential vs parallel performance
- **Configurable Parallelism**: Customizable collection and worker counts
- **Error Recovery**: Graceful handling of timeouts and failures

#### Shell Script (download_arxiv.sh) - Legacy Fallback
- Enhanced bash script with advanced features
- Configurable rate limiting (default: 3 seconds between downloads)
- Comprehensive error handling with retry logic (up to 3 attempts)
- Colored output for better user experience
- Progress tracking and download summaries
- Proper User-Agent headers to identify as research bot

#### Command Reference Tool (cheatsheet.sh) - INTERACTIVE HELP SYSTEM
- **Auto-Discovery**: Automatically finds and categorizes all Python and shell scripts in the directory
- **Colorized Output**: Color-coded sections and commands for easy readability
- **Multiple Help Formats**: Supports --help, -h, and help options testing for each script
- **Categorized Display**: Organizes scripts by function (Download, PDF Processing, Organization, Development, Setup, Utility)
- **Description Extraction**: Automatically extracts descriptions from docstrings and file comments
- **Interactive Navigation**: Quick access to specific script help and usage examples
- **List Mode**: Compact listing of all available scripts without descriptions
- **Script Detection**: Identifies 22+ scripts and their supported help options
- **Usage Examples**: Includes quick start examples and common usage patterns

#### PDF to TXT Converter (pdf_to_txt_converter.py) - ENHANCED
- **Multi-Library Support**: Uses PyPDF2 (primary) and pdfplumber (fallback) for robust text extraction
- **Smart Renaming**: Automatically renames files from arxiv IDs to include paper titles
- **Page-by-Page Processing**: Extracts text with clear page markers and error handling
- **Table Extraction**: Attempts to extract tables when regular text extraction fails
- **Recheck Functionality**: Can rename existing TXT files without reconverting PDFs
- **Collection Support**: Process specific collections or all collections automatically
- **Combined Operations**: Support for mixed command-line arguments (--rename --collection)
- **Error Recovery**: Graceful handling of extraction failures with detailed error reporting
- **Filename Normalization**: Handles special characters and length limits for filesystem compatibility

#### Paper Organization Scripts
**check_and_move_papers_enhanced.py** - Advanced Collection Management
- **Comprehensive Logging**: Timestamps, log levels (DEBUG/INFO/WARNING/ERROR), file output
- **Smart Paper Detection**: Scans all arxiv_links.txt files across 156+ collections
- **Intelligent Moving**: Finds misplaced papers and moves them to correct collection folders
- **Progress Tracking**: Real-time progress indicators with completion percentages
- **Error Handling**: Robust error recovery with detailed error reporting
- **Dry Run Mode**: Safe preview mode to see what would be moved before execution
- **Collection Filtering**: Process specific collections or all collections
- **Performance Metrics**: Execution time tracking and summary statistics
- **Status Indicators**: Visual status with emojis (✓✗?) for better readability

### Paper Collections

The repository contains curated collections of arXiv papers organized by research topic:

#### Major Collections
- **CoT/** - Chain of Thought reasoning papers
- **RAG/** - Retrieval-Augmented Generation papers  
- **Benchmark/** - Benchmarking and evaluation papers
- **icl-papers/** - In-Context Learning papers
- **multimodal_papers/** - Multimodal AI research papers

#### Specialized Collections (156+ total)
The system now supports 156+ specialized research collections, each with their own `arxiv_links.txt` file:
- **peft/** - Parameter-Efficient Fine-Tuning
- **multilingual/** - Multilingual language models
- **diffusion/** - Diffusion models and generation
- **attention/** - Attention mechanisms
- **quantization/** - Model quantization techniques
- **interpretability/** - Model interpretability and explainability
- **knowledge-graph/** - Knowledge graph integration
- **long-context/** - Long context processing
- **math/** - Mathematical reasoning
- **medical/** - Medical AI applications
- And many more specialized domains...

### URL Files

Text files containing arXiv PDF URLs for batch downloading:
- `CoT.txt` - Chain of Thought paper URLs
- `RAG.txt` - RAG paper URLs
- `Benchmark.txt` - Benchmark paper URLs
- `icl.txt` - In-Context Learning paper URLs
- `arxiv_links.txt` - Multimodal paper URLs

## Usage Patterns

### Basic Download Workflow
1. Choose a URL file (e.g., `CoT.txt`)
2. Run the downloader: `python scripts/arxiv_downloader.py CoT.txt`
3. Papers are downloaded to a directory named after the input file (e.g., `CoT/`)

### Command Discovery Workflow
1. **Quick overview**: Run `./cheatsheet.sh` to see all available commands with descriptions
2. **Find specific help**: Use `./cheatsheet.sh --help-for SCRIPT_NAME` for detailed script help
3. **List all scripts**: Use `./cheatsheet.sh -l` for compact script listing
4. **Get examples**: Check the quick start examples section in the cheatsheet output

### PDF to TXT Conversion Workflow
1. **Download papers**: Use scripts/arxiv_downloader.py to get PDF files
2. **Convert to TXT**: Use scripts/pdf_to_txt_converter.py to extract text with proper naming
3. **Recheck existing**: Use --rename option to fix filenames of already converted files
4. **Batch processing**: Use --all to process all collections automatically

### Advanced Download with Shell Script
1. Use the shell script for better error handling and progress tracking
2. Example: `./scripts/download_arxiv.sh RAG.txt ./my_papers`
3. Configure rate limiting by modifying variables at the top of the script

### Performance & Rate Limiting
The optimized scripts provide significant performance improvements while respecting server limits:

#### ArXiv Rate Limit Compliance ⚠️
- **IMPORTANT**: ArXiv allows only **1 concurrent connection** and **3+ second delays**
- **Default settings**: 1 worker, 3-3.5s delays to comply with ArXiv policy
- **Violation risks**: IP blocking, request failures, service denial
- **Official policy**: "make no more than one request every three seconds"

#### Performance Considerations
- **Enhanced features**: Better error handling, progress tracking, JSON persistence
- **Async processing**: Non-blocking I/O for collection management  
- **Smart retry**: Automatic backoff on server errors
- **File integrity**: Temporary file handling to prevent corruption

#### Rate Limiting Configuration
- **Python downloader**: 3-3.5s delays between downloads (ArXiv compliant)
- **Orchestrator**: Sequential collection processing with proper delays
- **Shell script**: 3-second delay (configurable via `SLEEP_BETWEEN_DOWNLOADS`)
- **Adaptive**: Automatic backoff on server errors

#### Safe Usage Recommendations
- **Always use**: 1 worker only (default)
- **Respect delays**: 3+ seconds between requests
- **Monitor**: Watch for 429/403 errors indicating rate limiting
- **Be patient**: ArXiv compliance means slower but reliable downloads

## File Organization

Papers are automatically organized by research topic through the directory structure created by the input filename. This allows for easy categorization and retrieval of papers by subject area.

### Automated Paper Organization
The enhanced organization system ensures papers are placed in the correct collection folders:

1. **Collection Detection**: Automatically scans all subdirectories for `arxiv_links.txt` files
2. **Paper Matching**: Extracts arXiv IDs from URLs and finds corresponding PDF files
3. **Smart Moving**: Identifies misplaced papers and moves them to correct collections
4. **Integrity Checking**: Verifies each collection against its `arxiv_links.txt` file
5. **Comprehensive Reporting**: Provides detailed statistics on collection completeness

### Organization Workflow
```bash
# Step 1: Check current organization status
python3 scripts/check_and_move_papers_enhanced.py --verbose

# Step 2: Review what would be moved (dry run)
python3 scripts/check_and_move_papers_enhanced.py --collections multimodal rag

# Step 3: Execute organization with logging
python3 scripts/check_and_move_papers_enhanced.py --execute --log-file organization.log

# Step 4: Verify organization completed successfully
python3 scripts/check_and_move_papers_enhanced.py --log-level WARNING
```

### Collection Completeness Tracking
- **Completion Rate**: Percentage of expected papers present in each collection
- **Missing Papers**: Papers listed in `arxiv_links.txt` but not found in collection folder
- **Extra Papers**: Papers in collection folder but not listed in `arxiv_links.txt`
- **Global Search**: Automatic detection of misplaced papers across all collections