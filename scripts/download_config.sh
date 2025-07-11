#!/bin/bash

# ArXiv Download Configuration
# This file contains rate limiting and safety settings to avoid being blocked by ArXiv

# === Rate Limiting Settings ===
export SLEEP_BETWEEN_DOWNLOADS=5    # Base seconds between downloads
export RANDOM_DELAY_MAX=3           # Additional random delay (1-3 seconds)
export MAX_RETRIES=3                 # Maximum retry attempts per file
export RETRY_DELAY=15                # Seconds to wait before retry
export TIMEOUT=45                    # Download timeout in seconds

# === Batch Processing Settings ===
export BATCH_SIZE=10                 # Number of files to download before long break
export BATCH_BREAK=30                # Seconds to wait between batches
export DAILY_LIMIT=500               # Maximum files per day (safety limit)

# === Conservative Mode ===
export CONSERVATIVE_MODE=true        # Enable extra-conservative settings
export CONSERVATIVE_MULTIPLIER=2     # Multiply all delays by this factor when enabled

# === User Agent ===
export USER_AGENT="Mozilla/5.0 (compatible; academic-research-bot/1.0; +https://github.com/academic-research)"

# Apply conservative mode if enabled
if [ "$CONSERVATIVE_MODE" = true ]; then
    export SLEEP_BETWEEN_DOWNLOADS=$((SLEEP_BETWEEN_DOWNLOADS * CONSERVATIVE_MULTIPLIER))
    export RETRY_DELAY=$((RETRY_DELAY * CONSERVATIVE_MULTIPLIER))
    export BATCH_BREAK=$((BATCH_BREAK * CONSERVATIVE_MULTIPLIER))
fi

# Display current configuration
show_config() {
    echo "📋 ArXiv Download Configuration:"
    echo "  🕒 Sleep between downloads: ${SLEEP_BETWEEN_DOWNLOADS}s + random 1-${RANDOM_DELAY_MAX}s"
    echo "  🔄 Max retries: $MAX_RETRIES"
    echo "  ⏱️  Retry delay: ${RETRY_DELAY}s"
    echo "  ⏰ Download timeout: ${TIMEOUT}s"
    echo "  📦 Batch size: $BATCH_SIZE files"
    echo "  🛑 Batch break: ${BATCH_BREAK}s"
    echo "  📊 Daily limit: $DAILY_LIMIT files"
    echo "  🔒 Conservative mode: $CONSERVATIVE_MODE"
    if [ "$CONSERVATIVE_MODE" = true ]; then
        echo "  📈 Conservative multiplier: ${CONSERVATIVE_MULTIPLIER}x"
    fi
}