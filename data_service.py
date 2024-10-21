import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import logging
import re

class DataService:
    def __init__(self, tushare_token: str):
        """
        初始化DataService，传入Tushare token，配置API访问。
        """
        ts.set_token(tushare_token)
        self.pro = ts.pro_api()

        # 合并期货交易所和合约映射为字典
        self.future_exchanges = {
            'CFFEX': ['IF', 'IC', 'IH'],
            'SHFE': ['CU', 'AL', 'ZN'],
            'DCE': ['M', 'C', 'I'],
            'CZCE': ['MA'],
            'INE': ['SC'],
            'GFEX': []  # 广州期货交易所，可能需要添加具体的合约
        }
        self.exchange_map = {code: exchange for exchange, codes in self.future_exchanges.items() for code in codes}

    def validate_stock_code(self, symbol: str, data_type: str) -> str:
        """
        验证并格式化证券代码，支持股票、期货和指数。
        """
        symbol = symbol.strip().upper()

        if data_type == 'stock':
            # 股票代码处理，按市场后缀
            return self._validate_stock_symbol(symbol)
        elif data_type == 'futures':
            # 期货代码处理
            return self._validate_futures_symbol(symbol)
        elif data_type == 'index':
            # 指数代码处理
            return self._validate_index_symbol(symbol)
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

    def _validate_stock_symbol(self, symbol: str) -> str:
        """验证和格式化股票代码"""
        clean_symbol = re.sub(r'\.(SZ|SH|BJ)$', '', symbol, flags=re.IGNORECASE)
        if clean_symbol.startswith('6'):
            return f"{clean_symbol}.SH"
        elif clean_symbol.startswith(('0', '3')):
            return f"{clean_symbol}.SZ"
        elif clean_symbol.startswith(('4', '8', '9')):
            return f"{clean_symbol}.BJ"
        else:
            raise ValueError(f"无效的股票代码: {symbol}")

    def _validate_futures_symbol(self, symbol: str) -> str:
        """验证和格式化期货代码"""
        clean_symbol = re.sub(r'\.(CFFEX|SHFE|DCE|CZCE|INE|GFEX)$', '', symbol, flags=re.IGNORECASE)
        match = re.match(r'([A-Za-z]+)(\d+)', clean_symbol)
        if not match:
            raise ValueError(f"无效的期货代码格式: {symbol}")
        product_code, _ = match.groups()
        exchange = self.exchange_map.get(product_code.upper())
        if not exchange:
            raise ValueError(f"不支持的期货品种: {product_code}")
        return f"{clean_symbol.lower()}.{exchange}"

    def _validate_index_symbol(self, symbol: str) -> str:
        """验证和格式化指数代码"""
        index_mapping = {
            '000300': '000300.SH', '000001': '000001.SH',
            '000905': '000905.SH', '399001': '399001.SZ'
        }
        clean_symbol = re.sub(r'\.(SZ|SH)$', '', symbol, flags=re.IGNORECASE)
        return index_mapping.get(clean_symbol, symbol)

    def validate_dates(self, start_date: str, end_date: str) -> tuple:
        """
        验证日期范围是否合理，并格式化为YYYYMMDD。
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            today = datetime.now()

            # 如果结束日期在未来，则调整为当前日期
            if end > today:
                end = today
                logging.warning(f"结束日期调整为当前日期: {end.strftime('%Y-%m-%d')}")

            # 确保开始日期不在结束日期之后
            if start > end:
                start = end - timedelta(days=30)
                logging.warning(f"开始日期调整为: {start.strftime('%Y-%m-%d')}")

            return start.strftime('%Y%m%d'), end.strftime('%Y%m%d')
        except ValueError as e:
            raise ValueError(f"日期格式错误，请使用YYYY-MM-DD格式: {e}")

    def get_data(self, symbol: str, start_date: str, end_date: str, data_type: str) -> pd.DataFrame:
        """
        获取股票、期货或指数的历史数据。
        """
        try:
            # 验证并格式化代码和日期
            symbol = self.validate_stock_code(symbol, data_type)
            start_date, end_date = self.validate_dates(start_date, end_date)

            logging.info(f"获取数据: {symbol} 从 {start_date} 到 {end_date}")

            # 根据数据类型获取不同的数据
            if data_type == 'futures':
                df = self.pro.fut_daily(ts_code=symbol, start_date=start_date, end_date=end_date)
                if df.empty:
                    symbol = self.get_current_future_contract(symbol, end_date)
                    logging.info(f"尝试获取当前可交易合约: {symbol}")
                    df = self.pro.fut_daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == 'index':
                df = self.pro.index_daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            else:  # stock
                df = self.pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)

            if df.empty:
                raise ValueError(f"未找到 {symbol} 从 {start_date} 到 {end_date} 的数据，可能是非交易日或代码错误")

            # 格式化数据表
            df['date'] = pd.to_datetime(df['trade_date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 字段映射
            column_mapping = {
                'vol': 'volume', 'amount': 'amount', 
                'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'
            }
            df.rename(columns={col: column_mapping.get(col, col) for col in df.columns}, inplace=True)

            return df
        except Exception as e:
            logging.error(f"获取 {symbol} 从 {start_date} 到 {end_date} 的数据时发生错误: {str(e)}")
            raise ValueError(f"获取数据失败: {str(e)}")

    def get_current_future_contract(self, symbol: str, date: str) -> str:
        """
        获取期货合约在指定日期内最近的有效合约。
        """
        product = symbol.split('.')[0][:-4]  # 例如从 'IF2412.CFFEX' 提取 'IF'
        exchange = symbol.split('.')[1]

        # 获取期货合约信息
        future_info = self.pro.fut_basic(exchange=exchange, fut_type='1', fields='ts_code,symbol,list_date,delist_date')

        # 过滤出指定日期可交易的合约
        valid_contracts = future_info[
            (future_info['symbol'].str.startswith(product)) &
            (future_info['list_date'] <= date) &
            (future_info['delist_date'] >= date)
        ]

        if valid_contracts.empty:
            # 获取未来可交易的合约
            future_contracts = future_info[
                (future_info['symbol'].str.startswith(product)) &
                (future_info['list_date'] > date)
            ]
            if not future_contracts.empty:
                return future_contracts.sort_values('list_date').iloc[0]['ts_code']
            else:
                raise ValueError(f"未找到 {date} 日及之后可交易的 {product} 合约")

        # 返回最近的到期合约
        return valid_contracts.sort_values('ts_code').iloc[0]['ts_code']

    def is_valid_futures_contract(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        检查期货合约在给定日期范围内是否有效。
        """
        try:
            df = self.get_data(symbol, start_date, end_date, 'futures')
            return not df.empty
        except Exception:
            return False