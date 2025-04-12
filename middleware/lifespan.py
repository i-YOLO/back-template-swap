from contextlib import asynccontextmanager
from typing import Any, Callable, NoReturn, Awaitable
from fastapi import FastAPI
from data import Context, rabbit, cache, db
from .security import RS256Checker
import logging
import asyncio
import settings


logger = logging.getLogger('app')


LifespanCallable = Callable[..., Awaitable[None]] | Callable[..., Awaitable[NoReturn]]

# 公共列表区
startup_list: list[LifespanCallable] = []
shutdown_list: list[LifespanCallable] = []


def _startup_done(task: asyncio.Task[None]):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except:
        logger.exception(f"初始化{task.get_name()}发生异常")


def _shutdown_done(task: asyncio.Task[None]):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except:
        logger.exception(f"服务关闭处理{task.get_name()}发生异常")


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    # Startup
    app.state.context = Context(
        cache=cache.RedisConfig(settings.CACHE_URL),
        databases={
            key: db.DatabaseConfig(url)
            for key, url in settings.DATABASE_DICT.items()
        },
        rabbit=rabbit.RabbitConfig(settings.RABBIT_URL),
    )
    app.state.checker = RS256Checker(open('public.pem').read())

    async with app.state.context:
        for startup_coro_func in startup_list:
            task = asyncio.create_task(
                startup_coro_func(app), name=startup_coro_func.__name__
            )
            task.add_done_callback(_startup_done)

        # Running
        yield

        # Shutdown
        tasks: list[asyncio.Task[None]] = []
        for end_coro_func in shutdown_list:
            tasks.append(
                asyncio.create_task(end_coro_func(app), name=end_coro_func.__name__)
            )
            tasks[-1].add_done_callback(_shutdown_done)
        await asyncio.gather(*tasks)


def on_startup(
    func: LifespanCallable
):
    """
    配置初始化启动任务
    """
    startup_list.append(func)
    return func


def on_shutdown(
    func: LifespanCallable
):
    """
    配置服务停止处理任务
    """
    shutdown_list.append(func)
    return func