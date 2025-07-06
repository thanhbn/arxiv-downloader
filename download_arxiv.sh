#!/bin/bash

# ArXiv PDF Download Script with Rate Limiting
# This script downloads PDFs from arXiv with proper delays to avoid being flagged as spam/DDoS

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/download_config.sh"

# Show configuration at start
show_config

# Function to display usage
show_usage() {
    echo "Usage: $0 <links_file> <destination_directory>"
    echo ""
    echo "Arguments:"
    echo "  links_file           Path to .txt file containing Arxiv PDF URLs (one per line)"
    echo "  destination_directory Path to directory where PDFs will be downloaded"
    echo ""
    echo "Example:"
    echo "  $0 arxiv_links.txt ./downloaded_papers"
    exit 1
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
if [ $# -ne 2 ]; then
    log_error "Error: Two arguments required"
    show_usage
fi

LINKS_FILE="$1"
DOWNLOAD_DIR="$2"

# Function to extract filename from Arxiv PDF URL
extract_filename() {
    local url=$1
    
    # Extract arxiv ID from URL (e.g., from https://arxiv.org/pdf/1234.5678.pdf extract 1234.5678)
    if [[ $url =~ arxiv\.org/pdf/([^/]+)\.pdf ]]; then
        echo "${BASH_REMATCH[1]}.pdf"
    else
        # Fallback to basename if URL doesn't match expected pattern
        basename "$url"
    fi
}

# Function to download a single PDF with retry logic
download_pdf() {
    local url=$1
    local filename=$(extract_filename "$url")
    local filepath="$DOWNLOAD_DIR/$filename"
    local attempt=1
    
    # Skip if file already exists
    if [ -f "$filepath" ]; then
        log_info "Skipping $filename (already exists)"
        return 0
    fi
    
    log_info "Downloading: $filename to $DOWNLOAD_DIR"
    
    while [ $attempt -le $MAX_RETRIES ]; do
        # Use wget with user-agent and timeout settings
        if wget -q --show-progress \
               --user-agent="$USER_AGENT" \
               --timeout=$TIMEOUT \
               --tries=1 \
               --wait=2 \
               --random-wait \
               -O "$filepath" "$url"; then
            log_success "Downloaded: $filename"
            return 0
        else
            log_warning "Attempt $attempt failed for $filename"
            
            # Remove partial file if it exists
            [ -f "$filepath" ] && rm "$filepath"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_info "Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
            fi
            
            ((attempt++))
        fi
    done
    
    log_error "Failed to download $filename after $MAX_RETRIES attempts"
    return 1
}

# Main function
main() {
    log_info "Starting ArXiv PDF download script"
    
    # Check if links file exists
    if [ ! -f "$LINKS_FILE" ]; then
        log_error "Links file '$LINKS_FILE' not found!"
        exit 1
    fi
    
    # Create download directory if it doesn't exist
    mkdir -p "$DOWNLOAD_DIR"
    
    # Count total links
    total_links=$(wc -l < "$LINKS_FILE")
    log_info "Found $total_links links to download"
    
    # Check daily limit
    if [ $total_links -gt $DAILY_LIMIT ]; then
        log_warning "Warning: Attempting to download $total_links files, which exceeds daily limit of $DAILY_LIMIT"
        log_warning "Consider splitting into smaller batches to avoid being flagged by ArXiv"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Download cancelled by user"
            exit 0
        fi
    fi
    
    # Initialize counters
    downloaded=0
    failed=0
    skipped=0
    current=0
    batch_count=0
    
    # Read links and download
    while IFS= read -r url; do
        # Skip empty lines and comments
        [[ -z "$url" || "$url" =~ ^#.*$ ]] && continue
        
        ((current++))
        
        log_info "Progress: $current/$total_links"
        
        # Download the PDF
        if download_pdf "$url"; then
            filename=$(extract_filename "$url")
            if [ -f "$DOWNLOAD_DIR/$filename" ]; then
                ((downloaded++))
                ((batch_count++))
            else
                ((skipped++))
            fi
        else
            ((failed++))
        fi
        
        # Check if we need a batch break
        if [ $batch_count -ge $BATCH_SIZE ] && [ $current -lt $total_links ]; then
            log_warning "Completed batch of $BATCH_SIZE downloads. Taking extended break of $BATCH_BREAK seconds..."
            sleep $BATCH_BREAK
            batch_count=0
        elif [ $current -lt $total_links ]; then
            # Regular delay between downloads
            random_delay=$((RANDOM % RANDOM_DELAY_MAX + 1))
            total_delay=$((SLEEP_BETWEEN_DOWNLOADS + random_delay))
            log_info "Waiting $total_delay seconds before next download (base: $SLEEP_BETWEEN_DOWNLOADS + random: $random_delay)..."
            sleep $total_delay
        fi
        
    done < "$LINKS_FILE"
    
    # Summary
    echo
    log_info "=== Download Summary ==="
    log_success "Successfully downloaded: $downloaded files"
    log_warning "Skipped (already exist): $skipped files"
    log_error "Failed: $failed files"
    
    # Calculate total size
    if [ -d "$DOWNLOAD_DIR" ]; then
        total_size=$(du -sh "$DOWNLOAD_DIR" | cut -f1)
        log_info "Total size: $total_size"
    fi
    
    log_info "Download complete!"
}

# Check if running as script (not sourced)
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi