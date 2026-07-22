#!/usr/bin/env python3
import http.server, json, os, time, re, cgi

BASE_DIR = 'D:/else/'
PORT = 6060
STATIC_DIR = 'D:/OneDrive - OmneNest Technologies Pvt Ltd/omnenest/logtracker'

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress logs

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def ok(self, data={}):
        self.send_json({'ok': True, **data})

    def err(self, msg):
        self.send_json({'ok': False, 'error': msg}, 400)

    def safe_name(self, s):
        return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', s)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    """def do_GET(self):
        # Serve static files
        path = self.path.split('?')[0]
        if path == '/' or path == '/index.html':
            filepath = os.path.join(STATIC_DIR, 'index.html')
            ctype = 'text/html'
        elif path == '/style.css':
            filepath = os.path.join(STATIC_DIR, 'style.css')
            ctype = 'text/css'
        else:
            self.send_response(404)
            self.end_headers()
            return

        if not os.path.exists(filepath):
            self.send_response(404)
            self.end_headers()
            return

        with open(filepath, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)"""

    def do_GET(self):
      print(f"GET request: {self.path}")  
      path = self.path.split('?')[0]
      if path == '/' or path == '/index.html':
        filepath = os.path.join(STATIC_DIR, 'index.html')
        ctype = 'text/html'
      elif path == '/style.css':
        filepath = os.path.join(STATIC_DIR, 'style.css')
        ctype = 'text/css'
      elif path == '/favicon.ico':
        self.send_response(204)
        self.end_headers()
        return
      else:
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not found')
        return

      if not os.path.exists(filepath):
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'File not found on disk')
        return

      with open(filepath, 'rb') as f:
            content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

    def do_POST(self):
        content_type = self.headers.get('Content-Type', '')
        body = {}
        files = {}

        if 'application/json' in content_type:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or '{}')

        elif 'multipart/form-data' in content_type:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            for key in form.keys():
                item = form[key]
                if hasattr(item, 'filename') and item.filename:
                    files[key] = item
                else:
                    body[key] = item.value

        action = body.get('action', '')

        # ── GET IP ──────────────────────────────
        if action == 'get_ip':
            ip = self.headers.get('X-Forwarded-For') or \
                 self.headers.get('X-Real-IP') or \
                 self.client_address[0]
            ip = ip.split(',')[0].strip()
            self.ok({'ip': ip})

        # ── CREATE DIR ──────────────────────────
        elif action == 'create_dir':
            name   = self.safe_name(body.get('name', ''))
            caseId = self.safe_name(body.get('caseId', ''))
            if not name or not caseId:
                return self.err('name and caseId required')
            path = os.path.join(BASE_DIR, name, caseId)
            os.makedirs(path, mode=0o755, exist_ok=True)
            self.ok({'path': path})

        # ── UPLOAD FILES ────────────────────────
        elif action == 'upload_file':
            name   = self.safe_name(body.get('name', ''))
            caseId = self.safe_name(body.get('caseId', ''))
            if not name or not caseId:
                return self.err('name and caseId required')
            path = os.path.join(BASE_DIR, name, caseId)
            os.makedirs(path, exist_ok=True)
            if not files:
                return self.err('No files received')
            uploaded, errors = [], []
            for key, item in files.items():
                safe = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(item.filename))
                dest = os.path.join(path, safe)
                if os.path.exists(dest):
                    base, ext = os.path.splitext(safe)
                    safe = f"{base}_{int(time.time())}{ext}"
                    dest = os.path.join(path, safe)
                with open(dest, 'wb') as f:
                    f.write(item.file.read())
                uploaded.append({'name': safe, 'path': dest, 'size': os.path.getsize(dest)})
            self.ok({'uploaded': uploaded, 'errors': errors, 'path': path})

        # ── LIST FILES ──────────────────────────
        elif action == 'list_files':
            name   = self.safe_name(body.get('name', ''))
            caseId = self.safe_name(body.get('caseId', ''))
            if not name or not caseId:
                return self.err('name and caseId required')
            path = os.path.join(BASE_DIR, name, caseId)
            if not os.path.isdir(path):
                return self.ok({'files': [], 'path': path})
            files_list = []
            for f in os.listdir(path):
                fp = os.path.join(path, f)
                files_list.append({
                    'name': f, 'path': fp,
                    'size': os.path.getsize(fp),
                    'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(fp)))
                })
            self.ok({'files': files_list, 'path': path})

        # ── DELETE FILE ─────────────────────────
        elif action == 'delete_file':
            name     = self.safe_name(body.get('name', ''))
            caseId   = self.safe_name(body.get('caseId', ''))
            filename = self.safe_name(body.get('filename', ''))
            if not name or not caseId or not filename:
                return self.err('name, caseId, filename required')
            fp = os.path.join(BASE_DIR, name, caseId, filename)
            if not os.path.exists(fp):
                return self.err('File not found')
            os.remove(fp)
            self.ok({'deleted': filename})

        else:
            self.err('Unknown action: ' + action)

if __name__ == '__main__':
    os.makedirs(BASE_DIR, exist_ok=True)
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Server running on port {PORT}')
    server.serve_forever()