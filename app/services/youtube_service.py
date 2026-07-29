"""
YouTube content extraction service.

- extract_video_id / extract_playlist_id: parse URLs
- get_video_metadata: title + author via oEmbed (no API key needed)
- get_video_transcript: captions via youtube-transcript-api (no API key needed)
- get_playlist_video_ids: requires YouTube Data API v3 key
- get_video_embed_html: responsive iframe HTML
"""
import re
import logging
import httpx

logger = logging.getLogger(__name__)

YOUTUBE_OEMBED = "https://www.youtube.com/oembed"
YOUTUBE_PLAYLIST_API = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEO_API = "https://www.googleapis.com/youtube/v3/videos"


# ─── URL parsing ──────────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str | None:
    """Extract 11-char video ID from any YouTube URL format."""
    patterns = [
        r"(?:youtube\.com/watch\?(?:.*&)?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None


def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from YouTube playlist URL."""
    m = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", url.strip())
    return m.group(1) if m else None


def is_playlist_url(url: str) -> bool:
    return "list=" in url and extract_playlist_id(url) is not None


# ─── Metadata (no API key) ────────────────────────────────────────────────────

def get_video_metadata(video_id: str) -> dict:
    """Get title, author, thumbnail via YouTube oEmbed (free, no key needed)."""
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get(YOUTUBE_OEMBED, params={
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "format": "json",
            })
            r.raise_for_status()
            data = r.json()
            return {
                "title":     data.get("title", ""),
                "author":    data.get("author_name", ""),
                "thumbnail": data.get("thumbnail_url", ""),
            }
    except Exception as e:
        logger.warning("oEmbed failed for %s: %s", video_id, e)
        return {"title": "", "author": "", "thumbnail": ""}


# ─── Transcript (no API key) ──────────────────────────────────────────────────

def get_video_transcript(video_id: str, preferred_langs: list[str] = None) -> str:
    """
    Fetch transcript text. Returns empty string if unavailable.
    Tries preferred_langs in order, then falls back to any available language.
    """
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled,
        )
        langs = preferred_langs or ["vi", "en"]
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 1. Try manual transcripts in preferred langs
        for lang in langs:
            try:
                entries = transcript_list.find_transcript([lang]).fetch()
                return _entries_to_text(entries)
            except Exception:
                pass

        # 2. Try auto-generated in preferred langs
        for lang in langs:
            try:
                entries = transcript_list.find_generated_transcript([lang]).fetch()
                return _entries_to_text(entries)
            except Exception:
                pass

        # 3. Any available transcript
        for t in transcript_list:
            try:
                return _entries_to_text(t.fetch())
            except Exception:
                pass

        return ""

    except Exception as e:
        logger.warning("Transcript unavailable for %s: %s", video_id, e)
        return ""


def _entries_to_text(entries: list) -> str:
    """Convert transcript entries to clean plain text."""
    parts = []
    for e in entries:
        text = e.get("text", "").strip()
        # Remove [Music], [Applause], etc.
        if text and not re.match(r"^\[.*\]$", text):
            parts.append(text)
    return " ".join(parts)


# ─── Playlist (YouTube Data API v3 required) ──────────────────────────────────

def get_playlist_video_ids(playlist_id: str, api_key: str, max_results: int = 100) -> list[str]:
    """
    Fetch video IDs from a playlist using YouTube Data API v3.
    Requires a valid API key. Returns list of video IDs (up to max_results).
    """
    video_ids = []
    page_token = None

    while len(video_ids) < max_results:
        params = {
            "part":       "contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(50, max_results - len(video_ids)),
            "key":        api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            with httpx.Client(timeout=20) as c:
                r = c.get(YOUTUBE_PLAYLIST_API, params=params)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPStatusError as e:
            logger.error("Playlist API error %s: %s", e.response.status_code, e.response.text[:200])
            break
        except Exception as e:
            logger.error("Playlist fetch error: %s", e)
            break

        for item in data.get("items", []):
            vid_id = item.get("contentDetails", {}).get("videoId")
            if vid_id:
                video_ids.append(vid_id)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    logger.info("Playlist %s: fetched %d video IDs", playlist_id, len(video_ids))
    return video_ids


def get_playlist_metadata(playlist_id: str, api_key: str) -> dict:
    """Get playlist title and description."""
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get(
                "https://www.googleapis.com/youtube/v3/playlists",
                params={"part": "snippet", "id": playlist_id, "key": api_key},
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            if items:
                sn = items[0].get("snippet", {})
                return {"title": sn.get("title", ""), "description": sn.get("description", "")}
    except Exception as e:
        logger.warning("Playlist metadata error: %s", e)
    return {"title": "", "description": ""}


# ─── Embed HTML ───────────────────────────────────────────────────────────────

def get_video_embed_html(video_id: str) -> str:
    """Return responsive 16:9 iframe for embedding a YouTube video."""
    return (
        '<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;margin:1.5em 0">'
        f'<iframe style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" '
        f'src="https://www.youtube.com/embed/{video_id}" '
        f'title="YouTube video" allowfullscreen loading="lazy"></iframe>'
        '</div>'
    )


# ─── Parse multi-line URL input ───────────────────────────────────────────────

def parse_youtube_input(raw_text: str, youtube_api_key: str = "") -> list[str]:
    """
    Parse a block of text containing YouTube URLs (video or playlist).
    Returns a flat list of video IDs (deduped, ordered).
    """
    seen = set()
    video_ids = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if is_playlist_url(line) and youtube_api_key:
            pl_id = extract_playlist_id(line)
            ids = get_playlist_video_ids(pl_id, youtube_api_key)
            for vid in ids:
                if vid not in seen:
                    seen.add(vid)
                    video_ids.append(vid)
        else:
            vid = extract_video_id(line)
            if vid and vid not in seen:
                seen.add(vid)
                video_ids.append(vid)

    return video_ids
