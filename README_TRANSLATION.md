# 🌐 Automated Paper Translation System

Comprehensive translation system using local Claude executable with queue management, parallel processing, and real-time monitoring.

## 📋 Overview

This system automatically translates academic papers from English to Vietnamese using a local Claude executable. It features:

- **Queue Management**: Thread-safe file queue with processing status tracking
- **Parallel Processing**: Configurable worker limits (1-16 workers)
- **Auto-Confirmation**: Automatically handles Claude y/N prompts
- **Real-time Monitoring**: Live progress tracking and system resource monitoring
- **File Locking**: Prevents race conditions in multi-process environments
- **Robust Error Handling**: Graceful handling of failures and timeouts

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have the local Claude executable installed and available in your PATH:

```bash
# Test Claude installation
claude --help

# Or specify custom path
/path/to/claude --help
```

### 2. Add Files to Translation Queue

```bash
# Add specific files
python add_to_translation_queue.py paper1.txt paper2.txt

# Add all .txt files in current directory
python add_to_translation_queue.py *.txt

# Add all .txt files in a directory
python add_to_translation_queue.py ./papers/

# Add recursively from subdirectories
python add_to_translation_queue.py --recursive ./collections/

# List what would be added (dry run)
python add_to_translation_queue.py --list *.txt
```

### 3. Start Translation

```bash
# Start with default settings (6 workers)
python translate_manager.py

# Custom worker count
python translate_manager.py --workers 4

# Custom Claude path
python translate_manager.py --claude-path /usr/local/bin/claude

# Custom queue file
python translate_manager.py --queue-file my_translations.txt
```

### 4. Monitor Progress

```bash
# Start real-time monitor (in another terminal)
python monitor_translation.py

# Custom refresh rate
python monitor_translation.py --refresh-rate 3

# Monitor custom queue file
python monitor_translation.py --queue-file my_translations.txt
```

## 📁 File Structure

```
arxiv-downloader/
├── translate_manager.py           # Main translation orchestrator
├── monitor_translation.py         # Real-time progress monitor
├── add_to_translation_queue.py    # Queue management helper
├── translation_queue.txt          # Queue file (auto-created)
├── translation_manager.log        # Translation logs
└── README_TRANSLATION.md          # This file
```

## 🔧 Configuration Options

### Translation Manager (`translate_manager.py`)

```bash
python translate_manager.py [OPTIONS]

Options:
  --workers N           Number of parallel workers (1-16, default: 6)
  --claude-path PATH    Path to Claude executable (default: claude)
  --queue-file FILE     Queue file path (default: translation_queue.txt)
  --verbose, -v         Enable debug logging
```

### Monitor (`monitor_translation.py`)

```bash
python monitor_translation.py [OPTIONS]

Options:
  --queue-file FILE     Queue file to monitor (default: translation_queue.txt)
  --refresh-rate N      Screen refresh rate in seconds (1-60, default: 5)
  --log-lines N         Number of log lines to show (default: 8)
```

### Queue Manager (`add_to_translation_queue.py`)

```bash
python add_to_translation_queue.py [PATHS...] [OPTIONS]

Options:
  --queue-file FILE     Queue file path (default: translation_queue.txt)
  --recursive, -r       Search directories recursively
  --force, -f           Add files even if already in queue
  --list, -l            List files without adding (dry run)
  --clear               Clear entire queue before adding
```

## 🔄 How It Works

### 1. Queue Management

- Files are added to `translation_queue.txt` with full paths
- Processing files are marked with `[Processing]` prefix
- Completed files are removed from the queue
- File locking prevents concurrent access issues

### 2. Translation Process

Each worker process:
1. Gets next file from queue (thread-safe)
2. Marks file as `[Processing]`
3. Reads file content and builds translation prompt
4. Calls Claude executable with auto-confirmation
5. Saves translation as `[filename]_vi.txt`
6. Removes completed file from queue

