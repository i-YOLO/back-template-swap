from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from middleware import RequestMiddleware, SecurityStatus, Request
from middleware.apploader import register_by
from views.render import *
from middleware.lifespan import on_startup, on_shutdown, lifespan_context
from .views import on_init
import settings
import logging
import warnings
import traceback
import sys

logger = logging.getLogger('app')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s][%(pathname)s:%(lineno)s]%(message)s'))
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)
httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.WARNING)


def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
    print(f"Warning message: {message}")
    print(f"Warning category: {category.__name__}")
    print(f"Warning filename: {filename}")
    print(f"Warning lineno: {lineno}")
    stack = traceback.extract_stack()
    print("Traceback (most recent call last):")
    for entry in stack[:-1]:
        print(f"  File \"{entry.filename}\", line {entry.lineno}, in {entry.name}")
        if entry.line:
            print(f"    {entry.line.strip()}")


warnings.showwarning = custom_warning_handler

__all__ = ['app', 'on_startup', 'on_shutdown']

app = FastAPI(
    # docs_url=None,
    # redoc_url=None,
    # openapi_url=None,
    lifespan=lifespan_context,
    dependencies=[],
    exception_handlers={
        # RequestValidationError: lambda request, exc: JSONResponse(content={
        #     "code": -127, "message": "parameter mismatch error", "data": None
        # }, status_code=422),
        HTTPException: HTTPException.handler,
    })

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(
#     RequestMiddleware,
#     check_salt=settings.CHECK_SALT,
#     jwt_secret=None,
#     url_filters=settings.URL_FILTERS,
# )


on_init(app)


def api_router_register(obj: APIRouter):
    app.include_router(obj)
    return True


register_by('on_init', app, api_router_register)
