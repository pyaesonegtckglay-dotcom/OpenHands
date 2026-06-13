#!/usr/bin/env bash
# ManusAI Backend Build Script
# Used by Render.com deployment
set -e

echo "=== ManusAI Backend Build ==="
echo "Python version: $(python3 --version 2>/dev/null || python --version)"
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing requirements..."
pip install --no-cache-dir -r requirements.txt

echo "=== Build completed successfully ==="
