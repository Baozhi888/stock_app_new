# config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    TUSHARE_TOKEN: str = "1ba1cfe5767fc1462c5bd00cbd911016ec18cf65233894e65fd0c4df"
    OPENAI_API_KEY: str
    API_URL: str = "https://oneapi.intellectapi.com/v1/chat/completions"
    MODEL_NAME: str = "groq"
    BASE_URL: str = "http://127.0.0.1:8000"
    FONT_PATH: str = "./static/fonts/imhei.ttf"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()