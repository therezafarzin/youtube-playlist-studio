from __future__ import annotations
import asyncio
from pathlib import Path
from config import TELEGRAM_TOKEN,TELEGRAM_SAFE_LIMIT
def configured() -> bool: return bool(TELEGRAM_TOKEN)
async def _send(path:Path,chat:str,caption:str):
 from telegram import Bot
 async with Bot(TELEGRAM_TOKEN) as bot:
  with path.open("rb") as f: return await bot.send_video(chat_id=chat,video=f,caption=caption[:1000],supports_streaming=True,write_timeout=300,read_timeout=300)
def send(path:Path,chat:str,caption:str):
 if not configured(): raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است.")
 if path.stat().st_size>TELEGRAM_SAFE_LIMIT: raise RuntimeError("فایل از حد امن ۴۹MB برای Bot API معمولی بزرگ‌تر است؛ فایل محلی حفظ شد.")
 return asyncio.run(_send(path,chat,caption))
async def _latest_chat():
 from telegram import Bot
 async with Bot(TELEGRAM_TOKEN) as bot:
  updates=await bot.get_updates(limit=50,timeout=0,allowed_updates=["message"])
  for update in reversed(updates):
   if update.effective_chat:
    chat=update.effective_chat
    return {"chat_id":str(chat.id),"name":chat.full_name or chat.title or chat.username or "Telegram"}
 raise RuntimeError("پیام جدیدی برای بات پیدا نشد؛ ابتدا در Telegram به بات پیام بدهید.")
def latest_chat():
 if not configured(): raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است.")
 return asyncio.run(_latest_chat())
