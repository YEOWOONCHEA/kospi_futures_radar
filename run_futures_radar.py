import os
import json
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv

import uvicorn
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sys

# 제갈량 코어 연동망
sys.path.append('D:/YouTube_Music_System/Zhuge_Intelligence_Agent')
sys.path.append('C:/Users/i88wi/1004MAS_Deployment_Zones/4_KRX_Stock_Radar')

try:
    from zhuge_ai_core import ZhugeCore
    ai_core = ZhugeCore()
except ImportError:
    ai_core = None

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 글로벌 캐시 메모리
global_cache = {
    "macro": {
        "nasdaq_futures": {"name": "나스닥 100 선물", "price": "18,245.50", "change": "+0.45%"},
        "usd_krw": {"name": "USD/KRW 환율(야간)", "price": "1,352.40", "change": "-0.15%"},
        "vix": {"name": "VIX 공포지수", "price": "12.40", "change": "-2.10%"}
    },
    "futures": [
        {
            "name": "KOSPI 200 야간선물",
            "price": "362.45",
            "change": "+0.80%",
            "volume": "12,450",
            "foreign_net_buy": "+1,240 계약 (순매수)",
            "basis": "+0.45 (콘탱고)"
        }
    ],
    "alerts": [],
    "verdict": "대기 중",
    "last_update": ""
}

async def fetch_mock_macro():
    """차후 야간 매크로 API 연동 전까지 데이터 시뮬레이션"""
    return {
        "nasdaq_futures": {"name": "나스닥 100 선물", "price": "18,245.50", "change": "+0.45%"},
        "usd_krw": {"name": "USD/KRW 환율(야간)", "price": "1,352.40", "change": "-0.15%"},
        "vix": {"name": "VIX 공포지수", "price": "12.40", "change": "-2.10%"}
    }

async def fetch_mock_futures():
    """차후 한국투자증권(KIS) 파생 API 연동시 치환될 부위"""
    return [
        {
            "name": "KOSPI 200 야간선물",
            "price": "362.45",
            "change": "+0.80%",
            "volume": "12,450",
            "foreign_net_buy": "+1,240",
            "basis": "+0.45 (Cons)"
        }
    ]

last_alert_time = 0

async def core_night_radar_loop():
    global last_alert_time
    while True:
        try:
            macro_data = await fetch_mock_macro()
            futures_data = await fetch_mock_futures()
            
            # 인텔리전스 피드 모의 (매크로 알림)
            now_ts = time.time()
            if now_ts - last_alert_time > 60:
                new_alert = f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ 시스템: 미 나스닥 상승 동조에 따른 야간 외인 매수세 지속 중."
                global_cache["alerts"].insert(0, new_alert)
                if len(global_cache["alerts"]) > 10:
                    global_cache["alerts"].pop()
                last_alert_time = now_ts
                
            # Zhuge AI Core 판단
            if ai_core:
                target_data = {
                    "macro": macro_data,
                    "futures": futures_data
                }
                # AI에 코스피 파생/야간선물로 분석 지시
                verdict = await asyncio.to_thread(
                    ai_core.analyze, [target_data], time_phase="PRE_MKT_NIGHT_CLOSE", market_type="futures"
                )
                global_cache["verdict"] = verdict

            global_cache["macro"] = macro_data
            global_cache["futures"] = futures_data
            global_cache["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        except Exception as e:
            print(f"Futures Loop Error: {e}")
        
        await asyncio.sleep(5)  # 선물 파생은 5초 갱신

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(core_night_radar_loop())

@app.get("/api/market_data")
def get_market_data():
    return JSONResponse(global_cache)

if __name__ == "__main__":
    print("[NIGHT] 1004MAS KOSPI Night Futures Server Started on port 8090")
    uvicorn.run("run_futures_radar:app", host="0.0.0.0", port=8090, reload=True)
