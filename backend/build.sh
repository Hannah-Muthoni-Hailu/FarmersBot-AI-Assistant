#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r backend/requirements.txt

# Download FFmpeg static binary
if [ ! -d "ffmpeg" ]; then
  echo "Downloading FFmpeg static binary..."
  mkdir -p ffmpeg
  
  # Corrected direct link to the latest stable release
  curl -L https://johnvansickle.com -o ffmpeg.tar.xz
  
  # Extract the saved file
  tar -xJf ffmpeg.tar.xz --strip-components=1 -C ffmpeg
  
  # Cleanup the archive to save space
  rm ffmpeg.tar.xz
fi

# Add FFmpeg to the current PATH so the build step can see it
export PATH=$PATH:$(pwd)/ffmpeg
