from __future__ import annotations
import shutil, subprocess
from flask import Flask,jsonify,request,render_template
from config import HOST,PORT,DOWNLOADS,prepare_paths
from database.db import connect,init_db,jobs
from services.cookies import refresh,status
from services.downloader import QueueEngine
from services.youtube import library,sync_channel,sync_playlist,videos
from services.telegram import configured,latest_chat
prepare_paths(); init_db(); engine=QueueEngine(); app=Flask(__name__)
def ok(**data): return jsonify(ok=True,**data)
def fail(e,code=400): return jsonify(ok=False,error=str(e)),code
@app.get("/")
def home(): return render_template("index.html")
@app.get("/api/health")
def health(): return ok(tools={x:bool(shutil.which(x)) for x in ("yt-dlp","ffmpeg","ffprobe")},telegram=configured())
@app.get("/api/cookie-status")
def cookie_status(): return ok(**status())
@app.post("/api/refresh-cookies")
def refresh_cookies():
 try:return ok(**refresh())
 except Exception as e:return fail(e)
@app.get("/api/library")
def get_library(): return ok(channels=library())
@app.post("/api/library/add-channel")
def add_channel():
 try:return ok(channel=sync_channel((request.json or {}).get("url", "")))
 except Exception as e:return fail(e)
@app.post("/api/library/sync-channel")
def sync_ch(): return add_channel()
@app.post("/api/library/delete-channel")
def delete_channel():
 key=str((request.json or {}).get("channel_key") or "")
 if not key:return fail("شناسهٔ کانال مشخص نیست.")
 with connect() as c:c.execute("DELETE FROM channels WHERE channel_key=?",(key,))
 return ok()
@app.post("/api/library/toggle-playlist-pin")
def pin():
 ident=str((request.json or {}).get("playlist_id") or "")
 with connect() as c:
  r=c.execute("SELECT pinned FROM playlists WHERE playlist_id=?",(ident,)).fetchone()
  if not r:return fail("Playlist پیدا نشد.",404)
  c.execute("UPDATE playlists SET pinned=? WHERE playlist_id=?",(not r[0],ident))
 return ok()
@app.post("/api/library/collection-videos")
def collection():
 body=request.json or {}; ident=str(body.get("playlist_id") or "")
 try:
  with connect() as c: count=c.execute("SELECT count(*) FROM videos WHERE playlist_id=?",(ident,)).fetchone()[0]
  if body.get("refresh") or count==0: sync_playlist(ident)
  p,items=videos(ident); return ok(playlist=p,videos=items)
 except Exception as e:return fail(e)
@app.post("/api/enqueue")
def enqueue():
 body=request.json or {}; items=body.get("items") or []
 if not items:return fail("حداقل یک ویدیو را انتخاب کنید.")
 settings={k:body.get(k) for k in ("quality","send_telegram","chat_id","keep_file","redownload")}; return ok(added=engine.enqueue(items,settings))
@app.get("/api/status")
def queue_status(): return ok(jobs=jobs())
@app.post("/api/cancel-current")
def cancel(): return ok(message="درخواست لغو ثبت شد." if engine.cancel() else "دانلود فعالی وجود ندارد.")
@app.post("/api/jobs/<job_id>/cancel")
def cancel_job(job_id):
 try: return ok(message="کار لغو شد." if engine.cancel(job_id) else "این کار دیگر فعال نیست.")
 except Exception as e:return fail(e)
@app.post("/api/jobs/<job_id>/pause")
def pause_job(job_id):
 try:engine.pause(job_id);return ok(message="دانلود موقتاً متوقف شد.")
 except Exception as e:return fail(e)
@app.post("/api/jobs/<job_id>/resume")
def resume_job(job_id):
 try:engine.resume(job_id);return ok(message="دانلود ادامه یافت.")
 except Exception as e:return fail(e)
@app.post("/api/jobs/<job_id>/retry")
def retry_job(job_id):
 try:return ok(added=engine.retry(job_id))
 except Exception as e:return fail(e)
@app.post("/api/jobs/<job_id>/delete")
def delete_job(job_id):
 try:engine.delete(job_id);return ok()
 except Exception as e:return fail(e)
@app.post("/api/jobs/<job_id>/move")
def move_job(job_id):
 try:engine.move(job_id,int((request.json or {}).get("direction",0)));return ok()
 except Exception as e:return fail(e)
@app.post("/api/clear-finished")
def clear():
 with connect() as c:c.execute("DELETE FROM jobs WHERE status IN ('done','failed','canceled','skipped')")
 return ok()
@app.post("/api/open-downloads")
def open_downloads(): subprocess.Popen(["open",str(DOWNLOADS)]); return ok()
@app.post("/api/detect-chat")
def detect_chat():
 try:return ok(**latest_chat())
 except Exception as e:return fail(e)
def main():
 missing=[x for x in ("yt-dlp","ffmpeg","ffprobe") if not shutil.which(x)]
 if missing: raise RuntimeError("ابزارهای لازم پیدا نشدند: "+", ".join(missing))
 print(f"YouTube Playlist Studio: http://{HOST}:{PORT}"); app.run(host=HOST,port=PORT,debug=False,threaded=True,use_reloader=False)
if __name__=="__main__":main()
