#!/usr/bin/env python3
"""
MathHumanizer Startup Script
Starts the FastAPI backend server
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("MathHumanizer - AI Text Humanization System")
print("=" * 60)
print()
print("Starting backend server...")
print()

# Set environment variables for faster startup
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HUB_OFFLINE'] = '1'  # Don't try to download models on startup

try:
    import uvicorn
    from humanizer_api import app
    
    print("✓ Backend loaded successfully!")
    print()
    print("Server running at: http://127.0.0.1:8001")
    print("Frontend available at: http://127.0.0.1:8001/")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
    
except KeyboardInterrupt:
    print("\n\nServer stopped by user.")
except Exception as e:
    print(f"Error starting server: {e}")
    print()
    print("Troubleshooting:")
    print("1. Make sure all dependencies are installed:")
    print("   pip install fastapi uvicorn ollama torch transformers nltk PyPDF2 numpy")
    print()
    print("2. Ensure Ollama is running with llama3 model:")
    print("   ollama pull llama3")
    print()
    print("3. Check if port 8001 is already in use")
    sys.exit(1)
