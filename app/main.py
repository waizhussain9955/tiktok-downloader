"""
FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router
from app.config import settings
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.api_prefix)

# Mount static directories
if os.path.exists("css"):
    app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("js"):
    app.mount("/js", StaticFiles(directory="js"), name="js")
if os.path.exists("img"):
    app.mount("/img", StaticFiles(directory="img"), name="img")

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/{page}.html")
async def read_page(page: str):
    file_path = f"{page}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"detail": "Not Found"}

@app.get("/robots.txt")
async def read_robots():
    return FileResponse("robots.txt")

@app.get("/sitemap.xml")
async def read_sitemap():
    return FileResponse("sitemap.xml")

# Health check at the root of the FastAPI app
@app.get("/api/health")
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "message": "Backend connected to index.html"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
