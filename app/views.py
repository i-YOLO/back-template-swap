from fastapi import FastAPI, Depends
from middleware.request import Request
from views.render import Text, Json, HTTPException


def on_init(app: FastAPI):
    """
    加载根公共视图
    """

    @app.get('/', description="获取时间和IP")
    async def _(request: Request):
        request = Request.from_request(request)
        return Text([request.now, request.ip])

    @app.get('/ping', description="健康检查")
    async def _():
        return Text('pong')
