# models.py
from pydantic import BaseModel, Field, constr
# from typing import Dict

class AnalysisRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    data_type: str

class AnalysisResponse(BaseModel):
    message: str
    image_path: str
    json_file_url: str
    symbol: str
    start_date: str
    end_date: str
    analysis: str