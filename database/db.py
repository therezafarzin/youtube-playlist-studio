from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime
from config import DB_PATH

def now() -> str: return datetime.now().isoformat(timespec="seconds")

@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON"); con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA busy_timeout=30000")
    try: yield con
    finally: con.close()

def init_db() -> None:
    with connect() as c:
      c.executescript("""
      CREATE TABLE IF NOT EXISTS channels(channel_key TEXT PRIMARY KEY,title TEXT NOT NULL,url TEXT NOT NULL,channel_id TEXT,added_at TEXT NOT NULL,last_synced TEXT,pinned INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS playlists(playlist_id TEXT PRIMARY KEY,channel_key TEXT NOT NULL,title TEXT NOT NULL,url TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'playlist',thumbnail TEXT,reported_count INTEGER,sort_order INTEGER NOT NULL DEFAULT 0,pinned INTEGER NOT NULL DEFAULT 0,added_at TEXT NOT NULL,last_synced TEXT,FOREIGN KEY(channel_key) REFERENCES channels(channel_key) ON DELETE CASCADE);
      CREATE TABLE IF NOT EXISTS videos(playlist_id TEXT NOT NULL,video_id TEXT NOT NULL,position INTEGER NOT NULL,title TEXT NOT NULL,url TEXT NOT NULL,duration INTEGER,thumbnail TEXT,channel TEXT,downloaded_before INTEGER NOT NULL DEFAULT 0,telegram_sent INTEGER NOT NULL DEFAULT 0,local_path TEXT,added_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(playlist_id,video_id),FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE);
      CREATE TABLE IF NOT EXISTS media_history(video_id TEXT PRIMARY KEY,title TEXT,local_path TEXT,downloaded_at TEXT,telegram_sent_at TEXT,validation_json TEXT,updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,video_id TEXT NOT NULL,playlist_id TEXT,title TEXT NOT NULL,video_url TEXT NOT NULL,position INTEGER NOT NULL,settings_json TEXT NOT NULL,status TEXT NOT NULL,progress REAL NOT NULL DEFAULT 0,speed TEXT,eta TEXT,message TEXT,error TEXT,path TEXT,cancel_requested INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS idx_videos_video ON videos(video_id); CREATE INDEX IF NOT EXISTS idx_videos_order ON videos(playlist_id,position); CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(status,created_at);
      """)
      columns={row[1] for row in c.execute("PRAGMA table_info(jobs)")}
      if "queue_order" not in columns:
          c.execute("ALTER TABLE jobs ADD COLUMN queue_order INTEGER")
          c.execute("UPDATE jobs SET queue_order=rowid WHERE queue_order IS NULL")
      c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(status,queue_order)")
      # Crash recovery: no subprocess survives an app restart; queued work remains retryable.
      c.execute("UPDATE jobs SET status='failed', message='برنامه هنگام اجرا بسته شد؛ دوباره به صف اضافه کنید.', updated_at=? WHERE status IN ('downloading','processing','validating','uploading','paused')", (now(),))

def upsert_history(video_id: str, **values) -> None:
    with connect() as c:
      old=c.execute("SELECT * FROM media_history WHERE video_id=?",(video_id,)).fetchone()
      row=dict(old) if old else {"video_id":video_id,"title":"","local_path":"","downloaded_at":None,"telegram_sent_at":None,"validation_json":"{}"}
      row.update({k:v for k,v in values.items() if v is not None}); row["updated_at"]=now()
      c.execute("""INSERT INTO media_history(video_id,title,local_path,downloaded_at,telegram_sent_at,validation_json,updated_at) VALUES(:video_id,:title,:local_path,:downloaded_at,:telegram_sent_at,:validation_json,:updated_at) ON CONFLICT(video_id) DO UPDATE SET title=excluded.title,local_path=excluded.local_path,downloaded_at=excluded.downloaded_at,telegram_sent_at=excluded.telegram_sent_at,validation_json=excluded.validation_json,updated_at=excluded.updated_at""",row)
      c.execute("UPDATE videos SET downloaded_before=CASE WHEN :downloaded_at IS NOT NULL THEN 1 ELSE downloaded_before END, telegram_sent=CASE WHEN :telegram_sent_at IS NOT NULL THEN 1 ELSE telegram_sent END, local_path=:local_path, updated_at=:updated_at WHERE video_id=:video_id",row)

def jobs() -> list[dict]:
    with connect() as c: return [dict(x) for x in c.execute("SELECT * FROM jobs ORDER BY created_at")]
