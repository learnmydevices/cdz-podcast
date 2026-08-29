#!/usr/bin/env python3
"""
new_episode.py - publish an episode of Cinema-ye Do Zabaane.

Reads the MP3's duration and file size itself, inserts a directory-valid
item at the top of feed.xml, validates the XML, and tells you exactly what
to upload. It refuses to write a broken feed.

Usage:
    python3 new_episode.py "path/to/episode.mp3" \
        --title "Episode title as it should appear in apps" \
        --notes-file notes_ep1.txt

Options:
    --notes "text"      Show notes inline instead of from a file
    --episode N         Episode number (default: auto, count + 1)
    --date "YYYY-MM-DD" Publish date (default: now)
    --remote-name x.mp3 Filename to use in the public URL (default: a clean
                        slug of the local filename; upload with THIS name)

Requires: ffprobe (comes with ffmpeg), config.json filled in.
"""

import argparse
import json
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, time as dtime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FEED = HERE / "feed.xml"
CONFIG = HERE / "config.json"
MARKER = "<!-- EPISODES:NEWEST-FIRST -->"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config() -> dict:
    if not CONFIG.exists():
        die("config.json not found next to this script.")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    for key in ("site_url", "media_base_url"):
        val = cfg.get(key, "")
        if not val or "PASTE" in val:
            die(f"Fill in '{key}' in config.json first.")
        cfg[key] = "https://" + re.sub(r"^https?://", "", val).rstrip("/")
    return cfg


def mp3_duration_seconds(path: Path) -> int:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        return round(float(out))
    except FileNotFoundError:
        die("ffprobe not found. Install ffmpeg:  brew install ffmpeg")
    except (subprocess.CalledProcessError, ValueError):
        die(f"Could not read duration from {path.name}. Is it a valid audio file?")


def hms(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def slugify(name: str) -> str:
    stem = Path(name).stem
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower() or "episode"
    return stem + ".mp3"


def main() -> None:
    p = argparse.ArgumentParser(description="Add an episode to the CDZ feed.")
    p.add_argument("mp3", help="Path to the finished episode MP3")
    p.add_argument("--title", required=True)
    p.add_argument("--notes", default=None)
    p.add_argument("--notes-file", default=None)
    p.add_argument("--episode", type=int, default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    p.add_argument("--remote-name", default=None)
    args = p.parse_args()

    mp3 = Path(args.mp3).expanduser().resolve()
    if not mp3.exists():
        die(f"File not found: {mp3}")
    if args.notes_file:
        notes = Path(args.notes_file).expanduser().read_text(encoding="utf-8").strip()
    elif args.notes:
        notes = args.notes.strip()
    else:
        die("Provide show notes with --notes or --notes-file.")

    cfg = load_config()
    feed_text = FEED.read_text(encoding="utf-8")
    if MARKER not in feed_text:
        die("feed.xml is missing the episodes marker; don't remove the comment line.")

    # Stamp the site and media URLs (first run) so the channel links are real.
    feed_text = feed_text.replace("https://SITE-URL-PLACEHOLDER", cfg["site_url"])
    feed_text = feed_text.replace("https://MEDIA-BASE-PLACEHOLDER", cfg["media_base_url"])

    remote_name = args.remote_name or slugify(mp3.name)
    enclosure_url = cfg["media_base_url"] + "/" + urllib.parse.quote(remote_name)
    if enclosure_url in feed_text:
        die(f"The feed already has an episode at {enclosure_url}. "
            f"Use --remote-name to give this file a different name.")

    size_bytes = mp3.stat().st_size
    duration = mp3_duration_seconds(mp3)
    ep_num = args.episode or feed_text.count("<item>") + 1
    if args.date:
        try:
            d = datetime.strptime(args.date, "%Y-%m-%d")
            pub = datetime.combine(d.date(), dtime(12, 0), tzinfo=timezone.utc)
        except ValueError:
            die("--date must look like 2026-08-29")
    else:
        pub = datetime.now(timezone.utc)

    item = f"""    <item>
      <title>{escape(args.title)}</title>
      <description>{escape(notes)}</description>
      <enclosure url="{enclosure_url}" length="{size_bytes}" type="audio/mpeg"/>
      <guid isPermaLink="false">{enclosure_url}</guid>
      <pubDate>{format_datetime(pub)}</pubDate>
      <itunes:duration>{hms(duration)}</itunes:duration>
      <itunes:episode>{ep_num}</itunes:episode>
      <itunes:explicit>false</itunes:explicit>
    </item>"""

    new_text = feed_text.replace(MARKER, MARKER + "\n" + item, 1)

    # Validate before writing anything: a broken feed never reaches disk.
    try:
        ET.fromstring(new_text.encode("utf-8"))
    except ET.ParseError as e:
        die(f"Validation failed, feed NOT modified: {e}")

    FEED.write_text(new_text, encoding="utf-8")
    print("Feed updated and validated.")
    print(f"  Episode {ep_num}: {args.title}")
    print(f"  Duration {hms(duration)}, {size_bytes:,} bytes")
    print()
    print("Before you git push, make sure this file is uploaded to R2 with EXACTLY this name:")
    print(f"  {remote_name}")
    print(f"  (it will be served at {enclosure_url})")
    if remote_name != mp3.name:
        print(f"  Tip: rename on upload, or run:  cp \"{mp3}\" ~/Desktop/{remote_name}")


if __name__ == "__main__":
    main()
