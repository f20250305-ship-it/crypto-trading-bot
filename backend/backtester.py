"""
Historical Backtesting Engine
Simulates running any strategy across the past 365 days of real cryptocurrency data.
Compares strategy performance against a simple 'Buy & Hold' benchmark.
Calculates realistic trading fees (0.1% per trade standard).
"""

from typing import List, Dict, Any
from backend.market_data import market_data
from backend.strategy import StrategyEngine, calculate_ema, calculate_rsi, calculate_macd


class BacktestEngine:
    @staticmethod
    def run_backtest(
        symbol: str = "BTCUSDT",
        strategy_id: str = "ema_crossover",
        initial_balance: float = 10000.0,
        days: int = 365,
        fee_rate: float = 0.001,  # 0.1% Binance standard spot fee
        stop_loss_pct: float = 0.03,  # 3% stop loss protection
        take_profit_pct: float = 0.06,  # 6% take profit target
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Executes historical backtest over real candlestick data.
        Returns comprehensive performance metrics, equity curve, and trade list.
        """
        params = params or {}
        # Fetch historical candles
        candles = market_data.get_klines(symbol=symbol, interval="1d", limit=days)
        if not candles or len(candles) < 35:
            # Fallback to hourly if daily not enough
            candles = market_data.get_klines(symbol=symbol, interval="4h", limit=days)

        if not candles or len(candles) < 30:
            return {
                "error": f"Insufficient historical data available for {symbol}.",
                "success": False,
            }

        cash = initial_balance
        position_crypto = 0.0
        entry_price = 0.0
        entry_date = ""

        trades = []
        equity_curve = []
        peak_equity = initial_balance
        max_drawdown_pct = 0.0

        first_close = candles[0]["close"]
        last_close = candles[-1]["close"]
        buy_and_hold_return_pct = round(((last_close - first_close) / first_close) * 100.0, 2)

        # Precalculate indicators
        close_prices = [c["close"] for c in candles]
        fast_ema = calculate_ema(close_prices, params.get("fast", 9))
        slow_ema = calculate_ema(close_prices, params.get("slow", 21))
        rsi_vals = calculate_rsi(close_prices, params.get("period", 14))

        # Loop through each candle from index 25 onwards
        for i in range(25, len(candles)):
            c = candles[i]
            price = c["close"]
            date_str = c.get("close_time", c["timestamp"])
            # Format timestamp to YYYY-MM-DD
            import datetime
            dt = datetime.datetime.fromtimestamp(date_str / 1000.0, tz=datetime.timezone.utc)
            date_formatted = dt.strftime("%Y-%m-%d")

            # Check open position risk management (Stop-Loss and Take-Profit)
            if position_crypto > 0:
                pnl_pct = (price - entry_price) / entry_price
                exit_reason = ""

                if pnl_pct <= -stop_loss_pct:
                    exit_reason = f"🛑 Stop-Loss triggered (-{abs(pnl_pct*100):.1f}%)"
                elif pnl_pct >= take_profit_pct:
                    exit_reason = f"🎯 Take-Profit hit (+{pnl_pct*100:.1f}%)"

                if exit_reason:
                    # Execute sell
                    proceeds = position_crypto * price * (1.0 - fee_rate)
                    net_pnl = proceeds - (position_crypto * entry_price)
                    cash += proceeds
                    trades.append({
                        "id": len(trades) + 1,
                        "entry_date": entry_date,
                        "exit_date": date_formatted,
                        "type": "SELL",
                        "entry_price": entry_price,
                        "exit_price": price,
                        "pnl_usd": round(net_pnl, 2),
                        "pnl_pct": round(pnl_pct * 100.0, 2),
                        "reason": exit_reason,
                        "win": net_pnl > 0
                    })
                    position_crypto = 0.0
                    entry_price = 0.0

            # Evaluate strategy signals
            action = "HOLD"
            reason = ""

            if strategy_id == "rsi_reversal":
                curr_rsi = rsi_vals[i]
                prev_rsi = rsi_vals[i-1]
                if curr_rsi < params.get("oversold", 30) and curr_rsi > prev_rsi:
                    action = "BUY"
                    reason = f"RSI oversold rebound ({curr_rsi:.1f})"
                elif curr_rsi > params.get("overbought", 70):
                    action = "SELL"
                    reason = f"RSI overbought peak ({curr_rsi:.1f})"

            else:
                # EMA Crossover
                f_curr, f_prev = fast_ema[i], fast_ema[i-1]
                s_curr, s_prev = slow_ema[i], slow_ema[i-1]
                if (f_prev <= s_prev) and (f_curr > s_curr):
                    action = "BUY"
                    reason = f"Golden Cross (EMA {params.get('fast', 9)} > EMA {params.get('slow', 21)})"
                elif (f_prev >= s_prev) and (f_curr < s_curr):
                    action = "SELL"
                    reason = f"Death Cross (EMA {params.get('fast', 9)} < EMA {params.get('slow', 21)})"

            # Execute trade logic
            if action == "BUY" and cash > 50 and position_crypto == 0:
                # Buy with available cash
                trade_amount = cash * 0.95  # Allocate 95% of cash
                cost_with_fee = trade_amount * (1.0 + fee_rate)
                if cost_with_fee <= cash:
                    qty = trade_amount / price
                    position_crypto = qty
                    entry_price = price
                    entry_date = date_formatted
                    cash -= trade_amount * (1.0 + fee_rate)

            elif action == "SELL" and position_crypto > 0:
                proceeds = position_crypto * price * (1.0 - fee_rate)
                pnl_pct = (price - entry_price) / entry_price
                net_pnl = proceeds - (position_crypto * entry_price)
                cash += proceeds
                trades.append({
                    "id": len(trades) + 1,
                    "entry_date": entry_date,
                    "exit_date": date_formatted,
                    "type": "SELL",
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl_usd": round(net_pnl, 2),
                    "pnl_pct": round(pnl_pct * 100.0, 2),
                    "reason": reason,
                    "win": net_pnl > 0
                })
                position_crypto = 0.0
                entry_price = 0.0

            # Calculate total current equity
            current_equity = cash + (position_crypto * price)
            if current_equity > peak_equity:
                peak_equity = current_equity
            dd_pct = ((peak_equity - current_equity) / peak_equity) * 100.0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

            equity_curve.append({
                "date": date_formatted,
                "equity": round(current_equity, 2),
                "price": price,
            })

        # Close any remaining open position at last price
        final_price = candles[-1]["close"]
        if position_crypto > 0:
            proceeds = position_crypto * final_price * (1.0 - fee_rate)
            pnl_pct = (final_price - entry_price) / entry_price
            net_pnl = proceeds - (position_crypto * entry_price)
            cash += proceeds
            trades.append({
                "id": len(trades) + 1,
                "entry_date": entry_date,
                "exit_date": candles[-1].get("timestamp"),
                "type": "SELL (Close Period)",
                "entry_price": entry_price,
                "exit_price": final_price,
                "pnl_usd": round(net_pnl, 2),
                "pnl_pct": round(pnl_pct * 100.0, 2),
                "reason": "Closed at end of backtest period",
                "win": net_pnl > 0
            })
            position_crypto = 0.0

        final_balance = round(cash, 2)
        total_pnl = round(final_balance - initial_balance, 2)
        strategy_return_pct = round((total_pnl / initial_balance) * 100.0, 2)

        winning_trades = [t for t in trades if t["win"]]
        losing_trades = [t for t in trades if not t["win"]]
        win_rate = round((len(winning_trades) / len(trades) * 100.0), 1) if trades else 0.0

        gross_profits = sum(t["pnl_usd"] for t in winning_trades)
        gross_losses = abs(sum(t["pnl_usd"] for t in losing_trades))
        profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else (round(gross_profits, 2) if gross_profits > 0 else 1.0)

        return {
            "success": True,
            "symbol": symbol,
            "strategy_id": strategy_id,
            "days": len(candles),
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "net_profit": total_pnl,
            "strategy_return_pct": strategy_return_pct,
            "buy_and_hold_return_pct": buy_and_hold_return_pct,
            "outperformed_benchmark": strategy_return_pct > buy_and_hold_return_pct,
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "trades": trades,
            "equity_curve": equity_curve[::max(1, len(equity_curve)//50)],  # sample 50 points for chart
        }


backtester = BacktestEngine()
