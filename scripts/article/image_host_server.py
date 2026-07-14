#!/usr/bin/env python3
"""
Simple HTTP server to host images locally for kie.ai API.
Provides URLs for images that can be used with kie.ai API.
"""

import http.server
import socketserver
import os
from pathlib import Path
import urllib.parse
import threading
import time

from _paths import PROJECT_ROOT

_IMAGES_DIR = PROJECT_ROOT / "lab bsk" / "selected_screenshots"

class ImageHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve images with CORS headers."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_IMAGES_DIR), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_GET(self):
        # Serve files from the images directory
        return super().do_GET()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_server(port=8000, directory=None):
    """Start the image hosting server."""
    if directory:
        os.chdir(directory)
    
    handler = ImageHandler
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), handler)
    
    print(f"Image hosting server started on http://localhost:{port}")
    print(f"Serving directory: {_IMAGES_DIR}")
    print(f"\nExample URLs:")
    print(f"  http://localhost:{port}/Lab13_01__page_0_Picture_0.jpeg")
    print(f"  http://localhost:{port}/Lab14_01__page_0_Picture_2.jpeg")
    print(f"\nPress Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.shutdown()

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    start_server(port=port)

