import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any
import os

# 更改字体
plt.rcParams['font.family'] = 'SimSun'

def read_stock_data(file_path: str) -> pd.DataFrame:
    """读取股票数据"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件：{file_path}")
    df = pd.read_csv(file_path, index_col='date', parse_dates=['date'])
    return df.sort_index()

def calculate_custom_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """计算自定义指标"""
    df['LC'] = df['close'].shift(1)
    df['VID'] = df['volume'].rolling(2).sum() / ((df['high'].rolling(2).max() - df['low'].rolling(2).min()) * 100)
    df['RC'] = (df['close'] - df['LC']) * df['VID']
    df['LONG'] = df['RC'].cumsum()
    
    df['DIFF'] = df['LONG'].rolling(10).mean()
    df['DEA'] = df['LONG'].rolling(20).mean()
    df['LON'] = df['DIFF'] - df['DEA']
    df['LLL'] = df['LON'].rolling(10).mean()
    
    df['V2'] = df['LON'].ewm(span=1).mean()
    df['V3'] = df['V2'].ewm(span=3).mean()
    df['V4'] = df['V3'].ewm(span=3).mean()
    df['V5'] = df['V4'].ewm(span=3).mean()
    df['V6'] = df['V5'].ewm(span=3).mean()

    df['buy_signal'] = np.where(df['V2'] > df['V2'].shift(1), 1, 0)
    df['sell_signal'] = np.where(df['V2'] < df['V2'].shift(1), 1, 0)
    
    return df

def backtest_strategy(df: pd.DataFrame, 
                      initial_capital: float = 500000, 
                      position_ratio: float = 0.3, 
                      stop_loss_pct: float = 0.05, 
                      take_profit_pct: float = 0.10) -> Dict[str, Any]:
    """
    回测交易策略
    
    :param df: 包含交易信号的DataFrame
    :param initial_capital: 初始资金，默认50万
    :param position_ratio: 仓位比例，默认0.3（30%仓位）
    :param stop_loss_pct: 止损百分比，默认5%
    :param take_profit_pct: 止盈百分比，默认10%
    :return: 包含回测结果的字典和更新后的DataFrame
    """
    cash = initial_capital
    stock_holding = 0
    entry_price = 0

    df['position'] = 0
    df['cash'] = initial_capital
    df['stock_holding'] = 0
    df['total_asset'] = initial_capital

    for i in range(1, len(df)):
        available_cash = cash * position_ratio

        current_price = df['close'].iloc[i]

        # 买入信号
        if df['buy_signal'].iloc[i] == 1 and stock_holding == 0:
            stock_holding = int(available_cash // current_price)
            entry_price = current_price
            cash -= stock_holding * entry_price
            df.loc[df.index[i], 'position'] = stock_holding

        # 卖出信号或止盈止损
        elif stock_holding > 0:
            current_return = (current_price - entry_price) / entry_price

            if df['sell_signal'].iloc[i] == 1 or current_return >= take_profit_pct or current_return <= -stop_loss_pct:
                cash += stock_holding * current_price
                stock_holding = 0
                df.loc[df.index[i], 'position'] = 0

        # 更新每日资产状况
        df.loc[df.index[i], 'cash'] = cash
        df.loc[df.index[i], 'stock_holding'] = stock_holding * current_price
        df.loc[df.index[i], 'total_asset'] = cash + df.loc[df.index[i], 'stock_holding']

    # 计算策略收益和风险指标
    df['daily_return'] = df['total_asset'].pct_change()
    df['strategy_return'] = (1 + df['daily_return']).cumprod() * initial_capital
    df['drawdown'] = (df['strategy_return'] / df['strategy_return'].cummax()) - 1

    total_return = (df['total_asset'].iloc[-1] - initial_capital) / initial_capital
    max_drawdown = df['drawdown'].min()
    
    # 处理可能的 NaN 值
    if np.isnan(df['daily_return']).all():
        sharpe_ratio = 0
    else:
        sharpe_ratio = np.sqrt(252) * df['daily_return'].mean() / df['daily_return'].std()
    
    non_zero_returns = df['daily_return'][df['daily_return'] != 0]
    if len(non_zero_returns) > 0:
        win_rate = len(non_zero_returns[non_zero_returns > 0]) / len(non_zero_returns)
    else:
        win_rate = 0

    results = {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'final_asset': df['total_asset'].iloc[-1]
    }

    return results, df

def plot_results(df: pd.DataFrame, stock_code: str):
    """绘制回测结果图表"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    # 绘制资产曲线
    ax1.plot(df.index, df['total_asset'], label='总资产')
    ax1.plot(df.index, df['cash'], label='现金', alpha=0.7)
    ax1.plot(df.index, df['stock_holding'], label='股票持仓', alpha=0.7)
    ax1.set_ylabel('资产价值')
    ax1.legend()
    ax1.set_title(f"{stock_code} 回测结果")

    # 绘制买卖信号
    ax2.plot(df.index, df['close'], label='收盘价', alpha=0.7)
    ax2.scatter(df.index[df['buy_signal'] == 1], df.loc[df['buy_signal'] == 1, 'close'], 
                color='green', marker='^', label='买入信号')
    ax2.scatter(df.index[df['sell_signal'] == 1], df.loc[df['sell_signal'] == 1, 'close'], 
                color='red', marker='v', label='卖出信号')
    ax2.set_ylabel('股票价格')
    ax2.legend()

    plt.tight_layout()
    plt.show()

def run_backtest(stock_code: str, file_path: str, initial_capital: float = 500000, position_ratio: float = 0.3):
    """运行单个股票的回测"""
    print(f"正在回测 {stock_code}...")
    
    # 读取数据
    df = read_stock_data(file_path)
    
    # 计算指标
    df = calculate_custom_indicator(df)
    
    # 运行回测
    results, df_with_signals = backtest_strategy(df, initial_capital, position_ratio)
    
    # 输出回测结果
    print(f"{stock_code} 回测结果：")
    print(f"总收益率: {results['total_return']:.2%}")
    print(f"最大回撤: {results['max_drawdown']:.2%}")
    print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    print(f"胜率: {results['win_rate']:.2%}")
    print(f"最终资产: ¥{results['final_asset']:,.2f}")
    print()
    
    # 绘制结果图表
    plot_results(df_with_signals, stock_code)
    
    # 保存回测结果
    output_file = f"{stock_code}_backtest_result.csv"
    df_with_signals.to_csv(output_file, index=True)
    print(f"回测结果已保存到 {output_file}")

def main():
    # 定义要回测的股票列表
    stocks_to_test = [
        {"code": "sz300454", "file": "D:/stock_app/data/tdx/day/sz300454.csv"},
        # 添加更多股票...
        # {"code": "sh600000", "file": "D:/stock_app/data/tdx/day/sh600000.csv"},
    ]
    
    # 设置回测参数
    initial_capital = 1000000  # 100万初始资金
    position_ratio = 0.3      # 30%仓位
    
    # 对每个股票进行回测
    for stock in stocks_to_test:
        run_backtest(stock["code"], stock["file"], initial_capital, position_ratio)

if __name__ == "__main__":
    main()