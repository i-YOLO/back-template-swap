import pandas as pd

"""
此文件用于获取所有Swap事件的时间戳
耗时会很久，如果不想自己跑一遍数据
可以使用files目录下的swap.csv文件，来获取绘制k线图所需要的数据
"""


# 获取区块时间戳
def get_block_timestamp(block_num):
    try:
        block = w3.eth.get_block(block_num)
        return pd.to_datetime(block.timestamp, unit='s')
    except:
        print("获取区块时间戳时出现异常!")
        return pd.to_datetime(0, unit='s')


if __name__ == '__main__':
    df = pd.read_csv('swap.csv')
    df['timestamp'] = df['blockNumber'].apply(get_block_timestamp)
    df.to_csv('swap.csv', index=False)
