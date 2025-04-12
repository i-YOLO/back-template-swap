from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine, close_all_sessions
from sqlalchemy.orm import declarative_base, as_declarative, declared_attr


class CustomBase:
    def as_dict(self):
        """
        字典化 ORM 实例
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


Base = declarative_base(cls=CustomBase)

DatabaseFactory = async_sessionmaker[AsyncSession]


class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = 1
    max_overflow: int = 4
    autoflush: bool = True

    def __init__(
            self, url: str, *,
            pool_size: int = 1,
            max_overflow: int = 4,
            autoflush: bool = True
    ) -> None:
        super().__init__(
            url=url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            autoflush=autoflush
        )


def declare_database(config: DatabaseConfig | None = None, *, url: str | None = None, pool_size: int = 1,
                     max_overflow: int = 15, autoflush: bool = True) -> DatabaseFactory:
    """
    声明一个数据库连接工厂
    """
    if config is not None:
        url = config.url
        pool_size = config.pool_size
        max_overflow = config.max_overflow
        autoflush = config.autoflush
    assert url is not None, "url is required"
    return async_sessionmaker(
        create_async_engine(url) if url.startswith('sqlite') else
        create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
        ),
        class_=AsyncSession,
        autoflush=autoflush,
        expire_on_commit=False
    )
