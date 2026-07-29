"""
Google Drive image service.

Fetches images from a public Google Drive folder and rehosts them via ImgBB
for stable embedding in blog articles.

Requires:
  - Google Drive folder must be public ("Anyone with the link" = Viewer)
  - Google API key with Drive API v3 enabled (same key used for YouTube/Indexing)
  - ImgBB API key for rehosting (optional but recommended)

Fallback chain (called by image_service.py):
  Google Drive → Pixabay → AI generation (Pollinations.ai)
"""
import logging
import random
import re
import urllib.parse

import httpx

logger = logging.getLogger(__name__)

DRIVE_FILES_API = "https://www.googleapis.com/drive/v3/files"
DRIVE_DOWNLOAD_URL = "https://drive.google.com/uc?export=download&id={file_id}"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


# ─── URL parsing ──────────────────────────────────────────────────────────────

def extract_folder_id(url: str) -> str | None:
    """Extract Google Drive folder ID from various URL formats."""
    if not url:
        return None
    # https://drive.google.com/drive/folders/FOLDER_ID
    # https://drive.google.com/drive/u/0/folders/FOLDER_ID
    m = re.search(r"/folders/([a-zA-Z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    # Raw folder ID (user may paste just the ID)
    if re.match(r"^[a-zA-Z0-9_-]{25,}$", url.strip()):
        return url.strip()
    return None


# ─── Fetch image list from Drive ──────────────────────────────────────────────

def list_folder_images(folder_id: str, api_key: str, max_files: int = 50) -> list[dict]:
    """
    List image files in a public Google Drive folder.
    Returns list of dicts with {id, name}.
    """
    try:
        params = {
            "q":      f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false",
            "fields": "files(id,name,mimeType)",
            "pageSize": max_files,
            "key":    api_key,
        }
        with httpx.Client(timeout=15) as c:
            r = c.get(DRIVE_FILES_API, params=params)
            r.raise_for_status()
            files = r.json().get("files", [])
            logger.info("Drive folder %s: found %d images", folder_id, len(files))
            return files
    except Exception as e:
        logger.warning("Drive list_folder_images error (folder=%s): %s", folder_id, e)
        return []


def _download_drive_image(file_id: str) -> bytes | None:
    """Download an image from Google Drive by file ID."""
    url = DRIVE_DOWNLOAD_URL.format(file_id=file_id)
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            r = c.get(url)
            if r.status_code == 200 and len(r.content) > 1000:
                return r.content
    except Exception as e:
        logger.warning("Drive download error (file_id=%s): %s", file_id, e)
    return None


def _upload_to_imgbb(image_bytes: bytes, imgbb_key: str, name: str = "image") -> str | None:
    """Upload image bytes to ImgBB and return the hosted URL."""
    import base64
    try:
        b64 = base64.b64encode(image_bytes).decode()
        with httpx.Client(timeout=30) as c:
            r = c.post(
                "https://api.imgbb.com/1/upload",
                data={"key": imgbb_key, "image": b64, "name": name},
            )
            r.raise_for_status()
            url = r.json()["data"]["url"]
            logger.info("ImgBB upload OK: %s", url)
            return url
    except Exception as e:
        logger.warning("ImgBB upload error: %s", e)
    return None


# ─── Main: get one image from Drive folder ────────────────────────────────────

def get_drive_image(
    drive_folder_url: str,
    google_api_key: str,
    imgbb_key: str = "",
    keywords: list[str] = None,
) -> str | None:
    """
    Pick a random image from the Drive folder, download it, rehost on ImgBB.
    Returns the stable hosted URL or None if unavailable.

    Image selection:
    - If file names contain keywords → prefer matching files
    - Otherwise pick randomly
    """
    folder_id = extract_folder_id(drive_folder_url)
    if not folder_id or not google_api_key:
        return None

    files = list_folder_images(folder_id, google_api_key)
    if not files:
        return None

    # Try to match by keyword in filename
    chosen = None
    if keywords:
        kw_lower = " ".join(keywords).lower()
        scored = []
        for f in files:
            name_lower = f["name"].lower()
            score = sum(1 for kw in keywords if kw.lower() in name_lower)
            scored.append((score, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored[0][0] > 0:
            chosen = scored[0][1]

    if not chosen:
        chosen = random.choice(files)

    image_bytes = _download_drive_image(chosen["id"])
    if not image_bytes:
        return None

    # Rehost via ImgBB if key available
    if imgbb_key:
        hosted_url = _upload_to_imgbb(image_bytes, imgbb_key, name=chosen["name"])
        if hosted_url:
            return hosted_url

    # Fallback: return direct Drive view URL (less stable but works for public files)
    return f"https://drive.google.com/uc?export=view&id={chosen['id']}"


# ─── AI Image Generation (Pollinations.ai — free, no key needed) ──────────────

def generate_ai_image(
    prompt: str,
    imgbb_key: str = "",
    width: int = 800,
    height: int = 534,
) -> str | None:
    """
    Generate an image using Pollinations.ai (free, no API key required).
    Optionally rehost on ImgBB for stability.

    Returns hosted URL or None on failure.
    """
    if not prompt:
        return None

    # Clean and encode prompt
    clean_prompt = re.sub(r"[^\w\s,.-]", " ", prompt).strip()[:200]
    seed = random.randint(1, 99999)
    encoded = urllib.parse.quote(clean_prompt)
    url = f"{POLLINATIONS_URL.format(prompt=encoded)}?width={width}&height={height}&nologo=true&seed={seed}"

    try:
        with httpx.Client(timeout=45, follow_redirects=True) as c:
            r = c.get(url)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                image_bytes = r.content
                if len(image_bytes) > 5000:
                    if imgbb_key:
                        hosted = _upload_to_imgbb(image_bytes, imgbb_key, name="ai-image")
                        if hosted:
                            logger.info("AI image generated + hosted: %s", hosted)
                            return hosted
                    # Return direct Pollinations URL if ImgBB fails
                    logger.info("AI image generated (pollinations): %s", url)
                    return url
    except Exception as e:
        logger.warning("Pollinations AI image error: %s", e)

    return None
