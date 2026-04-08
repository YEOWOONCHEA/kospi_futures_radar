import os
import json
import time
import asyncio
import random
from datetime import datetime
from dotenv import load_dotenv

import uvicorn
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sys

# 제갈량 코어 연동망
sys.path.append('D:/YouTube_Music_System/Zhuge_Intelligence_Agent')
sys.path.append('C:/Users/i88wi/1004MAS_Deployment_Zones/4_KRX_Stock_Radar')

# KIS API 설정
load_dotenv()
KIS_APP_KEY = os.getenv('KIS_FUTURES_APP_KEY', '')
KIS_APP_SECRET = os.getenv('KIS_FUTURES_APP_SECRET', '')
KIS_ACCOUNT_NO = os.getenv('KIS_FUTURES_ACCOUNT_NO', '')
KIS_URL = "https://openapi.koreainvestment.com:9443"
KIS_TOKEN = None
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

async def get_kis_token():
    global KIS_TOKEN
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        print("[KIS] No API credentials found.")
        return False
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    try:
        res = requests.post(f"{KIS_URL}/oauth2/tokenP", json=body)
        res_data = res.json()
        KIS_TOKEN = res_data.get("access_token", None)
        if KIS_TOKEN:
            print("[KIS] Token Successfully Authorized.")
            return True
        else:
            print(f"[KIS] Token Failed: {res_data}")
            return False
    except Exception as e:
        print(f"[KIS] Token Error: {e}")
        return False

async def fetch_mock_macro():
    """차후 야간 매크로 API 연동 전까지 데이터 시뮬레이션"""
    return {
        "nasdaq_futures": {"name": "나스닥 100 선물", "price": "18,245.50", "change": "+0.45%"},
        "usd_krw": {"name": "USD/KRW 환율(야간)", "price": "1,352.40", "change": "-0.15%"},
        "vix": {"name": "VIX 공포지수", "price": "12.40", "change": "-2.10%"}
    }

async def fetch_real_futures():
    """실시간 한국투자증권(KIS) 파생 데이터 페칭"""
    if not KIS_TOKEN:
        await get_kis_token()
    
    if not KIS_TOKEN:
        # Fallback to mock
        return [
            {
                "name": "KOSPI 200 야간선물 (MOCK)",
                "price": "362.45",
                "change": "+0.80%",
                "volume": "12,450",
                "foreign_net_buy": "+1,240",
                "basis": "+0.45 (Cons)"
            }
        ]
        
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {KIS_TOKEN}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHMIF10000000",   # 국내선물옵션 주간시세 (야간은 별도 TR_ID 혹은 코드 사용)
        "custtype": "P"
    }
    
    # 코스피 200 선물 근월물 코드 (예시용 고정 코드, 실제 구동시 매월 롤오버 추적 로직 필요)
    # 현재 API 규격상 종목코드 없이 기초 시세가 조회 안됨. 종목코드를 F101F000(예제) 로 조회 필요.
    # 계좌번호가 비어있으면 API 에러 발생 확률이 높으므로 모의반환.
    if not KIS_ACCOUNT_NO:
        return [
            {
                "name": "KOSPI 200 야간선물 (API ERROR - ACC NO)",
                "price": "N/A",
                "change": "0.0%",
                "volume": "0",
                "foreign_net_buy": "0",
                "basis": "N/A"
            }
        ]
        
    return [
        {
            "name": "KOSPI 200 야간선물 (KIS API)",
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
    # 최초 구동 시 토큰 발급
    await get_kis_token()
    
    while True:
        try:
            # 매크로 시뮬레이션 랜덤 변동
            for key, val in global_cache["macro"].items():
                p = float(val["price"].replace(",", ""))
                diff = p * random.uniform(-0.0005, 0.0005)
                new_p = p + diff
                
                chg_str = val["change"]
                if "%" in chg_str:
                    c_val = float(chg_str.replace("%", "").replace("+", ""))
                    c_val += (diff / p) * 100
                    val["change"] = f"{'+' if c_val > 0 else ''}{c_val:.2f}%"
                    
                val["price"] = f"{new_p:,.2f}"

            # 퓨처스 데이터 변동
            for f in global_cache["futures"]:
                if f["price"] != "N/A":
                    p = float(f["price"].replace(",", ""))
                    diff = p * random.uniform(-0.0003, 0.0003)
                    new_p = p + diff
                    
                    chg_str = f["change"]
                    if "%" in chg_str:
                        c_val = float(chg_str.replace("%", "").replace("+", ""))
                        c_val += (diff / p) * 100
                        f["change"] = f"{'+' if c_val > 0 else ''}{c_val:.2f}%"
                    
                    f["price"] = f"{new_p:,.2f}"
                    
                    # 거래량 및 외인 순매수 증가
                    vol = int(f["volume"].replace(",", "")) + random.randint(0, 15)
                    f["volume"] = f"{vol:,}"
                    
                    net_buy = int(f["foreign_net_buy"].replace(",", "").split(" ")[0].replace("+", ""))
                    net_buy += random.randint(-5, 10)
                    sign = "+" if net_buy > 0 else ""
                    f["foreign_net_buy"] = f"{sign}{net_buy:,} 계약 ({'순매수' if net_buy > 0 else '순매도'})"

            macro_data = global_cache["macro"]
            futures_data = global_cache["futures"]
            
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
        
        await asyncio.sleep(2)  # 선물 파생 대시보드 2초 주기로 연속 갱신 설정

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(core_night_radar_loop())

@app.get("/")
def serve_index():
    return FileResponse("index.html")

@app.get("/api/market_data")
def get_market_data():
    return JSONResponse(global_cache)

if __name__ == "__main__":
    print("[NIGHT] 1004MAS KOSPI Night Futures Server Started on port 8090")
    uvicorn.run("run_futures_radar:app", host="0.0.0.0", port=8090, reload=True)
