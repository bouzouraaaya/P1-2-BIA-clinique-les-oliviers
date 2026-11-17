# Faux serveur GLPI (simule initSession, creation d'elements, killSession) pour tester glpi_import.py
import json, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
STORE = []; FAIL_ONCE = {"DB-ERP - Base de données ERP"}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.endswith("/initSession"):
            if self.headers.get("Authorization") != "user_token BONJETON": return self._send(401, ["ERROR_GLPI_LOGIN", "bad token"])
            return self._send(200, {"session_token": "SESS123"})
        if self.path.endswith("/killSession"): return self._send(200, [])
        self._send(404, [])
    def do_POST(self):
        if self.headers.get("Session-Token") != "SESS123": return self._send(401, ["ERROR_SESSION_TOKEN_INVALID"])
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n).decode())
        name = body["input"]["name"]
        if name in FAIL_ONCE:
            FAIL_ONCE.discard(name); return self._send(400, ["ERROR_GLPI_ADD", "champ obligatoire manquant"])
        STORE.append((self.path.strip("/").split("/")[-1], name)); self._send(201, {"id": len(STORE), "message": "Item successfully added"})
def serve(port):
    s = HTTPServer(("127.0.0.1", port), H); threading.Thread(target=s.serve_forever, daemon=True).start(); return s
