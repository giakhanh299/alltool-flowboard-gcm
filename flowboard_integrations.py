"""Signed bot ingestion and verified Drive archival. No browser sessions accepted."""
import base64
import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path

BASE = Path('/var/www/alltool.pro/data')
DB = BASE / 'tasks.db'
CONFIG = BASE / 'flowboard_integrations.json'
FOLDER = '1_HIIAykbr-mBgvOptDHddSFV0K2W0Gs3'

def schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS integration_nonces(nonce TEXT PRIMARY KEY, at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS ingestion_events(event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS file_lifecycle(id TEXT PRIMARY KEY, modified REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS file_archives(id TEXT PRIMARY KEY, drive_id TEXT NOT NULL, url TEXT NOT NULL, size INTEGER NOT NULL, md5 TEXT NOT NULL, archived REAL NOT NULL);
    ''')

def uploaded(c, fid):
    c.execute('INSERT INTO file_lifecycle VALUES(?,?) ON CONFLICT(id) DO UPDATE SET modified=excluded.modified',(fid,time.time()))
    c.execute('DELETE FROM file_archives WHERE id=?',(fid,))

def archive_info(c, fid):
    return c.execute('SELECT url FROM file_archives WHERE id=?',(fid,)).fetchone()

def handle(h):
    if h.path != '/api/tasks/integration': return False
    code=200; out={}; compact=False; c=None
    try:
        if h.command!='POST': raise ValueError('method_not_allowed')
        length=int(h.headers.get('Content-Length','0'))
        if not 0<length<3*1024*1024: raise ValueError('invalid_size')
        envelope=json.loads(h.rfile.read(length))
        payload=envelope['payload']; role=envelope.get('role')
        cfg=json.loads(CONFIG.read_text())
        if role not in ('bot','archive'): raise PermissionError()
        if not isinstance(payload,str) or not hmac.compare_digest(hmac.new(cfg[role].encode(),payload.encode(),hashlib.sha256).hexdigest(),str(envelope.get('signature',''))): raise PermissionError()
        req=json.loads(payload); now=time.time()
        if abs(now*1000-float(req.get('timestamp',0)))>300000: raise PermissionError()
        nonce=req.get('nonce','')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{16,100}',nonce): raise PermissionError()
        c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row
        schema(c)
        with c:
            c.execute('DELETE FROM integration_nonces WHERE at<?',(now-600,))
            try:c.execute('INSERT INTO integration_nonces VALUES(?,?)',(role+nonce,now))
            except sqlite3.IntegrityError: raise PermissionError()
            action=req.get('action')
            row=c.execute('SELECT revision,payload FROM board WHERE id=1').fetchone()
            doc=json.loads(row['payload']) if row else None
            if not doc: raise ValueError('board_not_initialized')
            if role=='bot':
                if str(req.get('sender_id')) not in cfg.get('authorized_senders',[]): raise PermissionError()
                if action=='projects':
                    out={'ok':True,'projects':[{'id':p['id'],'title':p.get('title') or p.get('name','')} for p in doc['projects']]}
                elif action=='note':
                    pid=req.get('project_id');event=req.get('event_id');note=str(req.get('note','')).strip()
                    if not any(p['id']==pid for p in doc['projects']) or not re.fullmatch(r'[a-f0-9]{64}',str(event)) or len(note)>12000 or not note: raise ValueError('invalid_note')
                    old=c.execute('SELECT task_id FROM ingestion_events WHERE event_id=?',(event,)).fetchone()
                    if old:out={'ok':True,'task_id':old[0],'duplicate':True}
                    else:
                        tid='ZALO-'+event[:20];stamp=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now))
                        files=[];image=req.get('image')
                        if image:
                            content=base64.b64decode(image['base64'],validate=True)
                            if len(content)>1800000: raise ValueError('image_too_large')
                            fid='ZALOFILE-'+event[:20];c.execute('INSERT INTO files VALUES(?,?,?)',(fid,content,'application/octet-stream'));uploaded(c,fid)
                            files=[{'id':fid,'name':str(image.get('name','anh-zalo'))[:200],'size':len(content),'type':str(image.get('type','application/octet-stream'))[:100],'added':stamp[:10]}]
                        doc['tasks'].append({'id':tid,'projectId':pid,'title':note.split('\n')[0][:160],'description':note,'person':'','status':'todo','phase':'intake','priority':'normal','due':'','start':'','depends':[],'check':[],'files':files,'history':[],'source':'zalo','sourceEvent':event,'created':stamp})
                        doc['activities'].insert(0,{'at':stamp,'text':'Nhận ghi chú/tài liệu Zalo vào dự án','projectId':pid})
                        c.execute('INSERT INTO ingestion_events VALUES(?,?)',(event,tid));save_board(c,row,doc,now)
                        out={'ok':True,'task_id':tid,'duplicate':False}
                else: raise ValueError('invalid_action')
            elif action=='archive_candidates':
                c.execute('INSERT OR IGNORE INTO file_lifecycle SELECT id,? FROM files',(now,))
                refs={f['id']:f for t in doc['tasks'] for f in t.get('files',[]) if f.get('id')}
                rows=c.execute('SELECT f.id,length(f.content) size,l.modified FROM files f JOIN file_lifecycle l ON f.id=l.id LEFT JOIN file_archives a ON a.id=f.id WHERE l.modified<? AND a.id IS NULL AND length(f.content)>0 ORDER BY l.modified LIMIT 20',(now-15*86400,)).fetchall()
                out={'ok':True,'folder_id':FOLDER,'files':[{'id':r['id'],'name':refs[r['id']].get('name',r['id']),'size':r['size'],'modified':r['modified']} for r in rows if r['id'] in refs]}
            elif action in ('archive_chunk','archive_finalize'):
                fid=req.get('id');r=c.execute('SELECT f.content,l.modified FROM files f JOIN file_lifecycle l ON f.id=l.id LEFT JOIN file_archives a ON a.id=f.id WHERE f.id=? AND a.id IS NULL',(fid,)).fetchone()
                if not r or r['modified']>=now-15*86400:raise ValueError('file_not_eligible')
                content=r['content'];md5=hashlib.md5(content).hexdigest()
                if action=='archive_chunk':
                    offset=int(req.get('offset',0))
                    if offset<0 or offset>len(content):raise ValueError('invalid_offset')
                    part=content[offset:offset+512*1024]
                    out={'ok':True,'offset':offset,'size':len(content),'md5':md5,'base64':base64.b64encode(part).decode()}
                else:
                    drive_id=str(req.get('drive_id',''))
                    if not re.fullmatch(r'[A-Za-z0-9_-]{10,150}',drive_id) or req.get('size')!=len(content) or req.get('md5')!=md5: raise ValueError('verification_mismatch')
                    url='https://drive.google.com/file/d/'+drive_id+'/view'
                    c.execute('INSERT INTO file_archives VALUES(?,?,?,?,?,?)',(fid,drive_id,url,len(content),md5,now))
                    for task in doc['tasks']:
                        for f in task.get('files',[]):
                            if f.get('id')==fid:f.update({'driveUrl':url,'driveId':drive_id,'archivedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now))})
                    save_board(c,row,doc,now)
                    c.execute('UPDATE files SET content=? WHERE id=?',(b'',fid));compact=True
                    out={'ok':True,'id':fid,'drive_url':url,'released_bytes':len(content)}
            else:raise ValueError('invalid_action')
        if compact:c.execute('VACUUM')
    except PermissionError:code=403;out={'ok':False,'error':'forbidden'}
    except (ValueError,KeyError,TypeError):code=400;out={'ok':False,'error':'invalid_request'}
    except Exception:h.log_error('Integration request failed');code=500;out={'ok':False,'error':'integration_error'}
    finally:
        if c is not None:c.close()
    raw=json.dumps(out,ensure_ascii=False).encode();h.send_response(code);h.send_header('Content-Type','application/json; charset=utf-8');h.send_header('Cache-Control','no-store');h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)
    return True

def save_board(c,row,doc,now):
    c.execute('INSERT OR IGNORE INTO board_backups VALUES(?,?,?)',(row['revision'],row['payload'],now))
    c.execute('UPDATE board SET revision=revision+1,payload=? WHERE id=1',(json.dumps(doc,ensure_ascii=False),))
    c.execute('DELETE FROM board_backups WHERE revision<?',(row['revision']-29,))
