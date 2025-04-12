from typing import List
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from io import BytesIO
from web3 import AsyncWeb3
from starlette.exceptions import HTTPException
from pydantic import BaseModel, field_validator
import starlette.requests
from starlette.templating import Jinja2Templates
from data import create_logger
from web3_db import get_blocks, get_block, insert_block, query

"""
路由文件，路径：/api/v1/web3
"""

logger = create_logger('web3.views')

router = APIRouter(prefix='/api/v1/web3')

# 注：填写以main.py文件作为起始，来填目录
templates = Jinja2Templates(directory='templates')

# 使用异步的Web3库组件
w3 = AsyncWeb3(
    AsyncWeb3.AsyncHTTPProvider('https://mainnet.infura.io/v3/2a1f54e725154a56bd24606f28b283f2?enable=archive'))


# 区块信息
class Block(BaseModel):
    number: int
    hash: str
    timestamp: int
    transactions: str  # 交易哈希列表


# 范围
class Range(BaseModel):
    start: int
    end: int

    @field_validator('end')
    def enforce_range(cls, v, values):
        start_value = values.data['start']
        if start_value is not None and start_value >= v:
            raise ValueError(f'起始区块号({start_value})必须小于结束区块号({v})')
        elif v - start_value > 100:
            raise ValueError(f'限制区块号相差只能在100以内!')
        return v


# 查询对应区块范围，并同步到数据库
async def query_blocks(numbers: list[int]):
    block_list = []
    for number in numbers:
        try:
            block = await w3.eth.get_block(number)
        except Exception as e:
            print('部分区块找不到!')
            continue
        finally:
            # 将区块数据转换为模型实例
            block_data = {
                'number': block.number,
                'hash': block.hash.hex(),
                'timestamp': block.timestamp,
                'transactions': ",".join([tx.hex() for tx in block.transactions])
            }
            block_list.append(block_data)
    # 批量插入数据库
    await insert_block(block_list)


# 根据区块号获取区块数据
@router.get("/{number}", response_model=Block, summary='获取特定区块的数据（number示例：22106262）')
async def get_by_block_number(number: int):
    # 连接
    if not await w3.is_connected():
        raise HTTPException(status_code=404, detail="节点连接失败，请重试!")

    # 先从sqlite数据库获取
    block = await get_block(number)
    # 有，则直接return
    if block is not None:
        print("数据库存在，直接返回")
        return block

    # 没有，则查询链上数据
    # 获取区块
    try:
        block = await w3.eth.get_block(number)
    except Exception as e:
        raise HTTPException(status_code=404, detail="未找到对应区块!")

    # 将区块数据转换为字典对象
    block_data = {
        'number': block.number,
        'hash': block.hash.hex(),
        'timestamp': block.timestamp,
        'transactions': ",".join([tx.hex() for tx in block.transactions])
    }
    # print(block_data)

    # 将查询到的数据，存入到sqlite本地数据库
    await insert_block(block_data)  # 转化为字典对象，sqlalchemy数据库操作要求！

    inserted_block = await get_block(number)  # 新增检查
    assert inserted_block is not None
    print(
        f"number: {inserted_block.number}, hash: {inserted_block.hash}, timestamp: {inserted_block.timestamp}, transactions: {inserted_block.transactions}")

    # 返回
    return block_data


# 获取区块范围内的数据（查询数据库）
@router.post('/range', response_model=List[Block], summary='获取区块范围内的数据（区块号相差100以内）')
async def get_blocks_by_range(block_range: Range, tasks: BackgroundTasks):
    # 连接
    if not await w3.is_connected():
        raise HTTPException(status_code=404, detail="节点连接失败，请重试!")

    # 修改前：一个个获取
    """
    # 后续返回的结果集
    block_list = []
    for number in range(block_range.start, block_range.end):
        try:
            block = await w3.eth.get_block(number)
        except Exception as e:
            print(f'部分区块找不到!')
            continue
        finally:
            # 将区块数据转换为模型实例
            block_data = Block(
                hash=block.hash.hex(),
                number=block.number,
                timestamp=block.timestamp,
                transactions=[tx.hex() for tx in block.transactions]
            )
            block_list.append(block_data)
    """

    # 修改后：直接从本地sqlite数据库中获取
    # 后续返回的结果集
    block_list = await get_blocks(block_range.start, block_range.end)
    # 将数据库获取到的字典对象，转化为对应pydantic模型实例
    block_list = [Block.model_validate(block) for block in block_list]

    # 获取区块号列表
    numbers = list(range(block_range.start, block_range.end))
    # 取差集
    numbers = list(set(numbers).difference(set([block.number for block in block_list])))

    # print(numbers)

    # 开启一个后台任务去查询对应区块范围（只查在数据库中不存在的区块）的数据，并同步到数据库中
    tasks.add_task(query_blocks, numbers)

    return block_list


# 获取数据库中的前100条区块数据，按照时间戳排序
@router.get("/block/news", response_model=List[Block], summary='获取数据库中最新的100条区块数据')
async def get_new_blocks():
    block_list = await query()
    return block_list


# 获取一版1年的Swap事件的Log数据
@router.get("/logs/download", summary='获取一版1年的Swap事件的Log数据（可下载）')
async def get_swap_logs_in_one_year():
    # 这个路径是相对main（也就是你创建的app所在的目录下而言的）
    file_path = "files/swap.csv"
    # 读取文件
    with open(file_path, "rb") as file:
        file_content = file.read()
    file_like = BytesIO(file_content)
    file_like.seek(0)
    headers = {"Content-Disposition": "attachment; filename=swap.csv"}
    return StreamingResponse(file_like, media_type="application/octet-stream", headers=headers)


# 获取一版1年Log数据计算出来的Swap事件绘制而成的K线
@router.get('/kline/html',
            summary='获取一版1年Log数据计算出来的Swap事件绘制而成的K线（注：需要通过接口直接访问！测试文档无法直接跳转！）')
async def get_kline(request: starlette.requests.Request):
    return templates.TemplateResponse('UniSwap-V2_Kline_with_Volume.html', {'request': request})
