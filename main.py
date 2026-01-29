from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from downloader import search_manga, get_chapters, create_chapter_zip

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "results": [], "error": None})

@app.post("/search")
async def do_search(request: Request, query: str = Form(...)):
    try:
        results = search_manga(query)
        return templates.TemplateResponse("index.html", {"request": request, "results": results, "query": query})
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

@app.get("/chapters/{manga_url:path}")
async def show_chapters(request: Request, manga_url: str):
    try:
        chapters = get_chapters(f"https://mangafire.to{manga_url}")
        title = request.query_params.get("title", "Manga")
        return templates.TemplateResponse("chapters.html", {
            "request": request,
            "chapters": chapters,
            "title": title,
            "manga_url": manga_url
        })
    except Exception as e:
        return {"error": str(e)}

@app.get("/download/{chapter_url:path}")
async def download_chapter(chapter_url: str, title: str, chapter: str):
    try:
        zip_buffer, filename = create_chapter_zip(f"https://mangafire.to{chapter_url}", title, chapter)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
