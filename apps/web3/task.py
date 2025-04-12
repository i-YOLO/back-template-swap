from typing import Any

from starlette.exceptions import HTTPException
from web3 import AsyncWeb3

from tasks import TaskEntry, AppContext
from data import Context
from data.logger import create_logger
import asyncio

from web3_db import insert_block, query
from .views import w3, Block

logger = create_logger('web3.task')


def task_register(app: AppContext):
    # 定时任务，每12s查询最新区块的数据
    @app.loop('web3')
    async def web3_task_worker(task: TaskEntry, context: Context):
        while True:
            # 连接
            if not await w3.is_connected():
                raise HTTPException(status_code=404, detail="节点连接失败，请重试!")

            # 获取最新的区块
            block = await w3.eth.get_block('latest')

            # 将区块数据转换为字典对象
            block_data = {
                'number': block.number,
                'hash': block.hash.hex(),
                'timestamp': block.timestamp,
                'transactions': ",".join([tx.hex() for tx in block.transactions])
            }

            # 将查询到的数据，存入到sqlite本地数据库
            await insert_block(block_data)
            print("定时插入成功")

            block_list = await query()
            print(block_list)

            # 休眠12s
            await asyncio.sleep(12)
            print("休眠结束")
