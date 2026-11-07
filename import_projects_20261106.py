import sqlite3,json,time,datetime
from pathlib import Path
p=Path('/var/www/alltool.pro/data');c=sqlite3.connect(p/'tasks.db',timeout=20)
b=sqlite3.connect(p/('tasks_before_projects_'+str(int(time.time()))+'.db'));c.backup(b);b.close()
c.execute('BEGIN IMMEDIATE')
r=c.execute('select revision,payload from board where id=1').fetchone();d=json.loads(r[1]);report=json.loads((p/'project_report_20261106.json').read_text());staff=json.loads((p/'project_staff_20261106.json').read_text());stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
for person in staff:
 if not any(x['id']==person['id'] for x in d['people']):d['people'].append({'id':person['id'],'name':person['name'],'role':'Nhân sự xưởng','color':'blue','initial':''.join(s[0] for s in person['name'].split()[-2:])})
added=0
for x in report['reports']:
 if any(z['id']==x['id'] for z in d['projects']):continue
 d['projects'].append(dict(x,customer='',due='',contract=0,contractKnown=False,priority='normal',created='',transport=0,other=0,archived=False,importedAt=stamp));added+=1
 tid=x['id']+'-REVIEW'
 d['tasks'].append({'id':tid,'projectId':x['id'],'title':'Đối chiếu hồ sơ và cập nhật tiến độ thực tế','person':'','phase':'intake','status':'todo','priority':'normal','due':'','start':'','depends':[],'check':[],'files':[],'history':[],'description':x['note']+'\nNguồn: '+x['sourceFolder']+'\nNgày đối chiếu: '+x['evidenceDate']+'. Chưa phải ngày khởi công hay nghiệm thu.'})
if added:
 content=(p/'project_report_20261106.xlsx').read_bytes();fid='REPORT-20261106'
 c.execute('INSERT OR IGNORE INTO files VALUES(?,?,?)',(fid,content,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
 for t in d['tasks']:
  if t['id']=='GCM-HN-REVIEW' and not any(f['id']==fid for f in t['files']):t['files'].append({'id':fid,'name':'Thong_ke_du_an_06-09_den_06-11-2026.xlsx','size':len(content),'type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','added':stamp[:10]})
 d['activities'].insert(0,{'at':stamp,'text':'Đồng bộ '+str(added)+' nhóm hồ sơ từ ổ D và lịch sử trò chuyện; chưa xác nhận tiến độ sản xuất.','projectId':''})
 c.execute('INSERT OR IGNORE INTO board_backups VALUES(?,?,?)',(r[0],r[1],time.time()))
 c.execute('UPDATE board SET revision=revision+1,payload=? WHERE id=1',(json.dumps(d,ensure_ascii=False),))
c.commit();print(json.dumps({'added':added,'projects':len(d['projects']),'staff':len(d['people'])}));c.close()
