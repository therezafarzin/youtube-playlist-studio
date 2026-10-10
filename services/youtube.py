from __future__ import annotations
import hashlib,json,re,shutil,subprocess
from urllib.parse import parse_qs,urlparse
from database.db import connect,now
from .cookies import args as cookie_args
def run_json(url: str) -> dict:
    y=shutil.which("yt-dlp");
    if not y: raise RuntimeError("yt-dlp پیدا نشد")
    r=subprocess.run([y,*cookie_args(),"--flat-playlist","--dump-single-json","--no-warnings","--socket-timeout","60","--retries","3",url],capture_output=True,text=True,timeout=180)
    try: return json.loads(r.stdout)
    except Exception: raise RuntimeError((r.stderr or r.stdout or "yt-dlp خروجی معتبری نداد")[-1500:])
def channel_url(raw: str) -> str:
    raw=raw.strip(); raw=raw if raw.startswith("http") else "https://"+raw; p=urlparse(raw)
    if "youtube.com" not in p.netloc or not p.path.strip("/"): raise RuntimeError("لینک اصلی کانال YouTube را وارد کنید.")
    path=re.sub(r"/(videos|shorts|streams|playlists|featured|community|about)$","",p.path.rstrip("/"),flags=re.I)
    return "https://www.youtube.com"+path
def pid(url: str) -> str: return (parse_qs(urlparse(url).query).get("list") or [""])[0]
def sync_channel(raw: str) -> dict:
    base=channel_url(raw); data=run_json(base+"/playlists"); cid=str(data.get("channel_id") or data.get("uploader_id") or "")
    key=cid if cid.startswith("UC") else "ch_"+hashlib.sha1(base.encode()).hexdigest()[:18]; title=str(data.get("channel") or data.get("uploader") or data.get("title") or base.rsplit("/",1)[-1]); title=re.sub(r"\s*[-–—]\s*Playlists\s*$","",title,flags=re.I)
    refs={};
    for n,e in enumerate(data.get("entries") or [],1):
      if not isinstance(e,dict): continue
      ident=pid(str(e.get("url") or e.get("webpage_url") or "")) or (str(e.get("id") or "") if str(e.get("id") or "").startswith(("PL","UU","FL","OL")) else "")
      if ident: refs[ident]=(str(e.get("title") or ident),f"https://www.youtube.com/playlist?list={ident}",n)
    with connect() as c:
      t=now(); c.execute("INSERT INTO channels(channel_key,title,url,channel_id,added_at,last_synced) VALUES(?,?,?,?,?,?) ON CONFLICT(channel_key) DO UPDATE SET title=excluded.title,url=excluded.url,channel_id=excluded.channel_id,last_synced=excluded.last_synced",(key,title,base,cid,t,t))
      allrefs={f"uploads::{key}":("همه ویدیوهای کانال",base+"/videos",-1),**refs}
      for ident,(name,url,order) in allrefs.items(): c.execute("INSERT INTO playlists(playlist_id,channel_key,title,url,kind,sort_order,added_at,last_synced) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(playlist_id) DO UPDATE SET title=excluded.title,url=excluded.url,sort_order=excluded.sort_order",(ident,key,name,url,"uploads" if ident.startswith("uploads::") else "playlist",order,t,t))
    return {"channel_key":key,"title":title,"playlist_count":len(refs)+1}
def library() -> list[dict]:
    with connect() as c:
      channels=[]
      for ch in c.execute("SELECT * FROM channels ORDER BY pinned DESC,added_at DESC"):
       x=dict(ch); x["playlists"]= [dict(p) for p in c.execute("SELECT p.*,count(v.video_id) cached_count FROM playlists p LEFT JOIN videos v ON v.playlist_id=p.playlist_id WHERE p.channel_key=? GROUP BY p.playlist_id ORDER BY p.pinned DESC,p.sort_order,p.title",(ch["channel_key"],))]; channels.append(x)
      return channels
def sync_playlist(playlist_id: str) -> int:
    with connect() as c: p=c.execute("SELECT p.*,c.title channel_title FROM playlists p JOIN channels c ON c.channel_key=p.channel_key WHERE playlist_id=?",(playlist_id,)).fetchone()
    if not p: raise RuntimeError("Playlist پیدا نشد")
    data=run_json(p["url"]); entries=data.get("entries") or []; t=now(); count=0
    with connect() as c:
      for position,e in enumerate(entries,1):
       if not isinstance(e,dict) or not e.get("id"): continue
       vid=str(e["id"]); title=str(e.get("title") or vid); url=str(e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}")
       c.execute("""INSERT INTO videos(playlist_id,video_id,position,title,url,duration,thumbnail,channel,added_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(playlist_id,video_id) DO UPDATE SET position=excluded.position,title=excluded.title,url=excluded.url,duration=COALESCE(excluded.duration,videos.duration),thumbnail=COALESCE(excluded.thumbnail,videos.thumbnail),channel=COALESCE(excluded.channel,videos.channel),updated_at=excluded.updated_at""",(playlist_id,vid,int(e.get("playlist_index") or position),title,url,e.get("duration"),e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",e.get("channel") or p["channel_title"],t,t)); count+=1
      # A playlist can expose a repeated ID; the library key deliberately keeps
      # one canonical row per video ID, so report the persisted membership.
      count=c.execute("SELECT COUNT(*) FROM videos WHERE playlist_id=?",(playlist_id,)).fetchone()[0]
      c.execute("UPDATE playlists SET reported_count=?,last_synced=? WHERE playlist_id=?",(count,t,playlist_id))
    return count
def videos(playlist_id: str) -> tuple[dict,list[dict]]:
    from .media import find
    with connect() as c:
      p=c.execute("SELECT * FROM playlists WHERE playlist_id=?",(playlist_id,)).fetchone(); rows=c.execute("SELECT v.*,h.downloaded_at,h.telegram_sent_at FROM videos v LEFT JOIN media_history h ON h.video_id=v.video_id WHERE v.playlist_id=? ORDER BY position",(playlist_id,)).fetchall()
    if not p: raise RuntimeError("Playlist پیدا نشد")
    result=[]
    for r in rows:
      x=dict(r); local=find(x["video_id"]); x["local_exists"]=bool(local); x["local_path"]=str(local or x.get("local_path") or ""); x["duration_text"]=fmt(x.get("duration")); result.append(x)
    return dict(p),result
def fmt(n):
    try: n=int(n or 0); return f"{n//3600}:{n%3600//60:02d}:{n%60:02d}" if n>=3600 else f"{n//60}:{n%60:02d}"
    except: return ""
