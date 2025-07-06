# ArXiv Downloader

This tool downloads arXiv papers from a collection with proper rate limiting to avoid being flagged as spam or DDoS.

## Files Created

- `arxiv_links.txt` - Contains all 81 PDF links from the multimodal collection
- `download_arxiv.sh` - Smart download script with rate limiting
- `multimodal_papers/` - Directory containing downloaded PDFs

## Usage

### Basic Usage
```bash
./download_arxiv.sh
```

### Custom Configuration
```bash
# Use different links file and output directory
LINKS_FILE=my_links.txt DOWNLOAD_DIR=my_papers ./download_arxiv.sh
```

## Script Features

- **Rate Limiting**: 3-second delay between downloads to be respectful to arXiv servers
- **Error Handling**: Automatic retry (up to 3 attempts) for failed downloads
- **Skip Existing**: Won't re-download files that already exist
- **Progress Tracking**: Shows download progress and final summary
- **Colored Output**: Clear status messages with color coding
- **Timeout Protection**: 30-second timeout per download attempt

## Configuration Options

You can modify these variables at the top of `download_arxiv.sh`:

- `SLEEP_BETWEEN_DOWNLOADS=3` - Seconds to wait between downloads
- `MAX_RETRIES=3` - Number of retry attempts for failed downloads  
- `RETRY_DELAY=10` - Seconds to wait before retrying

## Safety Features

- Uses proper User-Agent to identify as research bot
- Implements respectful delays to avoid overwhelming arXiv servers
- Handles network errors gracefully with retry logic
- Provides detailed logging of all operations

## Example Output

```
[INFO] Starting ArXiv PDF download script
[INFO] Found 81 links to download
[INFO] Progress: 1/81
[INFO] Downloading: 2310.16045.pdf
[SUCCESS] Downloaded: 2310.16045.pdf
[INFO] Waiting 3 seconds before next download...
...
[INFO] === Download Summary ===
[SUCCESS] Successfully downloaded: 79 files
[WARNING] Skipped (already exist): 2 files  
[ERROR] Failed: 0 files
[INFO] Total size: 661M
[INFO] Download complete!
```

## Notes

- The original wget command downloaded all 81 files successfully
- This improved script adds safety features and better user experience
- Total collection size is approximately 661MB
- All papers are from the multimodal AI research domain
