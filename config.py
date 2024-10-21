# config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    TUSHARE_TOKEN: str = ""
    OPENAI_API_KEY: str
    API_URL: str = ""
    MODEL_NAME: str = "groq"
    BASE_URL: str = "http://127.0.0.1:8000"
    FONT_PATH: str = "./static/fonts/imhei.ttf"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
