from data.rabbit import RabbitConfig, RabbitMQ
from pydantic import BaseModel
from typing import Union
import os


config = RabbitConfig(os.getenv('RABBIT_URL', 'amqp://user:password@localhost:5672/'),)


class TestDataModel(BaseModel):
    id: int
    name: str


async def producer():
    rabbit = RabbitMQ(config)
    await rabbit.ensure_connection()
    # 已连接
    await rabbit.send('test_queue', TestDataModel(id=1, name='test')) # 发送消息
    """
    此时的test_queue将有
    {
        "id": 1,
        "name": "test"
    }
    """
    await rabbit.close() # 关闭连接


async def consumer():
    rabbit = RabbitMQ(config)
    async for data, msg in rabbit.receive('test_queue', TestDataModel):
        try:
            print(data.model_dump_json(indent=2))
            await msg.ack()
        except Exception as e:
            await msg.reject(requeue=True)
            print(e)
    async for data, msg in rabbit.receive('test_queue_2', dict | list):
        try:
            print(data)
            await msg.ack()
        except Exception as e:
            await msg.reject(requeue=True)
            print(e)
