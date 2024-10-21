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
        生成分析报告的提示信息,结合优化后的提示
        """
        if not df.empty:
            last_price = df['close'].iloc[-1]
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
            avg_volume = df['volume'].mean()
            volatility = df['close'].pct_change().std() * np.sqrt(252) * 100
            atr = df['ATR'].iloc[-1]
            channel_upper = df['channel_upper'].iloc[-1]
            channel_lower = df['channel_lower'].iloc[-1]

            atr_threshold = 0.05  # 动态调整ATR阈值
            r_breaker_signal = self.get_r_breaker_signals(df)

            # 构建更详细的分析报告
            analysis_prompt = f"""
            综上所述的信息，对{symbol}从{start_date}到{end_date}的表现进行分析如下：
            1. 整体趋势与表现：
            目前该指数处于{'上升' if last_price > df['close'].rolling(window=20).mean().iloc[-1] else '下降'}趋势中，当前价格为{last_price:.2f}，较近期支撑位有所{'上涨' if last_price > channel_lower else '下跌'}。支撑位位在约{channel_lower:.2f}一带，阻力位位在约{channel_upper:.2f}左右。

            2. 技术分析：
            基于布林带、MACD、RSI指标，短期信号如下：
            - 布林带指标：价格在{'中轨（20日线）以上，表明指数暂时保持上升趋势' if last_price > df['MIDA'].iloc[-1] else '中轨（20日线）以下，表明指数暂时保持下降趋势'}。
            - MACD指标：MACD线位于信号线（9日线）{'之上，表明市场可能有上升趋势' if df['MACD'].iloc[-1] > 0 else '之下，表明指数可能继续震荡'}。
            - RSI指标：RSI值为{df['RSI'].iloc[-1]:.2f}，{'' if df['RSI'].iloc[-1] > 50 else 'RSI值在50%以下，表明指数仍处于震荡状态。'}

            3. 信号解读：
            根据上述信号，当前指数处于{'观望' if r_breaker_signal == '维持观望,等待突破' else '有操作信号'}状态。我们建议{'保持观望，等待突破支撑或阻力位' if r_breaker_signal == '维持观望,等待突破' else '依据市场信号执行买卖操作'}。

            4. 市场展望：
            - 短期展望：未来几天，价格变动趋势可能维持{'震荡' if df['MACD'].iloc[-1] < 0 else '上升'}状态。
            - 长期展望：从长期角度看，该指数仍有上升潜力，尤其是如果能够突破阻力位{channel_upper:.2f}以上。

            5. 风险与机会：
            - 市场风险：波动率上升可能导致价格大幅波动。
            - 潜在机会：指数如能突破阻力位，并持续保持上升趋势，则可能有更大的上涨潜力。

            6. 交易策略：
            目前可考虑以{'多头为主，仓位比例推荐为6:4或7:3' if last_price > channel_lower else '观望为主，等待更好的进场时机'}。

            7. 投资策略建议：
            - 长期投资者：如果指数突破阻力位，可考虑加仓。如果价格持续保持上升趋势，可以继续保持持仓。
            - 短期交易者：进场点位可以在支撑位{channel_lower:.2f}附近，出场点位可以在阻力位{channel_upper:.2f}附近。

            8. 明日操作建议：
            根据R-Breaker信号，{r_breaker_signal}，明日的高低点位可能在{last_price * 0.99:.2f}-{last_price * 1.01:.2f}之间，一句话操作指南为“{r_breaker_signal}”。

            9. 指标分析：
            - ATR（平均真实价格范围）为{atr:.2f}，表明价格相对{'较为稳定，适合长期投资' if atr < atr_threshold else '波动较大，需要谨慎交易'}。
            - 趋势通道：指数目前价格在{channel_lower:.2f}至{channel_upper:.2f}之间波动，未来价格有持续维持上升趋势的可能。
            """
        else:
            analysis_prompt = f"从 {start_date} 到 {end_date}, 没有找到 {symbol} 的数据。请检查代码、日期范围，并确保数据源中有相应的数据。"

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
