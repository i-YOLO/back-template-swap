import redis.asyncio as aioredis
from pydantic import BaseModel, Field, field_serializer, field_validator, computed_field, SerializationInfo
from typing import TypeVar, TypeVarTuple, Unpack, Any, overload, AsyncGenerator, Generator, Type, Tuple
import json as jsonlib
import asyncio
import yarl
import re


ModelType = TypeVar("ModelType", bound=BaseModel)
_Type = TypeVar("_Type")
_TypeGroup = TypeVarTuple("_TypeGroup")

__all__ = ["RedisConfig", "Cache"]


REDIS_URL_RE = re.compile(r'redis://(?::(?P<password>[^:@]+)@)?(?P<host>[^:@]+):(?P<port>\d+)/(?P<db>\d+)(?:\?(?P<query>.*))?')


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0
    encoding: str | None = None

    def __init__(self, url: str | yarl.URL | None = None, **kwargs):
        if url is not None:
            if isinstance(url, str):
                if '#' in url:
                    d = REDIS_URL_RE.match(url).groupdict()
                    url = yarl.URL(f"redis://{d['host']}:{d['port']}/{d['db']}{f'?{d['query']}' if d['query'] else ''}").with_password(d['password'])
                else: url = yarl.URL(url)
            kwargs.update({
                'host': url.host,
                'port': url.port,
                'password': url.password,
                'db': int(url.path[1:] or 0),
                'encoding': url.query.get('encoding'),
            })
        super().__init__(**kwargs)

    @field_serializer("encoding", when_used='always')
    @classmethod
    def serialize_encoding(cls, value: str | None):
        return value or 'utf-8'

    @computed_field
    @property
    def decode_responses(self) -> bool:
        return self.encoding is not None


class Cache:
    def __init__(
        self,
        config: RedisConfig | None = None,
        *,
        host: str | None = None,
        port: int = 6379,
        password: str | None = None,
        db: int | str = 0,
        loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        params = config.model_dump() if config is not None else {}
        if host is not None:
            params['host'] = host
        if port != 6379:
            params['port'] = port
        if password is not None:
            params['password'] = password
        if db != 0:
            params['db'] = db
        # 禁止使用 decode_responses 参数以及自定义 encoding
        self._redis = aioredis.Redis(**params)
        self._loop = loop or asyncio.get_event_loop()


    @property
    def backend(self) -> aioredis.Redis:
        """
        获取缓存的后端对象
        """
        return self._redis

    async def close(self):
        await self._redis.close()

    async def delete(self, key: str):
        """
        删除缓存中的数据
        
        :param key: 缓存键
        """
        await self._redis.delete(str(key))

    @overload
    async def get(self, key: str, model: Type[_Type], *,
                  strict: bool | None = None, context: dict[str, Any] | None = None) -> _Type | None:
        """
        获取缓存中的数据
        
        :param key: 缓存键
        :param model: 数据模型 (返回给定类型或 None)
        1. 如果指定为 pydantic 则会自动进行 json 反序列化
        2. 如果指定为 bytes 则直接返回原始 bytes 数据
        3. 如果指定为 str 则会使用 utf-8 解码
        4. 如果指定为 int 则会使用大端序转换
        5. 如果指定为其他类型则会使用 json.loads 进行反序列化并以该类型返回
        """
        ...

    @overload
    async def get(self, key: str, model: Type[Tuple[Unpack[_TypeGroup]]]) -> Tuple[Unpack[_TypeGroup]] | None:
        """
        获取缓存中的数据
        
        :param key: 缓存键
        :param model: 数据模型 (返回给定类型或 None)
        1. 如果指定为 pydantic 则会自动进行 json 反序列化
        2. 如果指定为 bytes 则直接返回原始 bytes 数据
        3. 如果指定为 str 则会使用 utf-8 解码
        4. 如果指定为 int 则会使用大端序转换
        5. 如果指定为其他类型则会使用 json.loads 进行反序列化并以该类型返回
        """
        ...

    @overload
    async def get(self, key: str) -> bytes | None:
        """
        获取缓存中的数据
        
        :param key: 缓存键
        
        :return: 原始 bytes 数据
        """
        ...

    async def get(self, key: str, model: Type[_Type] | Type[Tuple[Unpack[_TypeGroup]]] | None = None, *,
                  strict: bool | None = None, context: dict[str, Any] | None = None):
        key = str(key)
        data: bytes | None = await self._redis.get(key)
        if data is None:
            return None
        elif model is None or model is bytes:
            return data
        elif model is str:
            return data.decode()
        elif model is int:
            return int.from_bytes(data, 'big') # 总是使用大端序
        elif issubclass(model, BaseModel):
            return model.model_validate_json(data, strict=strict, context=context)
        else:
            return jsonlib.loads(data)


    @overload
    async def set(self, key: str, value: str | bytes, *, expire: float | int | None = None) -> None:
        """
        设置缓存数据
        
        :param key: 缓存键
        :param value: 缓存值(raw data)
        :param expire: 过期时间(毫秒)
        """
        ...

    @overload
    async def set(self, key: str, value: int, *, expire: float | int | None = None) -> None:
        """
        设置缓存数据
        
        :param key: 缓存键
        :param value: 缓存值(int的大端序字节数组)
        :param expire: 过期时间(毫秒)
        """
        ...

    @overload
    async def set(self, key: str, value: ModelType, *, expire: float | int | None = None, **dump_kws) -> None:
        """
        设置缓存数据
        
        :param key: 缓存键
        :param value: 缓存值(pydantic model)
        :param expire: 过期时间(毫秒)
        :param dump_kws: model_dump_json 的额外参数
        """
        ...

    @overload
    async def set(self, key: str, value: Any, *, expire: float | int | None = None, **dump_kws) -> None:
        """
        设置缓存数据
        
        :param key: 缓存键
        :param value: 缓存值(json serializable data)
        :param expire: 过期时间(毫秒)
        :param dump_kws: json.dumps 的额外参数
        """
        ...

    async def set(self, key: str, value: Any, *, expire: float | int | None = None, **dump_kws):
        key = str(key)
        if isinstance(expire, float):
            expire = int(expire * 1000)
        if isinstance(value, (str, bytes)):
            await self._redis.set(key, value, px=expire)
        elif isinstance(value, int):
            await self._redis.set(key, value.to_bytes((value.bit_length() + 7) // 8, 'big'), px=expire)
        elif isinstance(value, BaseModel):
            await self._redis.set(key, value.model_dump_json(**dump_kws), px=expire)
        else:
            await self._redis.set(key, jsonlib.dumps(value, **dump_kws), px=expire)
