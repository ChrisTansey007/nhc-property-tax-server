#!/usr/bin/env python
"""
Run both MCP server and documentation server
"""

import subprocess
import sys
import os
import signal
import time

def run_servers():
    """Run both servers in parallel"""
    print("Starting New Hanover County Property Tax Search servers...")
    print("-" * 60)
    
    # Start MCP server
    mcp_process = subprocess.Popen(
        [sys.executable, "nhc_property_tax_server.py"],
        env=os.environ.copy()
    )
    print("✅ MCP Server started on http://localhost:8000/mcp")
    
    # Give MCP server time to start
    time.sleep(2)
    
    # Start documentation server
    docs_process = subprocess.Popen(
        [sys.executable, "docs_server.py"],
        env=os.environ.copy()
    )
    print("✅ Documentation server started on http://localhost:8001")
    print("-" * 60)
    print("📚 API Documentation: http://localhost:8001/docs")
    print("📖 ReDoc: http://localhost:8001/redoc")
    print("🔍 OpenAPI Spec: http://localhost:8001/openapi.json")
    print("-" * 60)
    print("Press Ctrl+C to stop both servers...")
    
    def signal_handler(sig, frame):
        print("\n\nShutting down servers...")
        mcp_process.terminate()
        docs_process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Wait for both processes
        mcp_process.wait()
        docs_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    run_servers()