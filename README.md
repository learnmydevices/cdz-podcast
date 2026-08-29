# Cinema-ye Do Zabaane (Bilingual Cinema)

Self-hosted podcast: feed and show page on Cloudflare Pages, audio on Cloudflare R2.

## Files
- `feed.xml` - the podcast RSS feed. Directories (Apple, Spotify, Amazon, YouTube) read this.
- `index.html` - the show page. Reads feed.xml in the browser and renders the episode list.
- `new_episode.py` - publish script. Run it per episode; it computes duration and size, inserts a validated item, and refuses to write a broken feed.
- `config.json` - the two URLs stamped into the feed (Pages site URL, R2 public URL). Fill in once.
- `notes_ep1.txt` - show notes for episode 1.

## Publish an episode
1. Upload the MP3 to the R2 bucket (name it what the script tells you).
2. `python3 new_episode.py "episode.mp3" --title "..." --notes-file notes.txt`
3. `git add -A && git commit -m "Episode N" && git push`

Pages redeploys automatically; every directory picks up the new episode from the feed.
