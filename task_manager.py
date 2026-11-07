"""Private task API, isolated from the marketplace database."""
import datetime
import hashlib
import hmac
import json
from flowboard_integrations import handle as handle_integration, schema as integration_schema, uploaded, archive_info
import secrets
import sqlite3
import time
import re
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

BASE = Path('/var/www/alltool.pro/data')
DB = BASE / 'tasks.db'
CONFIG = BASE / 'tasks_auth.json'

def digest(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 250000).hex()

def connect():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.executescript('''
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, expires REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL, at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS auth(id INTEGER PRIMARY KEY CHECK(id=1), salt TEXT NOT NULL, hash TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS board(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS board_backups(revision INTEGER PRIMARY KEY, payload TEXT NOT NULL, at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, content BLOB NOT NULL, type TEXT NOT NULL);
    ''')
    integration_schema(c)
    if not c.execute('SELECT 1 FROM auth').fetchone():
        cfg = json.loads(CONFIG.read_text())
        c.execute('INSERT INTO auth VALUES(1,?,?)', (cfg['salt'], cfg['hash']))
        c.commit()
    return c

def handle(h):
    if handle_integration(h): return True
    path = urlparse(h.path).path
    if not (path == '/api/tasks' or path.startswith('/api/tasks/')):
        return False
    def reply(code, data, cookie=None):
        raw = json.dumps(data, ensure_ascii=False).encode()
        h.send_response(code)
        h.send_header('Content-Type','application/json; charset=utf-8')
        h.send_header('Content-Length',str(len(raw)))
        h.send_header('Cache-Control','no-store')
        h.send_header('X-Content-Type-Options','nosniff')
        if cookie: h.send_header('Set-Cookie',cookie)
        h.end_headers()
        h.wfile.write(raw)
    try:
        body = {}
        if h.command == 'POST':
            origin = h.headers.get('Origin','')
            if not origin or urlparse(origin).scheme != 'https' or urlparse(origin).netloc != h.headers.get('Host'):
                reply(403, {'error':'Nguồn yêu cầu không hợp lệ.'}); return True
            length = int(h.headers.get('Content-Length','0'))
            limit = 35*1024*1024 if path.startswith('/api/tasks/file/') else (4*1024*1024 if path == '/api/tasks/state' else 24000)
            if length < 0 or length > limit:
                reply(413, {'error':'Dữ liệu quá lớn.'}); return True
            raw = h.rfile.read(length)
            body = {} if path.startswith('/api/tasks/file/') else json.loads(raw or b'{}')
            if not isinstance(body,dict): raise ValueError()
        with connect() as c:
            now = time.time()
            c.execute('DELETE FROM sessions WHERE expires < ?', (now,))
            c.execute('DELETE FROM attempts WHERE at < ?', (now-900,))
            cookies = SimpleCookie(); cookies.load(h.headers.get('Cookie',''))
            token = cookies['gcm_session'].value if 'gcm_session' in cookies else ''
            key = hashlib.sha256(token.encode()).hexdigest()
            session = c.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?', (key,now)).fetchone()
            def setcookie(value, age):
                return f'gcm_session={value}; Path=/api/tasks; Max-Age={age}; Secure; HttpOnly; SameSite=Strict'
            if path == '/api/tasks/login' and h.command == 'POST':
                ip = h.client_address[0]
                # Nginx supplies this header from the actual peer address.
                ip = h.headers.get('X-Real-IP',ip)
                if c.execute('SELECT count(*) FROM attempts WHERE ip=?',(ip,)).fetchone()[0] >= 8:
                    reply(429,{'error':'Thử lại sau 15 phút.'}); return True
                auth = c.execute('SELECT * FROM auth WHERE id=1').fetchone()
                if body.get('username') != 'admin' or not hmac.compare_digest(digest(str(body.get('password','')),auth['salt']),auth['hash']):
                    c.execute('INSERT INTO attempts VALUES(?,?)',(ip,now))
                    reply(401,{'error':'Sai tài khoản hoặc mật khẩu.'}); return True
                token = secrets.token_urlsafe(32)
                c.execute('INSERT INTO sessions VALUES(?,?)',(hashlib.sha256(token.encode()).hexdigest(),now+43200))
                c.execute('DELETE FROM attempts WHERE ip=?',(ip,))
                reply(200,{'ok':True},setcookie(token,43200)); return True
            if not session:
                reply(401,{'error':'Vui lòng đăng nhập.'}); return True
            if path == '/api/tasks/logout' and h.command == 'POST':
                c.execute('DELETE FROM sessions WHERE token=?',(key,))
                reply(200,{'ok':True},setcookie('',0)); return True
            if path == '/api/tasks/password' and h.command == 'POST':
                auth = c.execute('SELECT * FROM auth WHERE id=1').fetchone()
                new = str(body.get('new_password',''))
                if not hmac.compare_digest(digest(str(body.get('old_password','')),auth['salt']),auth['hash']):
                    reply(403,{'error':'Mật khẩu hiện tại không đúng.'}); return True
                if len(new)<12 or len(new)>200:
                    reply(400,{'error':'Mật khẩu mới cần 12–200 ký tự.'}); return True
                salt = secrets.token_hex(16)
                c.execute('UPDATE auth SET salt=?,hash=? WHERE id=1',(salt,digest(new,salt)))
                c.execute('DELETE FROM sessions')
                reply(200,{'ok':True},setcookie('',0)); return True
            if path.startswith('/api/tasks/file/'):
                fid = path.rsplit('/',1)[-1]
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',fid): raise ValueError()
                if h.command == 'GET':
                    archived = archive_info(c, fid)
                    if archived:
                        h.send_response(302); h.send_header('Location',archived['url']); h.send_header('Cache-Control','no-store'); h.send_header('Content-Length','0'); h.end_headers(); return True
                    row = c.execute('SELECT content,type FROM files WHERE id=?',(fid,)).fetchone()
                    if not row:
                        reply(404,{'error':'Không tìm thấy tệp.'}); return True
                    h.send_response(200)
                    h.send_header('Content-Type','application/octet-stream')
                    h.send_header('Content-Disposition','attachment')
                    h.send_header('Content-Length',str(len(row['content'])))
                    h.send_header('Cache-Control','no-store')
                    h.send_header('X-Content-Type-Options','nosniff')
                    h.end_headers(); h.wfile.write(row['content']); return True
                if h.command == 'POST':
                    # Keep blobs for prior snapshots; removing an attachment changes its metadata.
                    c.execute('INSERT INTO files VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET content=excluded.content,type=excluded.type',(fid,raw,'application/octet-stream'))
                    uploaded(c, fid)
                    reply(200,{'ok':True}); return True
            if path == '/api/tasks/state':
                row = c.execute('SELECT revision,payload FROM board WHERE id=1').fetchone()
                revision = row['revision'] if row else 0
                if h.command == 'GET':
                    reply(200,{'revision':revision,'data':json.loads(row['payload']) if row else None}); return True
                if h.command == 'POST':
                    doc = body.get('data')
                    keys = ('people','projects','tasks','handoffs','invoices','times','activities')
                    if not isinstance(doc,dict) or doc.get('version') != 3 or not all(isinstance(doc.get(k),list) for k in keys): raise ValueError()
                    for k in keys:
                        if len(doc[k])>20000 or not all(isinstance(v,dict) for v in doc[k]): raise ValueError()
                    encoded = json.dumps(doc,ensure_ascii=False)
                    expected = int(body.get('revision',-1))
                    # Acquire the writer lock before checking revision again.
                    c.execute('INSERT OR IGNORE INTO board VALUES(1,0,?)',('{}',))
                    current = c.execute('SELECT revision,payload FROM board WHERE id=1').fetchone()
                    if current['revision'] != expected:
                        reply(409,{'error':'Dữ liệu đã thay đổi trên thiết bị khác. Hãy tải lại trước khi sửa tiếp.'}); return True
                    if current['revision']:
                        c.execute('INSERT OR IGNORE INTO board_backups VALUES(?,?,?)',(current['revision'],current['payload'],now))
                    c.execute('UPDATE board SET revision=revision+1,payload=? WHERE id=1',(encoded,))
                    c.execute('DELETE FROM board_backups WHERE revision < ?',(current['revision']-29,))
                    reply(200,{'ok':True,'revision':current['revision']+1}); return True
            reply(404,{'error':'Không tìm thấy chức năng.'})
    except (ValueError, TypeError, KeyError):
        reply(400,{'error':'Dữ liệu không hợp lệ.'})
    except Exception:
        h.log_error('Task API failed')
        reply(500,{'error':'Không thể xử lý yêu cầu. Vui lòng thử lại.'})
    return True
