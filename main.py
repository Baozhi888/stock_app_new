import json
import logging
import os
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from analysis_service import AnalysisService
from config import Settings
from data_service import DataService
from models import AnalysisRequest, AnalysisResponse
from datetime import date, datetime
import tushare as ts

# 设置日志
logging.basicConfig(level=logging.INFO)
app = FastAPI()

# CORS 和静态文件设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化服务
settings = Settings()
data_service = DataService(settings.TUSHARE_TOKEN)
analysis_service = AnalysisService(settings)
executor = ThreadPoolExecutor(max_workers=5)

# 实施日期验证功能，确保请求的日期范围有效
def validate_date_range(start_date: str, end_date: str) -> tuple[date, date]:
    today = date.today()
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("日期格式无效，请使用 YYYY-MM-DD 格式")
    
    if start > today or end > today:
        raise ValueError("日期范围不能包含未来的日期")
    if start > end:
        raise ValueError("开始日期必须早于结束日期")
    
    return start, end

# 检查期货合约在给定日期范围内是否有效
def is_valid_futures_contract(symbol: str, start_date: date, end_date: date) -> bool:
    pro = ts.pro_api()
    today = date.today()

    # 获取期货合约信息
    df = pro.fut_basic(ts_code=symbol)
    
    if df.empty:
        raise ValueError("未找到期货合约信息")

    list_date = datetime.strptime(str(df['list_date'].iloc[0]), "%Y%m%d").date()
    end_date_con = datetime.strptime(str(df['end_date'].iloc[0]), "%Y%m%d").date()

    # 判断期货合约是否在给定日期范围内有效
    if (list_date <= start_date <= end_date_con) and (end_date <= end_date_con):
        return True
    return False



# 保存分析结果到 JSON 文件
def save_json_analysis(symbol: str, start_date: str, end_date: str, analysis: str):
    output_filename = f"./output/{symbol}_{start_date}_{end_date}_analysis.json"
    
    # 确保输出目录存在
    os.makedirs("./output", exist_ok=True)
    
    # 保存分析结果到 JSON
    analysis_result = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "analysis": analysis
    }
    
    try:
        with open(output_filename, "w", encoding="utf-8") as json_file:
            json.dump(analysis_result, json_file, ensure_ascii=False, indent=4)
        logging.info(f"JSON 文件成功保存至 {output_filename}")
    except Exception as e:
        logging.error(f"保存 JSON 文件失败: {e}")


@app.get("/", response_class=HTMLResponse)
def read_root():
    file_path = os.path.abspath("static/index.html")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read())
    except FileNotFoundError:
        return HTMLResponse(content="文件未找到", status_code=404)
    

# 数据分析异步处理
async def analyze_data_async(request: AnalysisRequest) -> AnalysisResponse:
    try:
        # 验证日期范围
        start_date, end_date = validate_date_range(request.start_date, request.end_date)
        
        # 对于期货合约，验证合约的有效性
        if request.data_type == "期货":
            if not is_valid_futures_contract(request.symbol, start_date, end_date):
                raise ValueError(f"请求的日期范围 {start_date} 到 {end_date} 对于合约 {request.symbol} 无效")
        
        # 获取数据
        df = data_service.get_data(request.symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), request.data_type)
        
        # 计算指标
        df = analysis_service.calculate_indicators(df)
        
        # 生成分析提示
        analysis_prompt = analysis_service.generate_analysis(df, request.symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

        # 创建输出目录
        os.makedirs("./output", exist_ok=True)

        # 生成图表
        image_path = f"./output/{request.symbol}_{start_date}_{end_date}.png"
        analysis_service.plot_analysis(df, request.symbol, image_path)

        # 获取 GPT 分析结果
        gpt_analysis = analysis_service.get_gpt_analysis(analysis_prompt)

        # 保存 JSON 分析结果
        save_json_analysis(request.symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), gpt_analysis)

        # 返回 JSON 和图片链接
        json_file_url = f"{settings.BASE_URL}/get_json/{request.symbol}_{start_date}_{end_date}"
        image_api_url = f"{settings.BASE_URL}/get_image/{request.symbol}_{start_date}_{end_date}.png"

        return AnalysisResponse(
            message=f"分析完成 {request.data_type} {request.symbol}",
            image_path=image_api_url,
            json_file_url=json_file_url,
            symbol=request.symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            analysis=gpt_analysis
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"分析过程发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.post("/analyze/")
async def analyze_data(request: AnalysisRequest):
    return await analyze_data_async(request)


@app.get("/get_image/{symbol}_{start_date}_{end_date}.png")
async def get_image(symbol: str, start_date: str, end_date: str):
    image_path = f"./output/{symbol}_{start_date}_{end_date}.png"
    logging.info(f"Fetching image from {image_path}")
    
    if not os.path.exists(image_path):
        logging.error(f"Image not found at {image_path}")
        raise HTTPException(status_code=404, detail="图像未找到")
    
    return Response(content=open(image_path, "rb").read(), media_type="image/png")

@app.get("/get_json/{symbol}_{start_date}_{end_date}")
async def get_json(symbol: str, start_date: str, end_date: str):
    json_filename = f"./output/{symbol}_{start_date}_{end_date}_analysis.json"
    
    logging.info(f"尝试获取 JSON 文件: {json_filename}")
    
    if not os.path.exists(json_filename):
        logging.error(f"JSON 文件未找到: {json_filename}")
        raise HTTPException(status_code=404, detail="JSON 文件未找到")
    
    try:
        with open(json_filename, "r", encoding="utf-8") as json_file:
            json_content = json.load(json_file)
        logging.info(f"成功读取 JSON 文件: {json_filename}")
        return json_content
    except json.JSONDecodeError as e:
        logging.error(f"JSON 文件解析错误: {json_filename}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail="JSON 文件解析错误")
    except Exception as e:
        logging.error(f"读取 JSON 文件时发生未知错误: {json_filename}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail="读取 JSON 文件时发生错误")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")