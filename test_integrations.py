import base64,hashlib,hmac,io,json,sqlite3,tempfile,time,uuid
from pathlib import Path
import flowboard_integrations as m

class Handler:
    path='/api/tasks/integration';command='POST'
    def __init__(self,obj):
        b=json.dumps(obj).encode();self.rfile=io.BytesIO(b);self.wfile=io.BytesIO();self.headers={'Content-Length':str(len(b))};self.status=None
    def send_response(self,c):self.status=c
    def send_header(self,*a):pass
    def end_headers(self):pass
    def log_error(self,*a):pass

def call(role,req,nonce=None,bad=False):
    p=json.dumps(dict(req,timestamp=time.time()*1000,nonce=nonce or uuid.uuid4().hex));sig=hmac.new(role.encode(),p.encode(),hashlib.sha256).hexdigest()
    h=Handler({'role':role,'payload':p,'signature':'wrong' if bad else sig});assert m.handle(h);return h.status,json.loads(h.wfile.getvalue())

with tempfile.TemporaryDirectory() as tmp:
    m.DB=Path(tmp)/'test.db';m.CONFIG=Path(tmp)/'config.json';m.CONFIG.write_text(json.dumps({'bot':'bot','archive':'archive','authorized_senders':['owner']}))
    c=sqlite3.connect(m.DB);c.executescript('CREATE TABLE board(id INTEGER PRIMARY KEY,revision INTEGER,payload TEXT);CREATE TABLE board_backups(revision INTEGER PRIMARY KEY,payload TEXT,at REAL);CREATE TABLE files(id TEXT PRIMARY KEY,content BLOB,type TEXT);');m.schema(c)
    doc={'version':3,'projects':[{'id':'P','title':'Test'}],'tasks':[{'id':'T','files':[{'id':'F','name':'test.txt'}]}],'activities':[]}
    c.execute('INSERT INTO board VALUES(1,1,?)',(json.dumps(doc),));c.execute('INSERT INTO files VALUES(?,?,?)',('F',b'hello','text/plain'));c.execute('INSERT INTO file_lifecycle VALUES(?,?)',('F',time.time()-16*86400));c.commit();c.close()
    assert call('bot',{'action':'projects','sender_id':'owner'},bad=True)[0]==403
    assert call('bot',{'action':'projects','sender_id':'stranger'})[0]==403
    nonce=uuid.uuid4().hex;assert call('bot',{'action':'projects','sender_id':'owner'},nonce)[0]==200;assert call('bot',{'action':'projects','sender_id':'owner'},nonce)[0]==403
    req={'action':'note','sender_id':'owner','project_id':'P','event_id':'a'*64,'note':'Note','image':None}
    assert call('bot',req)[1]['duplicate'] is False;assert call('bot',req)[1]['duplicate'] is True
    assert len(call('archive',{'action':'archive_candidates'})[1]['files'])==1
    chunk=call('archive',{'action':'archive_chunk','id':'F','offset':0})[1];assert base64.b64decode(chunk['base64'])==b'hello'
    req={'action':'archive_finalize','id':'F','drive_id':'1234567890abc','size':5,'md5':'bad'};assert call('archive',req)[0]==400
    c=sqlite3.connect(m.DB);assert c.execute('SELECT content FROM files WHERE id="F"').fetchone()[0]==b'hello';c.close()
    req['md5']=hashlib.md5(b'hello').hexdigest();assert call('archive',req)[0]==200
    c=sqlite3.connect(m.DB);assert c.execute('SELECT length(content) FROM files WHERE id="F"').fetchone()[0]==0;doc=json.loads(c.execute('SELECT payload FROM board').fetchone()[0]);assert doc['tasks'][0]['files'][0]['driveId']=='1234567890abc';assert len(doc['tasks'])==2;c.close()
    assert call('archive',{'action':'archive_chunk','id':'F','offset':0})[0]==400
    print('PASS: HMAC, sender authorization, replay, idempotent ingestion, age eligibility, chunks, checksum verification, retained source on failure, finalization and metadata.')
