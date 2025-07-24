#!/bin/bash

set -e

# Parse command line arguments
TARGET="$1"  # Optional target parameter

# Validate target if provided
if [[ -n "$TARGET" ]] && [[ ! "$TARGET" =~ ^(stable|latest|[0-9]+\.[0-9]+\.[0-9]+(-[^[:space:]]+)?)$ ]]; then
    echo "Usage: $0 [stable|latest|VERSION]" >&2
    exit 1
fi

GCS_BUCKET="https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases"
DOWNLOAD_DIR="$HOME/.claude/downloads"

for cmd in curl jq; do
    if ! command -v $cmd >/dev/null 2>&1; then
        echo "$cmd is required but not installed" >&2
        exit 1
    fi
done

# Detect platform
case "$(uname -s)" in
    Darwin) os="darwin" ;;
    Linux) os="linux" ;;
    *) echo "Windows is not supported" >&2; exit 1 ;;
esac

case "$(uname -m)" in
    x86_64|amd64) arch="x64" ;;
    arm64|aarch64) arch="arm64" ;;
    *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac

platform="${os}-${arch}"
mkdir -p "$DOWNLOAD_DIR"

# Always download stable version (which has the most up-to-date installer)
version=$(curl -fsSL "$GCS_BUCKET/stable")

checksum=$(curl -fsSL "$GCS_BUCKET/$version/manifest.json" | jq -r ".platforms[\"$platform\"].checksum // empty")

if [ -z "$checksum" ]; then
    echo "Platform $platform not found in manifest" >&2
    exit 1
fi

# Download and verify
binary_path="$DOWNLOAD_DIR/claude-$version-$platform"
if ! curl -fsSL -o "$binary_path" "$GCS_BUCKET/$version/$platform/claude"; then
    echo "Download failed" >&2
    rm -f "$binary_path"
    exit 1
fi

# Pick the right checksum tool
if [ "$os" = "darwin" ]; then
    actual=$(shasum -a 256 "$binary_path" | cut -d' ' -f1)
else
    actual=$(sha256sum "$binary_path" | cut -d' ' -f1)
fi

if [ "$actual" != "$checksum" ]; then
    echo "Checksum verification failed" >&2
    rm -f "$binary_path"
    exit 1
fi

chmod +x "$binary_path"

# Run claude install to set up launcher and shell integration
echo "Setting up Claude Code..."
"$binary_path" install ${TARGET:+"$TARGET"}

# Clean up downloaded file
rm -f "$binary_path"

echo ""
echo "✅ Installation complete!"
echo ""
