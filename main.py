from fastapi import FastAPI
from fastapi import Request
from fastapi.params import Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from routers.api.url_shorter import router as url_shorter_router
from routers.api.auth import router as register_router
from routers.web.pages import router as web_pages_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")



# WEB routers :

app.include_router(web_pages_router)


# API routers :

app.include_router(register_router, prefix="/api/auth")

app.include_router(url_shorter_router, prefix="/api", tags=["API"])
