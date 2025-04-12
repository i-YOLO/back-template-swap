from pyecharts import options as opts
from pyecharts.charts import Kline, Bar, Grid, Line
from pyecharts.commons.utils import JsCode
import pandas as pd

"""
根据kline.csv文件绘制k线图（带交易量）
"""


# 绘制k线（带交易量）
def generate_kline_with_volume(data):
    # k线
    kline = (
        Kline(
            init_opts=opts.InitOpts(width="800px", height="600px"))
        .add_xaxis(xaxis_data=list(data['timestamp']))
        .add_yaxis(
            series_name="klines",
            y_axis=data[["open", "close", "low", "high"]].values.tolist(),
            itemstyle_opts=opts.ItemStyleOpts(
                color="#ef232a",
                color0="#14b143",
                border_color="#ef232a",
                border_color0="#14b143",
            ),
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="最大值"),
                    opts.MarkPointItem(type_="min", name="最小值"),
                ]
            ),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="UniSwap-V2 Swap事件 K线周期图表", pos_left="0"),
            legend_opts=opts.LegendOpts(is_show=True, pos_bottom=10, pos_left="center"),
            toolbox_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=98,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="85%",
                    range_start=98,
                    range_end=100,
                ),
            ],
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(color="#4A4A4A")  # 网格线颜色
                ),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#00da3c"},
                    {"value": -1, "color": "#ec0000"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
            brush_opts=opts.BrushOpts(
                x_axis_index="all",
                brush_link="all",
                out_of_brush={"colorAlpha": 0.1},
                brush_type="lineX",
            )
        )
    )

    # 交易量
    bar = (
        Bar()
        .add_xaxis(xaxis_data=list(data.index))
        .add_yaxis(
            series_name="volume",
            y_axis=data["volume"].tolist(),
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                color=JsCode(
                    """
                function(params) {
                    var colorList;
                    if (barData[params.dataIndex][1] > barData[params.dataIndex][0]) {
                        colorList = '#ef232a';
                    } else {
                        colorList = '#14b143';
                    }
                    return colorList;
                }
                """
                )
            ),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )

    )

    # 两条均线
    line = (Line()
    .add_xaxis(xaxis_data=list(data['timestamp']))
    .add_yaxis(
        series_name="MA6",
        y_axis=data["MA6"].tolist(),
        xaxis_index=1,
        yaxis_index=1,
        label_opts=opts.LabelOpts(is_show=False),
    ).add_yaxis(
        series_name="MA12",
        y_axis=data["MA12"].tolist(),
        xaxis_index=1,
        yaxis_index=1,
        label_opts=opts.LabelOpts(is_show=False),
    )
    )

    # 表格
    grid_chart = Grid(
        init_opts=opts.InitOpts(
            width="1800px",
            height="1000px",
            animation_opts=opts.AnimationOpts(animation=False),
        )
    )

    grid_chart.add_js_funcs("var barData={}".format(data[["open", "close"]].values.tolist()))

    overlap_kline_line = kline.overlap(line)

    # 组合表格
    # 1. k线
    grid_chart.add(
        overlap_kline_line,
        grid_opts=opts.GridOpts(pos_left="11%", pos_right="8%", height="40%"),
    )
    # 2. 交易量
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="10%", pos_right="8%", pos_top="60%", height="20%"
        ),
    )

    # 产生对应的html文件
    grid_chart.render("../templates/UniSwap-V2_Kline_with_Volume.html")


if __name__ == '__main__':
    df = pd.read_csv('../files/kline.csv')

    # 均线配置
    df['MA6'] = df['close'].rolling(window=4).mean()
    df['MA12'] = df['close'].rolling(window=8).mean()

    # 异常数据过滤
    df = df[(df['low'] > 0.0001) &  # 最低价不能小于0.001
            (df['high'] > df['low']) &  # 最高价必须大于最低价
            (df['high'] >= df['close']) &  # 最高价>=收盘价
            (df['low'] <= df['open']) &  # 最低价<=开盘价
            # 波动率过滤（排除极端值）
            ((df['high'] / df['low']) < 1.5)  # 单根K线波动不超过50%
            ]

    # print((df['close'] > df['open']).value_counts())

    # 绘制k线（html）
    generate_kline_with_volume(df)
