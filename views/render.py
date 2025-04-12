from typing import Any, Mapping
from fastapi.requests import Request as BaseRequest
from fastapi.responses import JSONResponse, PlainTextResponse, Response as BaseResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from starlette.types import ExceptionHandler
from starlette.background import BackgroundTask
from typing_extensions import Annotated, Doc
from decimal import Decimal
import json as jsonlib


__all__ = ['Text', 'Json', 'HTTPException']


class Text(PlainTextResponse):
    @staticmethod
    def process_str_content(content: str) -> str:
        return content.rstrip("\n") + '\n'

    def __init__(self,
                 content: Any = None,
                 *,
                 status_code: int | None = None,
                 status: int | None = None,
                 headers: Mapping[str, str] | None = None,
                 background: BackgroundTask | None = None
                 ) -> None:
        if isinstance(content, list):
            content = ''.join([self.process_str_content(str(s)) for s in content])
        elif isinstance(content, str):
            content = self.process_str_content(content)
        super().__init__(content, status_code or status or 200, headers, None, background)


class JsonResponseEncoder(jsonlib.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj.quantize(Decimal('0.000000000000000001')))
        return super().default(obj)


class Pagination:
    pass


class Json(BaseResponse):
    media_type = 'application/json'

    def __init__(self,
                 content: Any = None,
                 *,
                 code: int = 0,
                 message: str = 'ok',
                 status_code: int | None = None,
                 status: int | None = None,
                 headers: Mapping[str, str] | None = None,
                 background: BackgroundTask | None = None
                 ) -> None:
        super().__init__({
            'code': code,
            'message': message,
            'data': content
        }, status_code or status or 200, headers, None, background)

    def render(self, content: Any) -> bytes:
        return jsonlib.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
            cls=JsonResponseEncoder
        ).encode('utf-8')


class HTTPException(FastAPIHTTPException):
    def __init__(
        self,
        code: Annotated[
            int,
            Doc(
                """
                Json Response Code (Default -1)
                Not consistent with HTTP Status Code.
                """
            )
        ] = -1,
        message: Annotated[
            str,
            Doc(
                """
                Json Response Message (Default 'error')
                """
            )
        ] = 'error',
        status_code: Annotated[
            int | None,
            Doc(
                """
                HTTP Status Code (Default 400)
                """
            ),
        ] = None,
        status: Annotated[
            int | None,
            Doc(
                """
                HTTP Status Code (equivalent to status_code, but this field has a lower priority than status_code) (Default 400)
                """
            ),
        ] = None,
        data: Annotated[
            Any,
            Doc(
                """
                Any data to be sent to the client in the `data` key of the JSON
                response.
                """
            ),
        ] = None,
        headers: Annotated[
            dict[str, str],
            Doc(
                """
                Any headers to send to the client in the response.
                """
            ),
        ] = None,
    ) -> None:
        super().__init__(status_code or status or 400, {
            'code': code,
            'message': message,
            'data': data
        }, headers)
        self._code = code
        self._message = message
        self._data = data

    @property
    def code(self) -> int:
        """
        Json Response Code (Default -1)
        """
        return self._code

    @property
    def message(self) -> str:
        """
        Json Response Message (Default 'error')
        """
        return self._message

    @property
    def data(self) -> Any:
        """
        Any data to be sent to the client in the `data` key of the JSON
        response.
        
        Source: detail
        """
        return self._data

    @classmethod
    async def handler(cls, _request: BaseRequest, _exc: "HTTPException") -> Json:
        """
        Exception Handler for FastAPI
        """
        return Json(_exc.data, code=_exc.code, message=_exc.message, status_code=_exc.status_code, headers=_exc.headers)
