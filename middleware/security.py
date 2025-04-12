import base64
from enum import Enum
from typing import Callable, Any, Mapping
from pydantic import BaseModel
import hmac
import hashlib
import time
from jose import jwt, exceptions as jwt_exc
import json


class SecurityStatus(Enum):
    UNKNOWN = -1
    AUTHORIZED = 0

    NO_AUTH = 1000
    INVALID_SCHEMA = 1001
    UNSUPPORTED_SCHEMA = 1002
    AUTH_ERROR = 1003
    AUTH_FAILED = 1004
    AUTH_EXPIRED = 1005


class SecurityData(BaseModel):
    auth: str
    verified: bool
    certificated: SecurityStatus
    data: dict[str, Any] = {}

    @property
    def status(self) -> int:
        match self.certificated:
            case SecurityStatus.AUTHORIZED: return 200
            case SecurityStatus.NO_AUTH: return 401
            case SecurityStatus.INVALID_SCHEMA: return 403
            case SecurityStatus.UNSUPPORTED_SCHEMA: return 501
            case SecurityStatus.AUTH_ERROR: return 400
            case SecurityStatus.AUTH_FAILED: return 401
            case SecurityStatus.AUTH_EXPIRED: return 401
            case _: return 500

    @property
    def code(self) -> int:
        value = self.certificated.value
        if value >= 1000:
            return value + 99101
        return value

    @property
    def response(self) -> dict[str, int | str]:
        return {
            'code': self.code,
            'message': self.certificated.name.capitalize().replace('_', ' '),
            'status': self.status,
        }

    @classmethod
    def ok(cls, auth: str, data: dict[str, Any] | None = None) -> 'SecurityData':
        return SecurityData(
            auth=auth,
            verified=True,
            certificated=SecurityStatus.AUTHORIZED,
            data=data or {},
        )

    def with_certificated(self, certificated: SecurityStatus, data: dict[str, Any] | None = None) -> 'SecurityData':
        return SecurityData(
            auth=self.auth,
            verified=self.verified,
            certificated=certificated,
            data=self.data | (data or {}),
        )

    def __str__(self):
        return json.dumps(self.response | {'data': self.data}, indent=4)


def check_checkcode(check_salt: bytes, check_code: str, timestamp: int) -> bool:
    # 计算当前时间戳所在的分钟的开始时间
    now = timestamp - timestamp % 60
    # 根据时间戳的秒数决定是检查前一分钟还是后一分钟
    other = now - 60 if timestamp % 60 < 30 else now + 60
    # 检查当前分钟、前一分钟或后一分钟的时间戳
    for ts in [now, other]:
        digest = hmac.new(check_salt, ts.to_bytes(4, 'big'), hashlib.sha256).hexdigest()
        if digest == check_code:
            return True
    return False


class SecurityCheckerBase:
    def get_all_schema(self) -> list[str]:
        return [name[8:] for name in dir(self) if name.startswith('checker_')]

    def authorize(self, headers: Mapping[str, str]) -> SecurityData:
        authorization = headers.get('Authorization', '').strip()
        failed_result = SecurityData(
            auth=authorization,
            verified=False,
            certificated=SecurityStatus.UNKNOWN,
        )
        if not authorization:
            return failed_result.with_certificated(SecurityStatus.NO_AUTH)
        if ' ' not in authorization:
            return failed_result.with_certificated(SecurityStatus.INVALID_SCHEMA)
        schema, token = authorization.split(' ', 1)
        if checker := getattr(self, f'checker_{schema.lower()}', None):
            return checker(token, headers)
        return failed_result.with_certificated(SecurityStatus.UNSUPPORTED_SCHEMA)


class RS256Checker(SecurityCheckerBase):
    def __init__(self, public_key: str | dict[str, Any]) -> None:
        self._public_key = public_key

    def checker_bearer(self, token: str, headers: dict[str, str]) -> SecurityData:
        failed_result = SecurityData(
            auth=token,
            verified=False,
            certificated=SecurityStatus.AUTH_FAILED,
        )
        try:
            data = jwt.decode(token, self._public_key, algorithms=['RS256'], options={"verify_aud": False})
            return SecurityData(
                auth=token,
                verified=True,
                certificated=SecurityStatus.AUTHORIZED,
                data=data,
            )
        except jwt_exc.ExpiredSignatureError:
            return failed_result.with_certificated(SecurityStatus.AUTH_EXPIRED)
        except jwt_exc.JWTError:
            return failed_result
