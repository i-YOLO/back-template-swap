import pandas as pd
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/2a1f54e725154a56bd24606f28b283f2?enable=archive'))

# csv表的数据格式
data = {
    'transactionHash': [],
    'blockNumber': [],
    'sender': [],
    'to': [],
    'amount0In': [],
    'amount1In': [],
    'amount0Out': [],
    'amount1Out': [],
}


# 处理日志信息
def deal_logs(swap_logs):
    for log in swap_logs:
        # 解析事件参数
        event_args = log.args
        # 将log日志存放到data中
        data['transactionHash'].append(log.transactionHash.hex())
        data['blockNumber'].append(log.blockNumber)
        data['sender'].append(event_args.sender)
        data['to'].append(event_args.to)
        data['amount0In'].append(event_args.amount0In)
        data['amount1In'].append(event_args.amount1In)
        data['amount0Out'].append(event_args.amount0Out)
        data['amount1Out'].append(event_args.amount1Out)


# 查询一般1年的Swap事件日志数据
# 注意，此处不带时间戳，无法直接转化为k线数据进行图形绘制
# 需要执行append_timestamp_to_logs文件主函数，才能成功获取swap事件的时间戳
def get_logs():
    if not w3.is_connected():
        raise Exception("节点连接失败，请重试!")

    # ASTRA-15交易对合约地址
    PAIR_ADDRESS = Web3.to_checksum_address("0x4df1c47ecfbac8482a4811d373128e2acc007d02")

    # UniSwap-V2-Pair合约ABI
    PAIR_ABI = [
        {
            "constant": True,
            "inputs": [],
            "name": "token0",
            "outputs": [{"name": "", "type": "address"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "token1",
            "outputs": [{"name": "", "type": "address"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "getReserves",
            "outputs": [
                {"name": "reserve0", "type": "uint112"},
                {"name": "reserve1", "type": "uint112"},
                {"name": "blockTimestampLast", "type": "uint32"}
            ],
            "type": "function"
        },
        # Swap事件ABI
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "sender", "type": "address"},
                {"indexed": False, "name": "amount0In", "type": "uint256"},
                {"indexed": False, "name": "amount1In", "type": "uint256"},
                {"indexed": False, "name": "amount0Out", "type": "uint256"},
                {"indexed": False, "name": "amount1Out", "type": "uint256"},
                {"indexed": True, "name": "to", "type": "address"}
            ],
            "name": "Swap",
            "type": "event"
        }
    ]

    # 创建 Pair 合约实例
    pair_contract = w3.eth.contract(address=PAIR_ADDRESS, abi=PAIR_ABI)

    swap_logs = []
    start_block = 18542170
    end_block = 20997856

    for start in range(start_block, end_block, 100000):
        try:
            # 分批获取（10000个区块每批）
            filter = pair_contract.events.Swap.create_filter(from_block=start, to_block=min(start + 100000, end_block))
            # 获取日志信息
            logs = filter.get_all_entries()
            # 将每一批的日志添加到末尾
            swap_logs.extend(logs)
        except:
            print("分批获取区块日志出现错误!")
            continue

    # 处理日志
    deal_logs(swap_logs)

    df = pd.DataFrame(data)
    df.to_csv("../files/swap.csv", index=False)


if __name__ == '__main__':
    get_logs()
