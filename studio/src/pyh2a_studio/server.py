'''A local HTTP host for the studio. Static files, and one JSON endpoint.

Deliberately the standard library and nothing else. This is a desktop tool for one
person: a threading `HTTPServer` handles it with room to spare, and every dependency
not taken here is one that cannot break a Pyodide build later. All the server does is
decode a request into `(op, payload)`, call `api.dispatch`, and encode the answer —
so the interesting behaviour stays in one testable function that knows nothing about
HTTP.

    POST /api   {"op": "...", "payload": {...}}   ->   {...}
    GET  /*                                        ->   files under `web/`

Run it:

    cd studio
    UV_PYTHON=3.12 uv run --with-editable . python -m pyh2a_studio.server --port 8730
'''

import argparse
import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pyh2a_studio import api

WEB_ROOT = Path(__file__).resolve().parent / 'web'
MAX_BODY = 8 * 1024 * 1024
'''Cap on a posted body. An input file is a few tens of kilobytes; eight megabytes is
generous and still refuses a runaway upload.'''


class Handler(BaseHTTPRequestHandler):
    '''Static files, plus `POST /api`.'''

    server_version = 'PaperPlantStudio/0.1'
    protocol_version = 'HTTP/1.1'

    def do_POST(self):  # noqa: N802  (BaseHTTPRequestHandler's naming)
        if self.path.split('?')[0] != '/api':
            self._send_json(404, {'error': f'no endpoint at {self.path}'})
            return

        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_BODY:
            self._send_json(413, {'error': f'body larger than {MAX_BODY} bytes'})
            return

        try:
            request = json.loads(self.rfile.read(length) or b'{}')
        except json.JSONDecodeError as error:
            self._send_json(400, {'error': f'body is not JSON: {error}'})
            return

        result = api.dispatch(request.get('op', ''), request.get('payload'))
        self._send_json(400 if 'error' in result else 200, result)

    def do_GET(self):  # noqa: N802
        path = self.path.split('?')[0]
        if path in ('/', ''):
            path = '/index.html'

        target = (WEB_ROOT / path.lstrip('/')).resolve()
        if not target.is_file() or WEB_ROOT not in target.parents:
            self._send_json(404, {'error': f'no file at {path}'})
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        # A local tool reloaded constantly during development: never serve a stale
        # sheet from cache, because the resulting confusion costs more than the bytes.
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, payload):
        body = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        '''One line per request, with the op rather than the opaque `/api`.'''

        print(f'{time.strftime("%H:%M:%S")}  {fmt % args}', flush=True)


def main():
    parser = argparse.ArgumentParser(description='Paper Plant Studio')
    parser.add_argument('--port', type=int, default=8730)
    parser.add_argument('--host', default='127.0.0.1')
    arguments = parser.parse_args()

    server = ThreadingHTTPServer((arguments.host, arguments.port), Handler)
    print(f'Paper Plant Studio on http://{arguments.host}:{arguments.port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
