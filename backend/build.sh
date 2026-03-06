#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Download FFmpeg static binary if it's not already there
if [ ! -d "ffmpeg" ]; then
  echo "Downloading FFmpeg static binary..."
  mkdir -p ffmpeg
  # Using the reliable static build from johnvansickle.com
  curl -L https://johnvansickle.com | tar -xJ --strip-components=1 -C ffmpeg
fi

# 3. Add FFmpeg to the current PATH so the build step can see it
export PATH=$PATH:$(pwd)/ffmpeg
