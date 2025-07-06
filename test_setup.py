#!/usr/bin/env python3
"""Test script to verify the environment setup"""

import sys
import subprocess

def test_imports():
    """Test importing required packages"""
    required_packages = [
        'requests',
        'bs4',
        'tqdm',
        'aiohttp',
        'aiofiles'
    ]
    
    vocabulary_packages = [
        'nltk',
        'sklearn',
        'numpy',
        'PyPDF2',
        'yake'
    ]
    
    print("Testing main packages...")
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package} - not installed")
    
    print("\nTesting vocabulary packages...")
    for package in vocabulary_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package} - not installed")

def test_environment():
    """Test environment configuration"""
    print(f"\nPython version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Virtual environment: {sys.prefix}")

if __name__ == "__main__":
    print("🧪 Testing environment setup...")
    test_imports()
    test_environment()
    print("\n✅ Environment test completed!")
