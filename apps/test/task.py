from typing import Any
from tasks import TaskEntry, AppContext
from data import Context
from data.logger import create_logger


logger = create_logger('test.task')


def task_register(app: AppContext):
    @app.register('test')
    async def test_task_worker(task: TaskEntry, context: Context):
        logger.info('Task worker is running')
