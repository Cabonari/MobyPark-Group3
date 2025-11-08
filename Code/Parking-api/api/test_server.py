#!/usr/bin/env python3
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"message": "Server is working"}')
    
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"message": "POST received"}')

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8001), TestHandler)
    print("Test server running on http://localhost:8001")
    server.serve_forever()