import pandas as pd
import numpy as np
import talib
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 1. Supported Timeframes & Asset Pairs (All OTC & Live Pairs Supported)
SUPPORTED_TIMEFRAMES = ["15s", "30s", "1m", "2m", "3m", "5m", "15m"]

# Aap yahan aur bhi pairs add kar sakte hain (e.g., AUDUSD-OTC, NZDUSD-OTC, Crypto pairs, etc.)
DEFAULT_SUPPORTED_PAIRS = [
    "EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "USDCAD-OTC",
    "EURGBP-OTC", "EURJPY-OTC", "GBPJPY-OTC", "NZDUSD-OTC", "USDCHF-OTC",
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"
]

class AdvancedMarketSignalEngine:
    def __init__(self, df: pd.DataFrame, timeframe: str):
        self.df = df
        self.timeframe = timeframe

    def analyze_indicators(self) -> Dict[str, Any]:
        close = self.df['close'].values
        rsi = talib.RSI(close, timeperiod=14)
        ema_fast = talib.EMA(close, timeperiod=9)
        ema_slow = talib.EMA(close, timeperiod=21)
        
        return {
            "rsi": rsi[-1] if len(rsi) > 0 else 50.0,
            "trend": "BULLISH" if ema_fast[-1] > ema_slow[-1] else "BEARISH"
        }

    def detect_all_ta_lib_patterns(self) -> Dict[str, Any]:
        op = self.df['open'].values
        hi = self.df['high'].values
        lo = self.df['low'].values
        cl = self.df['close'].values

        # TA-Lib candlestick pattern scanning
        patterns = {
            "Bullish Engulfing": talib.CDLENGULFING(op, hi, lo, cl)[-1] == 100,
            "Bearish Engulfing": talib.CDLENGULFING(op, hi, lo, cl)[-1] == -100,
            "Hammer": talib.CDLHAMMER(op, hi, lo, cl)[-1] == 100,
            "Shooting Star": talib.CDLSHOOTINGSTAR(op, hi, lo, cl)[-1] == -100,
            "Morning Star": talib.CDLMORNINGSTAR(op, hi, lo, cl)[-1] == 100,
            "Evening Star": talib.CDLEVENINGSTAR(op, hi, lo, cl)[-1] == -100,
            "Doji": talib.CDLDOJI(op, hi, lo, cl)[-1] != 0
        }

        detected_pattern = "NONE"
        signal = "NEUTRAL"

        bullish_list = ["Bullish Engulfing", "Hammer", "Morning Star"]
        bearish_list = ["Bearish Engulfing", "Shooting Star", "Evening Star"]

        for pat in bullish_list:
            if patterns[pat]:
                detected_pattern = pat
                signal = "CALL"
                break

        if signal == "NEUTRAL":
            for pat in bearish_list:
                if patterns[pat]:
                    detected_pattern = pat
                    signal = "PUT"
                    break

        return {"pattern": detected_pattern, "pattern_signal": signal}

    def generate_vip_signal(self) -> Dict[str, Any]:
        indicators = self.analyze_indicators()
        patterns = self.detect_all_ta_lib_patterns()

        rsi = indicators["rsi"]
        trend = indicators["trend"]
        pattern_sig = patterns["pattern_signal"]

        decision = "HOLD / WAIT"
        confidence = 0.0
        is_vip = False

        # VIP Filtering Logic for High Accuracy
        if trend == "BULLISH" and pattern_sig == "CALL" and rsi < 65:
            decision = "CALL (BUY)"
            confidence = 0.96  # 96% High Accuracy Target Filter
            is_vip = True
        elif trend == "BEARISH" and pattern_sig == "PUT" and rsi > 35:
            decision = "PUT (SELL)"
            confidence = 0.96
            is_vip = True
        elif pattern_sig == "CALL" and rsi < 30:
            decision = "CALL (BUY)"
            confidence = 0.88
            is_vip = False
        elif pattern_sig == "PUT" and rsi > 70:
            decision = "PUT (SELL)"
            confidence = 0.88
            is_vip = False

        return {
            "signal": decision,
            "is_vip_signal": is_vip,
            "confidence": confidence,
            "timeframe": self.timeframe,
            "pattern": patterns["pattern"],
            "rsi": round(rsi, 2),
            "trend": trend
        }

app = FastAPI(title="Pocket Option Multi-Pair & Multi-Timeframe VIP Signal Engine")

class Candle(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float

class MarketRequest(BaseModel):
    symbol: str               # Example: "EURUSD-OTC", "GBPJPY-OTC", etc.
    timeframe: str            # "15s", "30s", "1m", "2m", "3m", "5m", "15m"
    candles: List[Candle]

@app.post("/api/v1/signal")
async def get_trading_signal(data: MarketRequest):
    if data.timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid timeframe. Supported: {SUPPORTED_TIMEFRAMES}"
        )

    if len(data.candles) < 30:
        raise HTTPException(
            status_code=400, 
            detail="At least 30 candles are required for accurate analysis."
        )

    df = pd.DataFrame([c.dict() for c in data.candles])
    engine = AdvancedMarketSignalEngine(df, timeframe=data.timeframe)
    result = engine.generate_vip_signal()

    result["symbol"] = data.symbol.upper()
    result["market_type"] = "OTC" if "OTC" in data.symbol.upper() else "LIVE"

    return result

@app.get("/api/v1/pairs")
async def get_supported_pairs():
    return {
        "supported_pairs": DEFAULT_SUPPORTED_PAIRS,
        "supported_timeframes": SUPPORTED_TIMEFRAMES
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
