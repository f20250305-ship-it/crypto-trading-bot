"""
Market Data Module
Fetches real-time crypto prices and historical OHLCV klines from public endpoints.
Requires NO API keys or account registration.
"""

import time
import requests
from typing import List, Dict, Any, Optional

BINANCE_BASE_URL = "https://api.binance.com/api/v3"

SUPPORTED_PAIRS = [
    {"symbol": "BTCUSDT", "name": "Bitcoin", "icon": "₿"},
    {"symbol": "ETHUSDT", "name": "Ethereum", "icon": "Ξ"},
    {"symbol": "SOLUSDT", "name": "Solana", "icon": "◎"},
    {"symbol": "BNBUSDT", "name": "BNB", "icon": "🔶"},
    {"symbol": "DOGEUSDT", "name": "Dogecoin", "icon": "Ð"},
]


class MarketDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CryptoTradingBot/1.0",
            "Accept": "application/json",
        })
        self._cache = {}
        self._cache_ttl = 2.0  # 2 second cache for live prices to avoid spamming

    def get_supported_pairs(self) -> List[Dict[str, str]]:
        return SUPPORTED_PAIRS

    def get_ticker_24h(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Fetch 24-hour ticker statistics including price, high, low, volume, % change."""
        cache_key = f"ticker_{symbol}"
        now = time.time()
        if cache_key in self._cache:
            data, exp = self._cache[cache_key]
            if now < exp:
                return data

        try:
            url = f"{BINANCE_BASE_URL}/ticker/24hr"
            res = self.session.get(url, params={"symbol": symbol.upper()}, timeout=6)
            res.raise_for_status()
            raw = res.json()
            data = {
                "symbol": raw.get("symbol", symbol),
                "price": float(raw.get("lastPrice", 0.0)),
                "change_24h": float(raw.get("priceChangePercent", 0.0)),
                "high_24h": float(raw.get("highPrice", 0.0)),
                "low_24h": float(raw.get("lowPrice", 0.0)),
                "volume_24h": float(raw.get("volume", 0.0)),
                "quote_volume": float(raw.get("quoteVolume", 0.0)),
                "timestamp": int(raw.get("closeTime", int(now * 1000))),
            }
            self._cache[cache_key] = (data, now + self._cache_ttl)
            return data
        except Exception as e:
            # If rate-limited or offline, return safe fallback
            return {
                "symbol": symbol,
                "price": 65000.0 if "BTC" in symbol else (3500.0 if "ETH" in symbol else 150.0),
                "change_24h": 0.0,
                "high_24h": 0.0,
                "low_24h": 0.0,
                "volume_24h": 0.0,
                "quote_volume": 0.0,
                "timestamp": int(now * 1000),
                "error": str(e),
            }

    def get_klines(
        self, symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV historical candlestick data.
        Intervals: 1m, 5m, 15m, 1h, 4h, 1d
        Limit: up to 1000
        """
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        now = time.time()
        if cache_key in self._cache:
            data, exp = self._cache[cache_key]
            if now < exp:
                return data

        try:
            url = f"{BINANCE_BASE_URL}/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": limit,
            }
            res = self.session.get(url, params=params, timeout=10)
            res.raise_for_status()
            raw_klines = res.json()

            candles = []
            for item in raw_klines:
                # Binance format: [open_time, open, high, low, close, volume, close_time, ...]
                candles.append({
                    "timestamp": int(item[0]),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                    "close_time": int(item[6]),
                })

            # Cache klines for 30 seconds
            self._cache[cache_key] = (candles, now + 30.0)
            return candles
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return []


# Global singleton
market_data = MarketDataFetcher()
