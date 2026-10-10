from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path
from config import COOKIE_BROWSER, COOKIE_PATH
def status() -> dict:
    if not COOKIE_PATH.exists(): return {"ready":False,"size":0}
    raw=COOKIE_PATH.read_text(errors="replace"); domains=sum(1 for x in raw.splitlines() if "youtube.com" in x or "google.com" in x)
    return {"ready":COOKIE_PATH.stat().st_size>=100 and "Cookie File" in raw[:200] and domains>0,"size":COOKIE_PATH.stat().st_size,"domains":domains}
def args() -> list[str]:
    if not status()["ready"]: raise RuntimeError("cookies.txt معتبر نیست؛ ابتدا «بروزرسانی کوکی» را بزن.")
    return ["--cookies",str(COOKIE_PATH)]
def refresh() -> dict:
    y=shutil.which("yt-dlp")
    if not y: raise RuntimeError("yt-dlp پیدا نشد")
    temp=COOKIE_PATH.with_suffix(".new.txt"); temp.unlink(missing_ok=True)
    r=subprocess.run([y,"--cookies-from-browser",COOKIE_BROWSER,"--cookies",str(temp)],capture_output=True,text=True,timeout=120)
    # yt-dlp may report no URL with a nonzero status after successful export.
    if not temp.exists(): raise RuntimeError("Chrome فایل کوکی نساخت.")
    raw=temp.read_text(errors="replace")
    if temp.stat().st_size<100 or "Cookie File" not in raw[:200] or not any("youtube.com" in x or "google.com" in x for x in raw.splitlines()): temp.unlink(missing_ok=True); raise RuntimeError("فایل کوکی معتبر YouTube/Google ساخته نشد.")
    os.chmod(temp,0o600); temp.replace(COOKIE_PATH); return status()
