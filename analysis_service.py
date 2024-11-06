# analysis_service.py
from datetime import datetime, timedelta
import json
import logging
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import requests
from typing import Dict
from dotenv import load_dotenv
import os
import tushare as ts
from config import Settings
import matplotlib.font_manager as fm

load_dotenv()  # 加载 .env 文件
api_key = os.getenv('API_KEY')
model_name = os.getenv('MODEL_NAME')
api_url = os.getenv('API_URL')

class AnalysisService:
    def __init__(self, settings):
        self.settings = settings
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        

    def validate_dates(self, start_date: str, end_date: str) -> tuple:
        """验证并格式化日期"""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            today = datetime.now()
            
            if end > today:
                end = today

            if start > end:
                start = end - timedelta(days=30)
                
            return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
        except ValueError as e:
            raise ValueError(f"日期格式错误，请使用YYYY-MM-DD格式: {e}")

    def calculate_r_breaker(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算R-Breaker指标"""
        df['Prev_Close'] = df['close'].shift(1)
        df['Pivot'] = (df['high'] + df['low'] + df['Prev_Close']) / 3
        df['Break_Support'] = df['Pivot'] - 0.25 * (df['high'] - df['low'])
        df['Break_Resistance'] = df['Pivot'] + 0.25 * (df['high'] - df['low'])
        df['Scrutiny_Buy'] = df['Pivot'] + 0.1 * (df['high'] - df['low'])
        df['Scrutiny_Sell'] = df['Pivot'] - 0.1 * (df['high'] - df['low'])
        return df

    def get_r_breaker_signals(self, df: pd.DataFrame) -> str:
        """根据R-Breaker指标给出操作建议"""
        last_close = df['close'].iloc[-1]
        break_support = df['Break_Support'].iloc[-1]
        break_resistance = df['Break_Resistance'].iloc[-1]

        if last_close > break_resistance:
            return "多头突破,建议多头头寸"
        elif last_close < break_support:
            return "空头突破,建议空头头寸"
        else:
            return "维持观望,等待突破"

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # 同样的指标计算逻辑
        df = self.calculate_r_breaker(df)
        df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = df['EMA12'] - df['EMA26']
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2

        N = 20
        df['MIDA'] = df['close'].rolling(window=N).mean()
        df['UPPERA'] = df['MIDA'] + 2 * df['close'].rolling(window=N).std()
        df['LOWERA'] = df['MIDA'] - 2 * df['close'].rolling(window=N).std()

        df['RSI'] = 100 - (100 / (1 + df['close'].diff().apply(lambda x: max(x, 0)).rolling(window=14).mean() /
                                 df['close'].diff().apply(lambda x: max(-x, 0)).rolling(window=14).mean()))

        df['H-L'] = df['high'] - df['low']
        df['H-Cprev'] = abs(df['high'] - df['close'].shift(1))
        df['L-Cprev'] = abs(df['low'] - df['close'].shift(1))
        df['TR'] = df[['H-L', 'H-Cprev', 'L-Cprev']].max(axis=1)
        df['ATR'] = df['TR'].rolling(14).mean()

        df['channel_upper'] = df['MIDA'].rolling(window=15).max()
        df['channel_lower'] = df['MIDA'].rolling(window=15).min()

        if 'volume' in df.columns:
            df['MA_volume'] = df['volume'].rolling(window=20).mean()

        return df
   
    
    def generate_analysis(self, df: pd.DataFrame, symbol: str, start_date: str, end_date: str) -> str:
        """
        Generate an optimized analysis prompt based on the provided data, incorporating more parameters.
        """
        if df.empty:
            return f"从 {start_date} 到 {end_date}, 没有找到 {symbol} 的数据。请检查代码、日期范围，并确保数据源中有相应的数据。"

        last_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        price_change = (last_price - prev_price) / prev_price * 100
        avg_volume = df['volume'].mean()
        last_volume = df['volume'].iloc[-1]
        volume_change = (last_volume - df['volume'].iloc[-2]) / df['volume'].iloc[-2] * 100
        volatility = df['close'].pct_change().std() * np.sqrt(252) * 100
        atr = df['ATR'].iloc[-1]
        channel_upper = df['channel_upper'].iloc[-1]
        channel_lower = df['channel_lower'].iloc[-1]

        ema12 = df['EMA12'].iloc[-1]
        ema26 = df['EMA26'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        macd = df['MACD'].iloc[-1]
        signal = df['DEA'].iloc[-1]

        atr_threshold = 0.02 * last_price  # Dynamic ATR threshold (2% of last price)
        r_breaker_signal = self.get_r_breaker_signals(df)

        # 定义一些条件判断
        trend = "上升" if last_price > ema26 else "下降"
        volume_trend = "放大" if last_volume > avg_volume else "缩小"
        volatility_level = "高" if volatility > 30 else "中等" if volatility > 15 else "低"
        rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"
        macd_signal = "多头" if macd > signal else "空头"

        analysis_prompt = f"""
        请基于以下数据对 {symbol} 从 {start_date} 到 {end_date} 进行全面分析：

        1. 市场概况：
        - 当前价格：{last_price:.2f}（较前一日{'上涨' if price_change > 0 else '下跌'} {abs(price_change):.2f}%）
        - 成交量：{last_volume:.0f}（较前一日{'增加' if volume_change > 0 else '减少'} {abs(volume_change):.2f}%）
        - 平均成交量：{avg_volume:.0f}
        - 波动率（年化）：{volatility:.2f}%（{volatility_level}波动）
        - ATR：{atr:.2f}（{'高于' if atr > atr_threshold else '低于'}阈值 {atr_threshold:.2f}）
        - 支撑位：{channel_lower:.2f}
        - 阻力位：{channel_upper:.2f}

        2. 技术指标分析：
        - MACD：{macd:.4f}（{macd_signal}信号）
        - DIF：{df['DIF'].iloc[-1]:.4f}
        - DEA：{signal:.4f}
        - RSI：{rsi:.2f}（{rsi_status}）
        - EMA12：{ema12:.2f}
        - EMA26：{ema26:.2f}
        - 布林带：
            上轨：{df['UPPERA'].iloc[-1]:.2f}
            中轨：{df['MIDA'].iloc[-1]:.2f}
            下轨：{df['LOWERA'].iloc[-1]:.2f}

        3. R-Breaker策略信号：
        {r_breaker_signal}

        请根据以上数据，提供以下分析：

        1. 总体趋势评估：
        - 当前处于{trend}趋势。分析价格（{last_price:.2f}）相对于EMA26（{ema26:.2f}）的位置。
        - 评估短期、中期和长期趋势，考虑EMA12和EMA26的交叉情况。

        2. 技术指标解读：
        - MACD显示{macd_signal}信号，进一步解读这个信号的强度和可能持续时间。
        - RSI为{rsi:.2f}，处于{rsi_status}状态。分析这个水平对未来价格走势的影响。
        - 分析价格在布林带中的位置，判断是否有突破或回归的可能。

        3. 成交量分析：
        - 当前成交量{volume_trend}，成交量为{last_volume:.0f}，而平均成交量为{avg_volume:.0f}。
        - 分析成交量变化对价格走势的潜在影响。

        4. 支撑与阻力：
        - 当前价格（{last_price:.2f}）{'接近' if abs(last_price - channel_lower) / last_price < 0.05 else '远离'}支撑位（{channel_lower:.2f}）。
        - 当前价格（{last_price:.2f}）{'接近' if abs(last_price - channel_upper) / last_price < 0.05 else '远离'}阻力位（{channel_upper:.2f}）。
        - 分析突破这些位置的可能性及潜在影响。

        5. 波动性分析：
        - 当前波动率为{volatility:.2f}%，属于{volatility_level}波动水平。
        - ATR为{atr:.2f}，{'高于' if atr > atr_threshold else '低于'}阈值（{atr_threshold:.2f}）。分析这个水平对交易策略的影响。

        6. R-Breaker策略建议：
        - 当前R-Breaker策略信号为"{r_breaker_signal}"。
        - 根据这个信号，提供具体的操作建议，包括可能的入场点和出场点。

        7. 风险评估：
        - 基于当前的{'高' if volatility > 30 else '中等' if volatility > 15 else '低'}波动性，评估主要的风险因素。
        - 提供相应的风险控制建议，包括建议的止损位置。

        8. 交易策略：
        - 综合以上分析，提供短期（1-3天）和中长期（1-4周）的交易策略建议。
        - 建议的止损位可以设在{min(last_price * 0.95, channel_lower):.2f}附近，止盈位可以考虑设在{max(last_price * 1.05, channel_upper):.2f}附近。

        9. 未来展望：
        - 基于当前趋势和指标，预测未来5个交易日的可能价格区间为{last_price * (1 - volatility/100):.2f}到{last_price * (1 + volatility/100):.2f}。
        - 分析可能影响价格的关键因素，包括技术面和可能的基本面因素。

        请确保分析全面、客观，并提供具体、可操作的建议。考虑到市场的不确定性，也请说明在哪些情况下可能需要调整策略。
        """

        return analysis_prompt

    
    def get_gpt_analysis(self, prompt: str) -> str:
        headers = {
            'Content-Type': 'application/json', 
            'Authorization': f'Bearer {self.settings.OPENAI_API_KEY}'
        }
        data = {"model": self.settings.MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}

        try:
            response = requests.post(self.settings.API_URL, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            logging.error(f"GPT分析请求失败: {e}")
            return f"分析请求失败: {e}"
    
    def plot_analysis(self, df: pd.DataFrame, symbol: str, image_path: str) -> None:
        """
        绘制技术分析图
        """
        
        # 设置字体
        plt.rcParams['font.family']=['SimHei']
        plt.rcParams['font.sans-serif']=['SimHei']
        plt.rcParams['axes.unicode_minus']=False

        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        logging.info(f"Saving image to {image_path}")
        try:
            plt.figure(figsize=(14, 9))
            plt.subplot(5, 1, 1)
            plt.plot(df.index, df['close'], label='收盘价')
            plt.title(f'{symbol} 收盘价')
            plt.legend()

            plt.subplot(5, 1, 2)
            plt.plot(df.index, df['MACD'], label='MACD', color='r')
            plt.plot(df.index, df['DIF'], label='DIF', color='b')
            plt.plot(df.index, df['DEA'], label='DEA', color='g')
            plt.title(f'{symbol} MACD')
            plt.legend()

            plt.subplot(5, 1, 3)
            plt.plot(df.index, df['close'], label='收盘价')
            plt.plot(df.index, df['UPPERA'], label='上轨', color='r')
            plt.plot(df.index, df['LOWERA'], label='下轨', color='b')
            plt.title(f'{symbol} 布林带')
            plt.legend()

            plt.subplot(5, 1, 4)
            plt.plot(df.index, df['channel_upper'], label='通道上轨', color='r')
            plt.plot(df.index, df['channel_lower'], label='通道下轨', color='b')
            plt.plot(df.index, df['close'], label='收盘价', color='y')
            plt.title(f'{symbol} 趋势通道')
            plt.legend()

            plt.subplot(5, 1, 5)
            plt.bar(df.index, df['volume'], label='成交量', color='blue', alpha=0.3)
            plt.plot(df.index, df['MA_volume'], label='MA成交量', color='orange')
            plt.title(f'{symbol} 成交量')
            plt.legend()

            plt.tight_layout()
            plt.savefig(image_path)
            plt.close()
            logging.info(f"Image saved successfully to {image_path}")
        except Exception as e:
            logging.error(f"Error saving image: {e}")

    def gpt_analysis_task(self, prompt: str, symbol: str, start_date: str, end_date: str):
        gpt_analysis = self.get_gpt_analysis(prompt)
        if "错误" in gpt_analysis:
            logging.error(f"GPT分析失败: {gpt_analysis}")
            return

        analysis_result = {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "analysis": gpt_analysis
        }
        output_filename = f"./output/{symbol}_{start_date}_{end_date}_analysis.json"
        with open(output_filename, "w", encoding="utf-8") as json_file:
            json.dump(analysis_result, json_file, ensure_ascii=False, indent=4)
