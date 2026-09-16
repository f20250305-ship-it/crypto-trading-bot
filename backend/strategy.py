"""
Strategy Engine
Computes technical indicators and generates BUY / SELL / HOLD signals
with beginner-friendly human-readable explanations.
Pure Python implementation with zero compilation dependencies.
"""

import math
from typing import List, Dict, Any, Tuple


# ==========================================
# 1. Technical Indicators (Pure Python)
# ==========================================

def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average (SMA)."""
    if len(prices) < period:
        return [0.0] * len(prices)

    sma = [0.0] * len(prices)
    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1 : i + 1]
        sma[i] = round(sum(window) / period, 4)
    return sma


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average (EMA).
    Gives more weight to recent prices for faster reaction to market shifts.
    """
    if len(prices) < period:
        return [0.0] * len(prices)

    ema = [0.0] * len(prices)
    # First EMA value is SMA of the first 'period' elements
    initial_sma = sum(prices[:period]) / period
    ema[period - 1] = initial_sma
    multiplier = 2.0 / (period + 1)

    for i in range(period, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
        ema[i] = round(ema[i], 4)

    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index (RSI).
    Oscillates between 0 and 100:
    - Below 30: 'Oversold' (Price may be too low, potential buying bounce)
    - Above 70: 'Overbought' (Price may be too high, potential pullback)
    """
    if len(prices) <= period:
        return [50.0] * len(prices)

    rsi = [50.0] * len(prices)
    gains = []
    losses = []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    if len(gains) < period:
        return rsi

    # First average gain / loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(prices)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = round(100.0 - (100.0 / (1.0 + rs)), 2)

    return rsi


def calculate_macd(
    prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> Dict[str, List[float]]:
    """Calculate MACD Line, Signal Line, and MACD Histogram."""
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    macd_line = []
    for f, s in zip(fast_ema, slow_ema):
        if f > 0 and s > 0:
            macd_line.append(round(f - s, 4))
        else:
            macd_line.append(0.0)

    signal_line = calculate_ema(macd_line, signal_period)
    histogram = [round(m - s, 4) for m, s in zip(macd_line, signal_line)]

    return {
        "macd": macd_line,
        "signal": signal_line,
        "hist": histogram,
    }


# ==========================================
# 2. Strategy Evaluators
# ==========================================

class StrategyEngine:
    AVAILABLE_STRATEGIES = [
        {
            "id": "ema_crossover",
            "name": "EMA Crossover (Trend-Following)",
            "description": "Buys when short-term momentum (Fast EMA 9) crosses above long-term trend (Slow EMA 21). Sells when momentum reverses.",
            "params": {"fast": 9, "slow": 21, "rsi_filter": True}
        },
        {
            "id": "rsi_reversal",
            "name": "RSI Mean Reversion (Bargain Hunter)",
            "description": "Buys when asset is oversold (RSI < 30) and recovering. Sells when overbought (RSI > 70).",
            "params": {"oversold": 30, "overbought": 70, "period": 14}
        },
        {
            "id": "macd_momentum",
            "name": "MACD Momentum Trend",
            "description": "Trades based on MACD histogram expansion and signal line crossovers.",
            "params": {"fast": 12, "slow": 26, "signal": 9}
        },
    ]

    @classmethod
    def get_available_strategies(cls):
        return cls.AVAILABLE_STRATEGIES

    @staticmethod
    def evaluate(
        strategy_id: str,
        candles: List[Dict[str, Any]],
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the latest candle data against chosen strategy.
        Returns:
            action: 'BUY' | 'SELL' | 'HOLD'
            confidence: 0-100%
            reason: Plain English explanation
            indicators: Current indicator values
        """
        if not candles or len(candles) < 30:
            return {
                "action": "HOLD",
                "confidence": 0,
                "reason": "Accumulating market data (need at least 30 candles)...",
                "indicators": {},
            }

        close_prices = [c["close"] for c in candles]
        current_price = close_prices[-1]
        params = params or {}

        if strategy_id == "rsi_reversal":
            period = params.get("period", 14)
            oversold = params.get("oversold", 30)
            overbought = params.get("overbought", 70)
            rsi_vals = calculate_rsi(close_prices, period)
            curr_rsi = rsi_vals[-1]
            prev_rsi = rsi_vals[-2]

            indicators = {"rsi": curr_rsi, "prev_rsi": prev_rsi, "price": current_price}

            if curr_rsi < oversold and curr_rsi > prev_rsi:
                return {
                    "action": "BUY",
                    "confidence": 85,
                    "reason": f"RSI is oversold at {curr_rsi:.1f} (below {oversold}) and curling upward. Good dip-buying opportunity.",
                    "indicators": indicators,
                }
            elif curr_rsi > overbought:
                return {
                    "action": "SELL",
                    "confidence": 90,
                    "reason": f"RSI is overbought at {curr_rsi:.1f} (above {overbought}). Price may be overextended, locking in profit.",
                    "indicators": indicators,
                }
            else:
                return {
                    "action": "HOLD",
                    "confidence": 50,
                    "reason": f"RSI is neutral at {curr_rsi:.1f} (between {oversold} and {overbought}). No strong reversal edge.",
                    "indicators": indicators,
                }

        elif strategy_id == "macd_momentum":
            fast = params.get("fast", 12)
            slow = params.get("slow", 26)
            sig = params.get("signal", 9)
            macd_res = calculate_macd(close_prices, fast, slow, sig)
            curr_hist = macd_res["hist"][-1]
            prev_hist = macd_res["hist"][-2]
            curr_macd = macd_res["macd"][-1]
            curr_sig = macd_res["signal"][-1]

            indicators = {
                "macd": curr_macd,
                "signal": curr_sig,
                "hist": curr_hist,
                "price": current_price,
            }

            if prev_hist < 0 and curr_hist > 0:
                return {
                    "action": "BUY",
                    "confidence": 80,
                    "reason": f"MACD Histogram turned positive ({curr_hist:.2f}). Bullish momentum crossover detected.",
                    "indicators": indicators,
                }
            elif prev_hist > 0 and curr_hist < 0:
                return {
                    "action": "SELL",
                    "confidence": 80,
                    "reason": f"MACD Histogram turned negative ({curr_hist:.2f}). Bearish momentum breakdown detected.",
                    "indicators": indicators,
                }
            else:
                return {
                    "action": "HOLD",
                    "confidence": 40,
                    "reason": f"MACD momentum unchanged (Hist: {curr_hist:.2f}). Holding current stance.",
                    "indicators": indicators,
                }

        else:
            # Default: EMA Crossover
            fast_period = params.get("fast", 9)
            slow_period = params.get("slow", 21)
            fast_ema = calculate_ema(close_prices, fast_period)
            slow_ema = calculate_ema(close_prices, slow_period)
            rsi_vals = calculate_rsi(close_prices, 14)

            curr_fast = fast_ema[-1]
            curr_slow = slow_ema[-1]
            prev_fast = fast_ema[-2]
            prev_slow = slow_ema[-2]
            curr_rsi = rsi_vals[-1]

            indicators = {
                f"ema_{fast_period}": curr_fast,
                f"ema_{slow_period}": curr_slow,
                "rsi": curr_rsi,
                "price": current_price,
            }

            # Golden Cross: Fast EMA crosses ABOVE Slow EMA
            is_golden_cross = (prev_fast <= prev_slow) and (curr_fast > curr_slow)
            # Death Cross: Fast EMA crosses BELOW Slow EMA
            is_death_cross = (prev_fast >= prev_slow) and (curr_fast < curr_slow)

            if is_golden_cross:
                if curr_rsi > 75:
                    return {
                        "action": "HOLD",
                        "confidence": 40,
                        "reason": f"Golden Cross detected (EMA {fast_period} > EMA {slow_period}), but RSI is overbought at {curr_rsi:.1f}. Skipped high-risk entry.",
                        "indicators": indicators,
                    }
                return {
                    "action": "BUY",
                    "confidence": 88,
                    "reason": f"Golden Cross! Fast EMA {fast_period} (${curr_fast:,.2f}) crossed above Slow EMA {slow_period} (${curr_slow:,.2f}). Upward trend confirmed.",
                    "indicators": indicators,
                }
            elif is_death_cross:
                return {
                    "action": "SELL",
                    "confidence": 88,
                    "reason": f"Death Cross! Fast EMA {fast_period} (${curr_fast:,.2f}) crossed below Slow EMA {slow_period} (${curr_slow:,.2f}). Downward trend warning.",
                    "indicators": indicators,
                }
            elif curr_fast > curr_slow:
                return {
                    "action": "HOLD",
                    "confidence": 60,
                    "reason": f"Bullish trend ongoing (EMA {fast_period} > EMA {slow_period}). Price: ${current_price:,.2f}.",
                    "indicators": indicators,
                }
            else:
                return {
                    "action": "HOLD",
                    "confidence": 60,
                    "reason": f"Bearish trend ongoing (EMA {fast_period} < EMA {slow_period}). Waiting for bullish reversal signal.",
                    "indicators": indicators,
                }
