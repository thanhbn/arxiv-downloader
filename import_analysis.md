# Python Import Analysis Report

## Overview
This analysis covers all Python files in the `/home/admin88/arxiv-downloader` directory and identifies external libraries that need to be installed via pip.

## Summary of Findings

### Total Files Analyzed: 17
1. `huggingface_crawler.py`
2. `test_orchestrator.py`
3. `check_status.py`
4. `show_rate_limits.py`
5. `translate_papers.py`
6. `pdf_to_txt_converter.py`
7. `arxiv_downloader_backup.py`
8. `arxiv_orchestrator_backup.py`
9. `organize_papers.py`
10. `check_multimodal.py`
11. `fix_multimodal.py`
12. `check_and_move_papers.py`
13. `check_and_move_papers_enhanced.py`
14. `arxiv_downloader.py`
15. `arxiv_orchestrator.py`
16. `vocabulary/keyword_extractor.py`
17. `vocabulary/example_usage.py`
18. `test_setup.py`

## External Libraries Required

### Core Dependencies (High Priority)
These are essential for the main functionality:

1. **requests** - HTTP requests and PDF downloading
   - Used in: `huggingface_crawler.py`, `arxiv_downloader_backup.py`, `arxiv_downloader.py`
   - Critical for ArXiv PDF downloads

2. **openai** - OpenAI API integration
   - Used in: `translate_papers.py`
   - Required for translation functionality

3. **aiofiles** - Async file operations
   - Used in: `arxiv_orchestrator.py`
   - Required for optimized async processing

### NLP and Text Processing (Medium Priority)
Used for vocabulary and keyword extraction:

4. **nltk** - Natural Language Toolkit
   - Used in: `vocabulary/keyword_extractor.py`
   - Required for keyword extraction features

5. **scikit-learn** (sklearn) - Machine learning library
   - Used in: `vocabulary/keyword_extractor.py`
   - Required for TF-IDF keyword extraction

6. **numpy** - Numerical computing
   - Used in: `vocabulary/keyword_extractor.py`
   - Required for mathematical operations in keyword extraction

7. **yake** - YAKE keyword extractor
   - Used in: `vocabulary/keyword_extractor.py`
   - Required for YAKE keyword extraction algorithm

### PDF Processing (Medium Priority)
8. **PyPDF2** - PDF text extraction
   - Used in: `pdf_to_txt_converter.py`, `vocabulary/keyword_extractor.py`
   - Required for PDF text extraction

9. **pdfplumber** - Advanced PDF processing (optional fallback)
   - Used in: `pdf_to_txt_converter.py`
   - Optional but recommended for better PDF text extraction

### Testing and Development (Low Priority)
10. **beautifulsoup4** (bs4) - HTML parsing
    - Listed in: `test_setup.py`
    - May be used for web scraping functionality

11. **tqdm** - Progress bars
    - Listed in: `test_setup.py`
    - May be used for progress indication

12. **aiohttp** - Async HTTP client
    - Listed in: `test_setup.py`
    - May be used for async HTTP operations

## Standard Library Modules Used
These are built-in Python modules (no installation required):
- `os`, `sys`, `re`, `json`, `time`, `subprocess`, `pathlib`
- `datetime`, `urllib.parse`, `logging`, `argparse`
- `concurrent.futures`, `threading`, `asyncio`
- `collections`, `glob`, `shutil`

## File-by-File Breakdown

### Core Download Scripts
**huggingface_crawler.py**
- External: `requests`
- Standard: `os`, `re`, `urllib.parse`, `time`, `pathlib`

**arxiv_downloader.py** (Main downloader)
- External: `requests`
- Standard: `os`, `sys`, `time`, `pathlib`, `urllib.parse`, `re`, `concurrent.futures`, `threading`, `random`

**arxiv_orchestrator.py** (Optimized)
- External: `aiofiles`
- Standard: `os`, `json`, `asyncio`, `subprocess`, `sys`, `time`, `pathlib`, `datetime`, `urllib.parse`, `re`, `concurrent.futures`, `threading`

### Translation Scripts
**translate_papers.py**
- External: `openai`
- Standard: `os`, `glob`, `pathlib`, `time`, `json`, `logging`

### PDF Processing Scripts
**pdf_to_txt_converter.py**
- External: `PyPDF2`, `pdfplumber` (fallback)
- Standard: `os`, `glob`, `re`, `subprocess`, `sys`, `pathlib`

### Vocabulary and Keyword Extraction
**vocabulary/keyword_extractor.py**
- External: `numpy`, `PyPDF2`, `nltk`, `sklearn`, `yake`
- Standard: `re`, `collections`, `typing`

**vocabulary/example_usage.py**
- External: None (imports from keyword_extractor.py)
- Standard: `os`

### Organization and Utility Scripts
**check_and_move_papers_enhanced.py**
- External: None
- Standard: `os`, `shutil`, `re`, `logging`, `time`, `pathlib`, `datetime`, `argparse`

**test_setup.py**
- External: None (tests for: `requests`, `bs4`, `tqdm`, `aiohttp`, `aiofiles`, `nltk`, `sklearn`, `numpy`, `PyPDF2`, `yake`)
- Standard: `sys`, `subprocess`

## Requirements.txt Format

```txt
# Core dependencies for ArXiv downloading
requests>=2.25.0

# Translation functionality
openai>=1.0.0

# Async file operations
aiofiles>=0.8.0

# NLP and keyword extraction
nltk>=3.6
scikit-learn>=1.0.0
numpy>=1.20.0
yake>=0.4.8

# PDF processing
PyPDF2>=3.0.0
pdfplumber>=0.7.0

# Optional testing dependencies
beautifulsoup4>=4.9.0
tqdm>=4.60.0
aiohttp>=3.8.0
```

## Installation Commands

### Essential Dependencies (Minimum)
```bash
pip install requests openai aiofiles
```

### Full Feature Set
```bash
pip install requests openai aiofiles nltk scikit-learn numpy yake PyPDF2 pdfplumber
```

### Development and Testing
```bash
pip install requests openai aiofiles nltk scikit-learn numpy yake PyPDF2 pdfplumber beautifulsoup4 tqdm aiohttp
```

## Dependency Priority Levels

### Level 1 (Critical) - Core ArXiv Functionality
- `requests` - Essential for downloading PDFs
- `openai` - Required for translation features (if used)
- `aiofiles` - Required for async orchestrator

### Level 2 (Important) - Enhanced Features
- `nltk`, `scikit-learn`, `numpy`, `yake` - Keyword extraction
- `PyPDF2`, `pdfplumber` - PDF text processing

### Level 3 (Optional) - Development/Testing
- `beautifulsoup4`, `tqdm`, `aiohttp` - May be used in future features

## Notes
1. Many scripts will work without all dependencies - install based on required functionality
2. The translation script requires OpenAI API key environment variable
3. NLTK may require additional data downloads (punkt, stopwords)
4. Some scripts have fallback mechanisms when optional libraries are missing