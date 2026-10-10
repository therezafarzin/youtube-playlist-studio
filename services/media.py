from __future__ import annotations
import json, re, shutil, subprocess
from pathlib import Path
from config import BROKEN, DOWNLOADS

INTERMEDIATE=re.compile(r"(\.part$|\.ytdl$|\.temp$|\.f\d+\.)",re.I)
def intermediate(path: Path) -> bool: return bool(INTERMEDIATE.search(path.name))
def probe(path: Path) -> dict:
    if intermediate(path) or not path.is_file(): raise ValueError("فایل موقت یا ناموجود است")
    p=shutil.which("ffprobe")
    if not p: raise RuntimeError("ffprobe پیدا نشد")
    r=subprocess.run([p,"-v","error","-show_entries","format=duration:stream=codec_type,codec_name","-of","json",str(path)],capture_output=True,text=True,timeout=60)
    if r.returncode: raise ValueError("ffprobe فایل را باز نکرد")
    data=json.loads(r.stdout); streams=data.get("streams",[]); types=[x.get("codec_type") for x in streams]
    duration=float(data.get("format",{}).get("duration") or 0)
    if "video" not in types or "audio" not in types or duration <= 0: raise ValueError("فایل نهایی باید Video، Audio و duration معتبر داشته باشد")
    return {"duration":duration,"video_codec":next(x.get("codec_name","") for x in streams if x.get("codec_type")=="video"),"audio_codec":next(x.get("codec_name","") for x in streams if x.get("codec_type")=="audio")}
def find(video_id: str) -> Path|None:
    paths=[p for p in DOWNLOADS.iterdir() if p.is_file() and f"[{video_id}]" in p.name and p.suffix.lower()==".mp4" and not intermediate(p)]
    return max(paths,key=lambda p:p.stat().st_mtime) if paths else None
def quarantine(path: Path) -> Path:
    BROKEN.mkdir(exist_ok=True); target=BROKEN / path.name
    if target.exists(): target=BROKEN / (path.stem+".invalid"+path.suffix)
    return path.replace(target)
