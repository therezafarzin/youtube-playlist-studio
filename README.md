# YouTube Playlist Studio

A local, RTL (right-to-left) dashboard for managing a library of YouTube channels and playlists, downloading videos sequentially, and optionally sending them to Telegram.

The application runs exclusively on `127.0.0.1`.

## Installation and Setup

```bash
cd /Users/rezafarzin/Documents/ChatGPT/youtube_playlist_studio
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### System Requirements

The following tools must be installed:

- `yt-dlp`
- `ffmpeg`
- `ffprobe`

On macOS, you can install them using Homebrew:

```bash
brew install yt-dlp ffmpeg
```

Once the application is running, open the dashboard in your browser:

**http://127.0.0.1:8787**

## Workflow

1. **Refresh Chrome Cookies:** In the Dashboard, click **"Refresh Chrome Cookies"**. This is the only operation that may trigger a macOS Keychain access prompt. All subsequent scanning and downloading operations use the local `cookies.txt` file.
2. **Add and Sync Playlists:** Enter the main YouTube channel URL, open the desired playlist, and synchronize its contents.
3. **Select and Download Videos:** Select videos, choose the preferred quality, and add them to the download queue. The queue uses a single worker and is persisted in an SQLite database.

### Download Validation

A download is marked as successful only after validation with `ffprobe`, confirming that the final file contains:

- A valid video stream
- A valid audio stream
- A valid duration

Incomplete `.part` files or separate streams such as `.f137.mp4` are never considered completed downloads.

Corrupted or invalid files are moved to:

```text
downloads/broken/
```

## Telegram Integration

Telegram integration is optional.

Before starting the application, set your Telegram bot token as an environment variable in your shell:

```bash
export TELEGRAM_BOT_TOKEN='token-here'
python app.py
```

Enter your Telegram Chat ID in the dashboard interface.

### File Size Limitations

Files exceeding the configured safe limit of **49 MB** for the Telegram Bot API remain marked as successfully downloaded, but their Telegram delivery is recorded as failed.

The downloaded files are preserved and are **not deleted** if Telegram delivery fails.

## Data Storage and Backups

The following files and directories contain user data and are excluded from Git tracking:

- `library.db` — SQLite database containing library and queue information.
- `cookies.txt` — Locally stored YouTube authentication cookies.
- `downloads/` — Downloaded video files.

### Existing Backup

A snapshot was created before the dashboard redesign:

```text
backups/pre-redesign-20260925/
```

**Security Notice:** This backup contains authentication cookies and is protected by restrictive file permissions. It must be kept private and should never be uploaded to a public repository.

### Creating a New Backup

To create a new backup:

1. Stop the application.
2. Securely copy `library.db`.
3. Back up the entire `downloads/` directory.
4. Store the backup in a secure location.

Always ensure the application is stopped before copying the database to avoid inconsistencies.

## Troubleshooting

### Cookie or Authentication Errors

If a playlist scan fails due to cookie-related issues:

- Make sure you are signed in to YouTube in Google Chrome.
- Refresh Chrome cookies using the dashboard.
- Retry the scan or download.

### Interrupted Downloads

If the application crashes while processing a download job, the interrupted job is marked as `failed`.

Failed jobs must be manually added back to the queue. They are not automatically retried.

### Application Logs

Application logs are stored at:

```text
logs/app.log
```

Sensitive information, including Telegram bot tokens and authentication cookies, is excluded from application logs.

## Security and Privacy

- The application is accessible only through the local loopback address (`127.0.0.1`).
- Authentication cookies remain stored locally.
- Telegram integration is optional.
- User data, downloaded files, and cookies are excluded from Git tracking.
- Sensitive credentials should never be committed to version control.

## Technology Stack

- **Python** — Application backend
- **SQLite** — Persistent library and download queue storage
- **yt-dlp** — YouTube video and playlist downloading
- **FFmpeg / FFprobe** — Media processing and validation
- **Telegram Bot API** — Optional video delivery
- **Local Web Dashboard** — Browser-based interface with RTL support

---

**YouTube Playlist Studio** provides a local workflow for organizing YouTube playlists, managing sequential downloads, validating media files, and optionally delivering downloaded videos through Telegram.
