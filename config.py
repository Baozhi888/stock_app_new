from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    TUSHARE_TOKEN: str = Field(..., env="TUSHARE_TOKEN")
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    API_URL: str = Field(..., env="API_URL")
    MODEL_NAME: str = "groq"
    BASE_URL: str = Field(default="", env="BASE_URL")
    FONT_PATH: str = "./static/fonts/imhei.ttf"
    FUTURES_EXCHANGE: str = "CFFEX"  # 中金所
    FUTURES_TYPES: list = ["IF", "IC", "IH"]  # 主要股指期货品种
    FUTURES_DATA_FIELDS: list = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        use_enum_values = True