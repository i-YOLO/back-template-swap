from data import Context, rabbit, cache, db
from pydantic import BaseModel
from typing import Any, Callable, Awaitable
from data.logger import create_logger
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncEngine
from middleware.lifespan import startup_list, shutdown_list
import traceback
import logging
import asyncio
import settings
import random
import xxhash


class TaskEntry(BaseModel):
    task: str
    identity: str
    data: dict[str, Any]


class ErrorLogModel(BaseModel):
    msg_type: str = 'post'
    recv_name: str = '服务器报错'
    title: str | None = None
    content: list | dict | str
    identity: str | None = None

    @classmethod
    def exception(cls, exc_type: type[BaseException], exc_val: BaseException, tb: Any):
        return cls(
            title=f'QuickAlert Worker Exception[{exc_type.__name__}]: {exc_val}',
            content=[
                [
                    {
                        "tag": "text",
                        "text": ''.join(traceback.format_exception(exc_type, value=exc_val, tb=tb))
                    }
                ],
                [
                    {
                        "tag": "text",
                        "text": "服务器处理回调数据时发生错误，请尽快处理"
                    }
                ]
            ]
        )


TaskHandler = Callable[[Context, TaskEntry], Awaitable[None]] | Callable[[Context, TaskEntry], None]


NOW_RUNTIME_SEED = random.randint(0, 2**32 - 1)


class AppContext:
    def __init__(self, name: str):
        self.context: Context | None = None
        self.queues = name.split(';')
        self.logger = create_logger(f'Worker-{name}', logging.ERROR, True, False)
        self.callables: dict[str, TaskHandler] = {}
        self.loops: dict[str, Callable[['AppContext', Context], Awaitable[None]]] = {}
        self.loop_tasks: dict[str, asyncio.Task[None]] = {}

    def loop(self, loop_name: str):
        """
        注册循环任务
        """
        if loop_name.endswith('.worker'):
            raise ValueError("Loop name cannot end with '.worker'")
        def wrapper(func: Callable[['AppContext', Context], Awaitable[None]]):
            self.loops[loop_name] = func
            return func
        return wrapper

    def register(self, task: str):
        """
        注册任务处理函数
        """
        def wrapper(func: TaskHandler):
            self.callables[task] = func
            return func
        return wrapper

    async def __aenter__(self):
        self.context = Context(
            cache=cache.RedisConfig(settings.CACHE_URL),
            databases={
                key: db.DatabaseConfig(url)
                for key, url in settings.DATABASE_DICT.items()
            },
            rabbit=rabbit.RabbitConfig(settings.RABBIT_URL),
        )
        await self.context.initalize()
        return self

    def _task_done(self, task: asyncio.Task[None]):
        try:
            task.result()
            self.logger.info(f"Task {task.get_name()} Done!")
        except asyncio.CancelledError: pass
        except (KeyboardInterrupt, SystemExit): raise
        except Exception as e:
            self.logger.exception(f"Task {task.get_name()} failed: {e}")

    async def invoke(self, task: TaskEntry):
        assert self.context is not None, "Context is not initialized"
        if task.task in self.callables:
            # return asyncio.create_task(self.callables[task.task](self.context, task))
            if asyncio.iscoroutinefunction(self.callables[task.task]):
                await self.callables[task.task](self.context, task)
            else:
                self.callables[task.task](self.context, task)

    async def run_receiver(self, queue: str):
        async for task, message in self.context.amqp.receive(queue, TaskEntry):
            try:
                await self.invoke(task)
                await message.ack()
            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                raise
            except DatabaseError:
                self.logger.exception(f"Database error, restart all database session")
                await message.nack(requeue=True)
                await self.context.database.restart()
            except Exception as e:
                self.logger.exception(f"[{queue}]Task {task.task}({task.identity}) failed: {e}")
                await self.context.amqp.send('error-log', ErrorLogModel(
                    title='Worker事件处理出错',
                    content=[
                        [
                            {
                                "tag": "text",
                                "text": f"任务{task.task}({task.identity})执行失败: {e}\n"
                            },
                        ],
                        [
                            {
                                "tag": "text",
                                "text": self.context.traceback
                            }
                        ],
                        [
                            {
                                "tag": "text",
                                "text": f"\n{queue}-Worker监控将被阻塞，请尽快处理"
                            }
                        ]
                    ],
                    identity=xxhash.xxh3_128_hexdigest(f"{queue}-{task.task}-{task.identity}-{e}", NOW_RUNTIME_SEED)
                ))
                await message.nack(requeue=True)
                await asyncio.sleep(15)

    async def run(self):
        """
        运行任务消费服务
        """
        assert self.context is not None, "Context is not initialized"
        for startup in startup_list:
            await startup(self.context)
        for loop in self.loops:
            task = asyncio.create_task(self.loops[loop](self, self.context))
            task.add_done_callback(self._task_done)
            task.set_name(f"Worker-{self.queues}-Loop.{loop}")
            self.loop_tasks[loop] = task
        for queue in self.queues:
            task = asyncio.create_task(self.run_receiver(queue))
            task.add_done_callback(self._task_done)
            task.set_name(f"Worker-{queue}")
            self.loop_tasks[f'{queue}.worker'] = task
        await asyncio.gather(*self.loop_tasks.values())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self.context is not None, "Context is not initialized"
        for shutdown in shutdown_list:
            await shutdown(self.context)
        for task in self.loop_tasks.values():
            try: task.cancel()
            except: pass
        await self.context.close()
        self.context = None
        return False
