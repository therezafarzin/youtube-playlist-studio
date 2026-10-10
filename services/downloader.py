from __future__ import annotations
import json,logging,os,re,shutil,signal,subprocess,threading,uuid
from config import DOWNLOADS
from database.db import connect,now,upsert_history
from .cookies import args as cookie_args
from .media import find,probe,quarantine
from .telegram import send
log=logging.getLogger(__name__)
class QueueEngine:
 def __init__(self):
  self.wake=threading.Event(); self.process=None; self.active_id=None; self.lock=threading.RLock()
  self.wake.set(); threading.Thread(target=self.loop,name="download-worker",daemon=True).start()
 def enqueue(self,items,settings):
  added=0
  with connect() as c:
   order=c.execute("SELECT COALESCE(MAX(queue_order),0) FROM jobs").fetchone()[0]
   for x in sorted(items,key=lambda z:int(z.get("position",z.get("index",0)) or 0)):
    vid=str(x.get("video_id") or x.get("id") or "")
    if not vid or c.execute("SELECT 1 FROM jobs WHERE video_id=? AND status IN ('queued','downloading','processing','validating','uploading')",(vid,)).fetchone(): continue
    order+=1;jid=uuid.uuid4().hex
    c.execute("INSERT INTO jobs(job_id,video_id,playlist_id,title,video_url,position,settings_json,status,message,queue_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(jid,vid,x.get("playlist_id"),x.get("title") or vid,x.get("video_url") or x.get("url") or f"https://www.youtube.com/watch?v={vid}",int(x.get("position",x.get("index",1)) or 1),json.dumps(settings),"queued","در صف",order,now(),now()));added+=1
  self.wake.set();return added
 def update(self,jid,**kw):
  allowed={"status","progress","speed","eta","message","error","path","cancel_requested"}; cols={k:v for k,v in kw.items() if k in allowed};cols["updated_at"]=now();sets=','.join(f"{k}=?" for k in cols)
  with connect() as c:c.execute(f"UPDATE jobs SET {sets} WHERE job_id=?",(*cols.values(),jid))
 def next_job(self):
  with connect() as c:return c.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY queue_order,created_at LIMIT 1").fetchone()
 def loop(self):
  while True:
   row=self.next_job()
   if not row:self.wake.clear();self.wake.wait(timeout=2);continue
   try:self.run(dict(row))
   except Exception as e:log.exception("job failed");self.update(row["job_id"],status="failed",error=str(e),message="دانلود ناموفق بود")
 def run(self,j):
  jid=j["job_id"]; settings=json.loads(j["settings_json"])
  old=find(j["video_id"])
  if old and not settings.get("redownload"):
   try:return self.finish(j,old,probe(old),settings)
   except Exception:quarantine(old)
  quality=str(settings.get("quality","720"));height="" if quality=="best" else f"[height<={quality}]";fmt=f"bv{height}[vcodec^=avc1]+ba[acodec^=mp4a]/bv{height}+ba/b[acodec!=none][vcodec!=none]";out=str(DOWNLOADS/f"{j['position']:03d} - %(title)s [%(id)s].%(ext)s")
  cmd=[shutil.which("yt-dlp") or "yt-dlp",*cookie_args(),"--force-ipv4","--socket-timeout","60","--retries","5","--fragment-retries","5","--extractor-args","youtube:player_client=web","--no-playlist","--newline","--continue","--merge-output-format","mp4","--remux-video","mp4","--format",fmt,"--output",out,"--progress-template","download:PROGRESS|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",j["video_url"]]
  self.update(jid,status="downloading",message="دانلود Video + Audio",error="")
  with self.lock:self.active_id=jid;self.process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
  tail=[]
  for line in self.process.stdout or []:
   tail.append(line);tail=tail[-60:];m=re.search(r"PROGRESS\|([^|]+)\|([^|]+)\|(.+)",line)
   if m:self.update(jid,progress=float(re.sub(r"[^0-9.]","",m.group(1)) or 0),speed=m.group(2).strip(),eta=m.group(3).strip())
   with connect() as c: cancelled=c.execute("SELECT cancel_requested FROM jobs WHERE job_id=?",(jid,)).fetchone()[0]
   if cancelled:
    os.killpg(self.process.pid,signal.SIGTERM);self.update(jid,status="canceled",message="لغو شد");self.clear_active();return
  rc=self.process.wait();self.clear_active();path=find(j["video_id"]);self.update(jid,status="validating",message="بررسی Audio و Video فایل")
  try:info=probe(path) if path else (_ for _ in ()).throw(ValueError("فایل نهایی MP4 پیدا نشد"))
  except Exception as e:
   if path:quarantine(path)
   output="".join(tail)[-1200:]
   if "Sign in to confirm you’re not a bot" in output or "HTTP Error 403" in output:raise RuntimeError("YouTube دسترسی دانلود را رد کرد (403 / تأیید ورود). روی «بروزرسانی کوکی Chrome» بزنید و پس از ورود به YouTube، دوباره تلاش کنید.\n\n"+output)
   raise RuntimeError(str(e)+"\n"+output)
  self.finish(j,path,info,settings,warning=rc!=0)
 def clear_active(self):
  with self.lock:self.process=None;self.active_id=None
 def finish(self,j,path,info,settings,warning=False):
  jid=j["job_id"];upsert_history(j["video_id"],title=j["title"],local_path=str(path),downloaded_at=now(),validation_json=json.dumps(info));self.update(jid,status="processing",progress=100,path=str(path),message="فایل سالم است")
  if settings.get("send_telegram"):
   self.update(jid,status="uploading",message="ارسال به Telegram")
   try:send(path,str(settings.get("chat_id") or ""),j["title"]);upsert_history(j["video_id"],telegram_sent_at=now())
   except Exception as e:self.update(jid,status="done",message="دانلود کامل شد؛ ارسال تلگرام ناموفق بود",error=str(e));return
   if not settings.get("keep_file",True):path.unlink(missing_ok=True);upsert_history(j["video_id"],local_path="")
  self.update(jid,status="done",progress=100,message="دانلود کامل شد"+("؛ yt-dlp هشدار داد اما فایل تأیید شد" if warning else ""))
 def pause(self,jid):
  with self.lock:
   if jid != self.active_id or not self.process or self.process.poll() is not None:raise RuntimeError("فقط دانلود فعال قابل توقف موقت است.")
   os.killpg(self.process.pid,signal.SIGSTOP)
  self.update(jid,status="paused",message="موقتاً متوقف شده")
 def resume(self,jid):
  with self.lock:
   if jid != self.active_id or not self.process or self.process.poll() is not None:raise RuntimeError("دانلود قابل ادامه پیدا نشد.")
   os.killpg(self.process.pid,signal.SIGCONT)
  self.update(jid,status="downloading",message="دانلود ادامه یافت")
 def cancel(self,jid=None):
  with connect() as c:
   if jid:
    row=c.execute("SELECT status FROM jobs WHERE job_id=?",(jid,)).fetchone()
    if not row:raise RuntimeError("کار پیدا نشد.")
    if row[0]=="queued":c.execute("UPDATE jobs SET status='canceled',message='لغو شد',updated_at=? WHERE job_id=?",(now(),jid));return True
    if row[0] not in ("downloading","processing","validating","uploading","paused"):return False
    c.execute("UPDATE jobs SET cancel_requested=1,updated_at=? WHERE job_id=?",(now(),jid))
    if row[0]=="paused":
     with self.lock:
      if self.process and self.process.poll() is None:os.killpg(self.process.pid,signal.SIGCONT)
   else:c.execute("UPDATE jobs SET cancel_requested=1,updated_at=? WHERE status IN ('downloading','processing','validating','uploading')",(now(),))
  return True
 def retry(self,jid):
  with connect() as c:r=c.execute("SELECT * FROM jobs WHERE job_id=?",(jid,)).fetchone()
  if not r:raise RuntimeError("کار پیدا نشد.")
  j=dict(r);return self.enqueue([{"video_id":j["video_id"],"playlist_id":j["playlist_id"],"title":j["title"],"video_url":j["video_url"],"position":j["position"]}],json.loads(j["settings_json"]))
 def delete(self,jid):
  with connect() as c:
   r=c.execute("SELECT status FROM jobs WHERE job_id=?",(jid,)).fetchone()
   if not r:raise RuntimeError("کار پیدا نشد.")
   if r[0] in ("downloading","processing","validating","uploading"):raise RuntimeError("ابتدا دانلود فعال را لغو کنید.")
   c.execute("DELETE FROM jobs WHERE job_id=?",(jid,))
 def move(self,jid,direction):
  with connect() as c:
   rows=c.execute("SELECT job_id,queue_order FROM jobs WHERE status='queued' ORDER BY queue_order,created_at").fetchall();ids=[r[0] for r in rows]
   if jid not in ids:raise RuntimeError("فقط کارهای در صف قابل جابه‌جایی هستند.")
   at=ids.index(jid);other=at+direction
   if other<0 or other>=len(ids):return
   a,b=rows[at],rows[other];c.execute("UPDATE jobs SET queue_order=? WHERE job_id=?",(b[1],a[0]));c.execute("UPDATE jobs SET queue_order=? WHERE job_id=?",(a[1],b[0]))
  self.wake.set()
