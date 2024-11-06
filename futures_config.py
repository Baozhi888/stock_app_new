from typing import Dict, List

class FuturesConfig:
    # 期货交易所映射
    EXCHANGE_MAP: Dict[str, str] = {
        'IF': 'CFFEX',  # 沪深300股指期货
        'IC': 'CFFEX',  # 中证500股指期货
        'IH': 'CFFEX',  # 上证50股指期货
        'IM': 'CFFEX',  # 中证1000股指期货
        'T': 'CFFEX',   # 10年期国债期货
        'TS': 'CFFEX',  # 2年期国债期货
        # ... 可以添加更多品种
    }

    # 主力合约月份
    MAIN_CONTRACT_MONTHS: List[str] = ['03', '06', '09', '12']

    # 期货数据字段
    FUTURES_FIELDS: List[str] = [
        'ts_code', 'trade_date', 'open', 'high', 'low', 
        'close', 'vol', 'amount', 'oi', 'oi_chg'
    ]

    # 期货分析指标配置
    ANALYSIS_SETTINGS = {
        'oi_ma_periods': [5, 10, 20],  # 持仓量均线周期
        'volume_ma_periods': [5, 10, 20],  # 成交量均线周期
        'price_ma_periods': [5, 10, 20, 60],  # 价格均线周期
    }

    @staticmethod
    def get_contract_size(symbol: str) -> float:
        """获取合约乘数"""
        contract_sizes = {
            'IF': 300,
            'IC': 200,
            'IH': 300,
            'IM': 200,
        }
        product = symbol.split('.')[0][:2]
        return contract_sizes.get(product, 1.0)
