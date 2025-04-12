import pandas as pd

"""
此文件用于将swap.csv中存放的Swap事件日志（带时间戳），转化为k线数据（kline.csv文件）
"""


# 计算每笔交易的价格
def compute_price(row):
    # 根据不同方向计算价格
    if int(row['amount0In']) > 0 and int(row['amount1Out']) > 0:
        return int(row['amount1Out']) / int(row['amount0In'])
    elif int(row['amount1In']) > 0 and int(row['amount0Out']) > 0:
        return int(row['amount0Out']) / int(row['amount1In'])
    else:
        return None  # 或者设定默认值


def get_kline():
    df = pd.read_csv('../files/swap.csv')

    df['price'] = df.apply(compute_price, axis=1)

    # 如果需要计算成交量，可以类似地计算，比如取交易中输入或输出代币数量
    # 例如，假设我们以 token0 的数量作为成交量（视实际情况而定）
    df['volume'] = df['amount0In'] + df['amount0Out']
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df['volume'].fillna(0, inplace=True)

    # 将时间戳设置为索引
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    # 以固定时间间隔（例如1小时）进行重采样，计算OHLC和成交量
    # 注意：如果 df['price'] 有空值，可能需要预先处理
    ohlc = df['price'].resample('1h').ohlc()
    vol = df['volume'].resample('1h').sum()

    # 合并生成K线数据
    kline = ohlc.join(vol)

    # print(kline)

    # 将结果保存到 Excel
    kline.to_csv('../files/kline.csv')


# 注意：请忽略控制台的报错信息
# 存在版本兼容问题，但仍然能够正常使用
if __name__ == '__main__':
    get_kline()
