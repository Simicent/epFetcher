# epFetcher

A lightweight background script that prefetches the next episode in Jellyfin into your rclone cache before it starts playing, eliminating buffering at episode transitions.

## How It Works

The script runs every minute via cron and:

1. Checks for active Jellyfin sessions
2. Detects if an episode is playing with less than 10 minutes remaining
3. Finds the next episode in the season
4. Reads the first 50% of the file (minimum 256MB) through the rclone mount, populating the local cache
5. Logs the result to `prefetch.log`

By the time the next episode starts, the data is already in rclone's cache — Jellyfin gets it at local disk speed instead of fetching from the remote on demand.

## Requirements

- Python 3.10+
- A Jellyfin server with API access
- rclone VFS mount with `--vfs-cache-mode full` and `--vfs-cache-max-age` of at least 1h
- The script must run on a host where the rclone mount path matches the paths returned by the Jellyfin API

## Installation

\```bash
git clone https://github.com/Simicent/epFetcher.git
cd epFetcher
bash install.sh
\```

The installer will create a venv, install dependencies, copy `.env.example` to `.env`, and register the cron job.

## Configuration

Edit `.env` after installation:

\```env
JELLYFIN_URL=http://your-jellyfin-host:8096
JELLYFIN_TOKEN=your_api_token_here
\```

To get your API token: Jellyfin Dashboard → API Keys → Add API Key.

## Deployment Requirement

This script reads episode files **directly via the filesystem path** returned by the Jellyfin API. It must run on a host where that path is valid — same machine as Jellyfin, or a separate machine with identical rclone mount points. Docker users must share the same volume mounts as the Jellyfin container.

## Log Format

\```
2026-04-24 07:15:01 | Frieren | current=Episode 1 | next=S01E02 Episode 2 | prefetched=512MB | /mnt/media/frieren/S01E02.mkv
\```

## File Structure

\```
epFetcher/
├── main.py
├── install.sh
├── requirements.txt
├── .env.example
├── .env               # not committed
└── prefetch.log       # not committed
\```

## Removing the Cron Job

\```bash
crontab -e
\```

## License

MIT