### 3. Claude Executable Integration

The system calls Claude using:
```bash
claude --model sonnet
```

And automatically handles:
- Stdin prompt feeding
- Auto-confirmation of y/N prompts
- Output capture and file saving
- Error handling and timeouts

## 📊 Monitoring Features

The monitor displays:

- **Queue Status**: Total, processing, pending files with progress bar
- **Active Processes**: Claude processes with CPU/memory usage
- **Recent Logs**: Latest translation activities
- **System Resources**: Disk space and memory usage
- **Runtime Statistics**: Monitor uptime and refresh rate

## ⚙️ Advanced Usage

### Batch Processing Multiple Collections

```bash
# Add all papers from multiple directories
python add_to_translation_queue.py --recursive \
    ./activation/ ./attention/ ./benchmarks/

# Start translation with optimal worker count
python translate_manager.py --workers 8
```

### Custom Translation Workflow

```bash
# Clear existing queue
python add_to_translation_queue.py --clear

# Add specific patterns
python add_to_translation_queue.py \
    --recursive \
    "./papers/2024*.txt" \
    "./research/llm*.txt"

# Start with custom configuration
python translate_manager.py \
    --workers 4 \
    --claude-path /opt/claude/bin/claude \
    --verbose
```

### Monitoring During Translation

```bash
# Terminal 1: Start translation
python translate_manager.py --workers 6

# Terminal 2: Monitor progress
python monitor_translation.py --refresh-rate 2

# Terminal 3: Check logs
tail -f translation_manager.log
```

## 🛠️ Troubleshooting

### Common Issues

**Claude executable not found:**
```bash
# Check if Claude is in PATH
which claude

# Or specify full path
python translate_manager.py --claude-path /full/path/to/claude
```

**Permission denied on queue file:**
```bash
# Check file permissions
ls -la translation_queue.txt

# Fix permissions if needed
chmod 644 translation_queue.txt
```

**Workers not starting:**
```bash
# Check available system resources
python monitor_translation.py

# Reduce worker count
python translate_manager.py --workers 2
```

### Performance Tuning

**Optimal Worker Count:**
- Start with 4-6 workers for most systems
- Monitor CPU/memory usage with the monitor
- Adjust based on Claude executable performance

**Memory Management:**
- Each worker uses ~100-500MB depending on paper size
- Monitor memory usage during translation
- Reduce workers if memory usage is high

**Disk Space:**
- Translated files are roughly the same size as originals
- Monitor disk usage for large collections
- Ensure adequate free space before starting

## 🔐 Safety Features

- **File Locking**: Prevents queue corruption in concurrent access
- **Atomic Operations**: Queue updates are atomic to prevent corruption
- **Error Recovery**: Graceful handling of translation failures
- **Process Isolation**: Each translation runs in separate process
- **Timeout Protection**: Prevents hanging on problematic files
- **Signal Handling**: Clean shutdown on Ctrl+C

## 📝 Output Format

Translated files follow the naming convention:
- Input: `paper.txt`
- Output: `paper_vi.txt`

Translation includes:
- Vietnamese academic terminology
- Preserved formatting (code, formulas, tables)
- Professional academic tone
- Technical accuracy

## 🚨 Important Notes

1. **Claude Rate Limits**: Respect any rate limits imposed by your Claude executable
2. **File Sizes**: Very large papers may take longer to translate
3. **Network/API**: This system works entirely with local Claude executable
4. **Backup**: Keep backups of original files before translation
5. **Quality**: Review translations for accuracy in critical applications

## 📈 Performance Expectations

Typical performance (varies by system and paper complexity):
- **Small papers** (<10 pages): 1-3 minutes per paper
- **Medium papers** (10-30 pages): 3-8 minutes per paper  
- **Large papers** (>30 pages): 8-15 minutes per paper

With 6 workers: ~10-30 papers per hour depending on size and complexity.