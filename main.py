from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from downloader import search_manga, get_chapters, create_zip_from_images, get_chapter_images

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "results": [], "error": None})

@app.post("/search")
async def do_search(request: Request, query: str = Form(...)):
    try:
        results = search_manga(query, limit=15)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "results": results,
            "query": query,
            "error": None
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

@app.get("/chapters/{manga_id}")
async def show_chapters(request: Request, manga_id: str):
    try:
        chapters = get_chapters(manga_id, language="en")  # 必要なら "ja"
        title = request.query_params.get("title", "Manga")
        return templates.TemplateResponse("chapters.html", {
            "request": request,
            "chapters": chapters,
            "title": title,
            "manga_id": manga_id
        })
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/download/{chapter_id}")
async def download_chapter(chapter_id: str, title: str, chapter: str):
    try:
        images = get_chapter_images(chapter_id)
        if not images:
            raise ValueError("No images found")
        zip_buffer, filename = create_zip_from_images(images, title, chapter)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))
