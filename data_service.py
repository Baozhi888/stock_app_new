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
        
        # 处理完整的合约代码（例如：IF2403）
        match = re.match(r'([A-Za-z]+)(\d+)', clean_symbol)
        if match:
            product_code, contract_month = match.groups()
            product_code = product_code.upper()
            
            # 验证品种代码
            exchange = self.exchange_map.get(product_code)
            if not exchange:
                raise ValueError(f"不支持的期货品种: {product_code}")
                
            # 验证合约月份格式（应该是4位数字，如2403）
            if len(contract_month) != 4:
                raise ValueError(f"无效的合约月份格式: {contract_month}")
                
            return f"{product_code}{contract_month}.{exchange}"
        
        # 处理品种代码（例如：IF）
        if clean_symbol.isalpha():
            product_code = clean_symbol.upper()
            exchange = self.exchange_map.get(product_code)
            if not exchange:
                raise ValueError(f"不支持的期货品种: {product_code}")
            return f"{product_code}.{exchange}"
            
        raise ValueError(f"无效的期货代码格式: {symbol}")

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
                # 解析合约信息
                match = re.match(r'([A-Za-z]+)(\d{4})\.(.*)', symbol)
                if match:
                    product, contract_month, exchange = match.groups()
                    
                    # 获取当前可交易的合约
                    current_contracts = self.pro.fut_basic(
                        exchange=exchange,
                        fut_type='1',
                        fields='ts_code,symbol,list_date,delist_date'
                    )
                    
                    # 过滤出指定品种的合约
                    product_contracts = current_contracts[
                        current_contracts['ts_code'].str.startswith(f"{product}")
                    ]
                    
                    if product_contracts.empty:
                        raise ValueError(f"未找到 {product} 的可交易合约")
                    
                    # 获取最近的可交易合约
                    valid_contract = product_contracts.sort_values('delist_date', ascending=False).iloc[0]
                    symbol = valid_contract['ts_code']
                    logging.info(f"使用最近可交易合约: {symbol}")

                # 获取期货数据
                df = self.pro.fut_weekly_monthly(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    freq='week'
                )
                
                if df.empty:
                    # 如果周线数据为空，尝试获取日线数据
                    df = self.pro.fut_daily(
                        ts_code=symbol,
                        start_date=start_date,
                        end_date=end_date
                    )

                if df.empty:
                    raise ValueError(f"未找到 {symbol} 从 {start_date} 到 {end_date} 的数据")

                # 处理期货特有字段
                df['amount'] = df['amount'].fillna(0)
                df['oi'] = df['oi'].fillna(0)
                df['oi_chg'] = df['oi_chg'].fillna(0)
                df['settle'] = df['settle'].fillna(df['close'])

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

            # 更新字段映射以包含期货特有字段
            column_mapping = {
                'vol': 'volume',
                'amount': 'amount',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'settle': 'settle',
                'oi': 'oi',
                'oi_chg': 'oi_chg',
                'change1': 'price_change',
                'change2': 'settle_change'
            }
            df.rename(columns={col: column_mapping.get(col, col) for col in df.columns}, inplace=True)

            return df
        except Exception as e:
            logging.error(f"获取 {symbol} 从 {start_date} 到 {end_date} 的数据时发生错误: {str(e)}")
            raise ValueError(f"获取数据失败: {str(e)}")

    def get_current_future_contract(self, symbol: str, date: str) -> str:
        """
        获取期货品种当前最活跃的合约。
        """
        try:
            product = symbol.split('.')[0]  # 例如从 'IF.CFFEX' 提取 'IF'
            exchange = symbol.split('.')[1]

            # 获取所有可交易的合约
            future_info = self.pro.fut_basic(
                exchange=exchange,
                fut_type='1',
                fields='ts_code,symbol,list_date,delist_date,oi'
            )

            # 过滤出指定品种的合约
            valid_contracts = future_info[
                future_info['ts_code'].str.startswith(product)
            ]

            if valid_contracts.empty:
                raise ValueError(f"未找到 {product} 的可交易合约")

            # 按照持仓量排序，获取最活跃的合约
            active_contract = valid_contracts.sort_values('oi', ascending=False).iloc[0]
            
            logging.info(f"选择合约 {active_contract['ts_code']} 作为当前活跃合约")
            return active_contract['ts_code']

        except Exception as e:
            logging.error(f"获取当前期货合约时发生错误: {str(e)}")
            raise ValueError(f"获取当前期货合约失败: {str(e)}")

    def is_valid_futures_contract(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        检查期货合约在给定日期范围内是否有效。
        """
        try:
            df = self.get_data(symbol, start_date, end_date, 'futures')
            return not df.empty
        except Exception:
            return False