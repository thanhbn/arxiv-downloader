#!/bin/bash

# Git remote switching script - Round robin toggle
# Usage: ./switch_remote.sh

GITHUB_REMOTE="git@github.com:thanhbn/arxiv-downloader.git"
LOCAL_REMOTE="git@localhost:digital-portal/arxiv-downloader.git"

# Get current remote URL
CURRENT_REMOTE=$(git remote get-url origin)

if [ "$CURRENT_REMOTE" = "$GITHUB_REMOTE" ]; then
    echo "Switching from GitHub to local remote..."
    git remote set-url origin "$LOCAL_REMOTE"
    echo "Remote switched to: $LOCAL_REMOTE"
else
    echo "Switching from local to GitHub remote..."
    git remote set-url origin "$GITHUB_REMOTE"
    echo "Remote switched to: $GITHUB_REMOTE"
fi

echo "Current remote:"
git remote -v
