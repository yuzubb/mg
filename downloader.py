import requests
import io
import zipfile
from urllib.parse import quote_plus
from typing import List, Dict

BASE_URL = "https://api.mangadex.org"
HEADERS = {
    "User-Agent": "MangaDownloader/1.0 (Personal use only; contact: your@email.com)"
}

def search_manga(query: str, limit: int = 10) -> List[Dict]:
    url = f"{BASE_URL}/manga"
    params = {
        "title": query,
        "limit": limit,
        "includes[]": "cover_art",
        "availableTranslatedLanguage[]": ["en", "ja"],  # 英語/日本語対応作品優先
        "order[relevance]": "desc",  # 関連度順
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", []):
            attrs = item["attributes"]
            title_en = attrs["title"].get("en") or ""
            title_ja = attrs["title"].get("ja") or ""
            display_title = title_en or title_ja or "No title"
            alt_titles = [t.get("ja") or t.get("en") for t in attrs.get("altTitles", []) if t]
            results.append({
                "id": item["id"],
                "title": display_title,
                "alt_titles": alt_titles,
                "description": attrs.get("description", {}).get("en", "")[:200] + "...",
                "year": attrs.get("year"),
                "status": attrs.get("status"),
                "cover_id": next((r["id"] for r in item.get("relationships", []) if r["type"] == "cover_art"), None)
            })
        return results
    except Exception as e:
        raise ValueError(f"Search failed: {str(e)}")

def get_chapters(manga_id: str, language: str = "en", limit: int = 100) -> List[Dict]:
    url = f"{BASE_URL}/manga/{manga_id}/feed"
    params = {
        "translatedLanguage[]": [language],
        "limit": limit,
        "order[chapter]": "asc",  # 1話から順
        "includeFutureUpdates": 0,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        chapters = []
        for ch in data.get("data", []):
            attrs = ch["attributes"]
            chapters.append({
                "id": ch["id"],
                "chapter": attrs.get("chapter", "N/A"),
                "title": attrs.get("title", ""),
                "volume": attrs.get("volume", ""),
                "pages": attrs.get("pages", 0),
            })
        return chapters
    except Exception as e:
        raise ValueError(f"Chapters fetch failed: {str(e)}")

def get_chapter_images(chapter_id: str) -> List[str]:
    url = f"{BASE_URL}/at-home/server/{chapter_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        base_url = data["baseUrl"]
        chapter_hash = data["chapter"]["hash"]
        filenames = data["chapter"]["data"]  # 高画質
        # dataSaver で低画質も可能: data["chapter"]["dataSaver"]
        images = [f"{base_url}/data/{chapter_hash}/{fn}" for fn in filenames]
        return images
    except Exception as e:
        raise ValueError(f"Image fetch failed: {str(e)}")

def create_zip_from_images(images: List[str], title: str, chapter: str) -> (io.BytesIO, str):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for i, img_url in enumerate(images):
            try:
                r = requests.get(img_url, headers=HEADERS, timeout=15, stream=True)
                r.raise_for_status()
                zipf.writestr(f"{i+1:03d}.jpg", r.content)
            except Exception:
                pass  # 失敗したらスキップ
    zip_buffer.seek(0)
    safe_title = title.replace(" ", "_").replace("/", "_")[:50]
    filename = f"{safe_title}_Ch{chapter}.zip"
    return zip_buffer, filename
