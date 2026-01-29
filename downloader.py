# downloader.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import zipfile
import io
import os

HEADERS = {'Referer': 'https://mangafire.to/', 'User-Agent': 'Mozilla/5.0'}

def search_manga(query: str):
    url = f"https://mangafire.to/search?keyword={quote_plus(query)}"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []
    for item in soup.select('.film-list .flw-item'):
        a = item.select_one('.film-name a')
        if a:
            results.append({
                'title': a.text.strip(),
                'url': urljoin("https://mangafire.to", a['href'])
            })
    return results

def get_chapters(manga_url: str):
    resp = requests.get(manga_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    chapters = []
    for li in soup.select('.manga-chapter .mc-item'):
        a = li.select_one('.chapter-name')
        if a:
            chapters.append({
                'number': a.text.strip(),
                'url': urljoin("https://mangafire.to", a['href'])
            })
    return chapters[::-1]  # 新→旧 なら逆に

def get_images(chapter_url: str):
    resp = requests.get(chapter_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    imgs = []
    for img in soup.select('.read-content img'):
        src = img.get('data-src') or img.get('src')
        if src:
            imgs.append(urljoin("https://mangafire.to", src))
    return imgs

def create_chapter_zip(chapter_url: str, title: str, chapter_num: str):
    images = get_images(chapter_url)
    if not images:
        raise ValueError("画像が見つかりませんでした")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, img_url in enumerate(images):
            try:
                r = requests.get(img_url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                zip_file.writestr(f"{i+1:03d}.jpg", r.content)
            except Exception as e:
                print(f"画像ダウンロード失敗: {img_url} - {e}")

    zip_buffer.seek(0)
    filename = f"{title.replace(' ', '_')}_{chapter_num.replace(' ', '_')}.zip"
    return zip_buffer, filename
