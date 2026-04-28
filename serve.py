#!/usr/bin/env python3
"""Local dev server for the claim form generator.

Serves files from this directory and accepts POSTs to /save-field-map
so the calibrator can write field-map.json directly into the project.

Run:  python3 serve.py
"""
import http.server
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PORT = 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_POST(self):
        if self.path == '/save-field-map':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                json.loads(body)
            except Exception as e:
                self._respond(400, {'ok': False, 'error': f'invalid JSON: {e}'})
                return
            (ROOT / 'field-map.json').write_bytes(body)
            self._respond(200, {'ok': True, 'bytes': len(body)})
        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    os.chdir(ROOT)
    print(f'Serving {ROOT} at http://localhost:{PORT}/')
    print(f'  - calibrate: http://localhost:{PORT}/calibrate.html')
    print(f'  - filler:    http://localhost:{PORT}/filler.html')
    try:
        http.server.ThreadingHTTPServer(('localhost', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
