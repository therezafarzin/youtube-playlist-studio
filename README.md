# YouTube Playlist Studio

داشبورد محلی و RTL برای Library کانال‌ها و Playlistهای YouTube، دانلود ترتیبی و ارسال اختیاری به Telegram. برنامه فقط روی `127.0.0.1` اجرا می‌شود.

## نصب و اجرا

```bash
cd /Users/rezafarzin/Documents/ChatGPT/youtube_playlist_studio
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

پیش‌نیازهای سیستم: `yt-dlp`، `ffmpeg` و `ffprobe` (مثلاً `brew install yt-dlp ffmpeg`). سپس `http://127.0.0.1:8787` را باز کنید.

## گردش کار

1. در Dashboard، «بروزرسانی کوکی Chrome» را بزنید. تنها این عمل ممکن است Keychain را باز کند؛ تمام scan و downloadهای بعدی از `cookies.txt` محلی استفاده می‌کنند.
2. URL اصلی کانال را وارد کنید، Playlist را باز کنید و Sync کنید.
3. ویدیوها را انتخاب، کیفیت را تعیین و به صف اضافه کنید. صف تک‌کارگر و در SQLite پایدار است.

فایل نهایی فقط پس از `ffprobe` و تأیید Video + Audio + duration معتبر موفق می‌شود. فایل‌های `.part` یا streamهای جدا مثل `.f137.mp4` هرگز نهایی محسوب نمی‌شوند؛ فایل خراب به `downloads/broken/` می‌رود.

## Telegram

اختیاری است. پیش از اجرا token را فقط در محیط shell بدهید:

```bash
export TELEGRAM_BOT_TOKEN='token-here'
python app.py
```

Chat ID را در UI وارد کنید. فایل بالاتر از حد امن ۴۹MB برای Bot API به‌عنوان دانلود موفق می‌ماند اما ارسال شکست‌خورده ثبت می‌شود و فایل پاک نمی‌شود.

## داده و پشتیبان

`library.db`، `cookies.txt` و `downloads/` دادهٔ کاربر هستند و توسط Git نادیده گرفته می‌شوند. پیش از بازطراحی یک snapshot در `backups/pre-redesign-20260925/` ساخته شده است؛ این پوشه شامل cookie است و permission خصوصی دارد. برای backup جدید، در زمانی که برنامه بسته است از `library.db` و `downloads/` کپی امن بگیرید.

## رفع مشکل

- اگر scan خطای cookie داد، کوکی را refresh کنید و در Chrome وارد YouTube باشید.
- اگر یک job هنگام crash قطع شده، به `failed` تبدیل می‌شود و باید آگاهانه دوباره به صف اضافه شود.
- لاگ بدون token/cookie در `logs/app.log` است.
