import requests
import io
import zipfile
from urllib.parse import quote_plus
from typing import List, Dict, Optional

BASE_URL = "https://api.mangadex.org"
UPLOADS_URL = "https://uploads.mangadex.org/covers"
HEADERS = {
    "User-Agent": "MangaDownloader/1.0 (Personal use only)"
}

def search_manga(query: str, limit: int = 15) -> List[Dict]:
    url = f"{BASE_URL}/manga"
    params = {
        "title": query,
        "limit": limit,
        "includes[]": ["cover_art"],
        "availableTranslatedLanguage[]": ["en", "ja"],
        "order[relevance]": "desc",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", []):
            attrs = item["attributes"]
            title_en = attrs["title"].get("en")
            title_ja = attrs["title"].get("ja")
            display_title = title_en or title_ja or next(iter(attrs["title"].values()), "No Title")
            alt_titles = [t.get("ja") or t.get("en") for t in attrs.get("altTitles", []) if any(t.values())]

            # cover_art関係からcover_id取得
            cover_id = next(
                (r["id"] for r in item.get("relationships", []) if r["type"] == "cover_art"),
                None
            )
            cover_url = None
            if cover_id:
                cover_url = get_cover_url(item["id"], cover_id)

            results.append({
                "id": item["id"],
                "title": display_title,
                "alt_titles": alt_titles,
                "description": attrs.get("description", {}).get("en") or attrs.get("description", {}).get("ja", "")[:200] + "...",
                "year": attrs.get("year"),
                "status": attrs.get("status"),
                "cover_url": cover_url or "https://via.placeholder.com/200x300?text=No+Cover",
            })
        return results
    except Exception as e:
        raise ValueError(f"Search failed: {str(e)}")

def get_cover_url(manga_id: str, cover_id: str) -> Optional[str]:
    url = f"{BASE_URL}/cover/{cover_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            attrs = resp.json()["data"]["attributes"]
            filename = attrs["fileName"]
            return f"{UPLOADS_URL}/{manga_id}/{filename}.512.jpg"  # thumbnail 512px
        return None
    except Exception:
        return None

def get_chapters(manga_id: str, preferred_lang: str = "en") -> List[Dict]:
    languages = [preferred_lang, "ja"] if preferred_lang == "en" else ["ja", "en"]
    for lang in languages:
        url = f"{BASE_URL}/manga/{manga_id}/feed"
        params = {
            "translatedLanguage[]": [lang],
            "limit": 500,
            "order[chapter]": "asc",
            "includeFutureUpdates": 0,
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                chapters = []
                for ch in data.get("data", []):
                    attrs = ch["attributes"]
                    chapters.append({
                        "id": ch["id"],
                        "chapter": attrs.get("chapter", "Extra/Special"),
                        "title": attrs.get("title", ""),
                        "volume": attrs.get("volume", "?"),
                        "pages": attrs.get("pages", 0),
                    })
                if chapters:
                    return chapters
        except Exception:
            continue
    return []  # 両言語で章なし

def get_chapter_images(chapter_id: str) -> List[str]:
    url = f"{BASE_URL}/at-home/server/{chapter_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        base_url = data["baseUrl"]
        chapter_hash = data["chapter"]["hash"]
        filenames = data["chapter"]["data"]  # 高画質優先
        return [f"{base_url}/data/{chapter_hash}/{fn}" for fn in filenames]
    except Exception as e:
        raise ValueError(f"Images fetch failed: {str(e)}")

def create_zip_from_images(images: List[str], title: str, chapter: str) -> tuple[io.BytesIO, str]:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for i, img_url in enumerate(images):
            try:
                r = requests.get(img_url, headers=HEADERS, timeout=15, stream=True)
                r.raise_for_status()
                ext = img_url.split('.')[-1].split('?')[0] or 'jpg'
                zipf.writestr(f"{i+1:03d}.{ext}", r.content)
            except Exception:
                pass
    zip_buffer.seek(0)
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:50]
    filename = f"{safe_title}_Ch{chapter}.zip"
    return zip_buffer, filename
