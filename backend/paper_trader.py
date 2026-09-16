"""
Paper Trading Engine
Manages a zero-risk simulated trading account with live market prices.
Tracks virtual portfolio, order execution, unrealized/realized P&L,
and runs the automated real-time trading loop with risk controls.
"""

import time
import threading
from typing import Dict, List, Any, Optional
from backend.market_data import market_data
from backend.strategy import StrategyEngine


class PaperTrader:
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        # Format of position: { "quantity": float, "avg_entry_price": float, "cost_basis": float }
        self.trade_history: List[Dict[str, Any]] = []
        self.fee_rate = 0.001  # 0.1% standard exchange fee

        # Bot Settings
        self.is_bot_running = False
        self.active_symbol = "BTCUSDT"
        self.strategy_id = "ema_crossover"
        self.trade_allocation_pct = 0.25  # Use 25% of cash per trade for safety
        self.stop_loss_pct = 0.025        # 2.5% stop loss
        self.take_profit_pct = 0.050      # 5.0% take profit
        self.last_signal = {"action": "HOLD", "reason": "Bot starting up...", "time": time.time()}

        # Concurrency lock
        self._lock = threading.Lock()
        self._bot_thread: Optional[threading.Thread] = None

    def reset_account(self, new_balance: Optional[float] = None):
        """Reset the paper trading balance and wipe trade history."""
        with self._lock:
            if new_balance is not None and new_balance > 0:
                self.initial_balance = new_balance
            self.cash = self.initial_balance
            self.positions.clear()
            self.trade_history.clear()
            self.last_signal = {
                "action": "HOLD",
                "reason": f"Account reset to ${self.initial_balance:,.2f} virtual USD.",
                "time": time.time()
            }

    def execute_order(
        self, symbol: str, side: str, amount_usd: Optional[float] = None, reason: str = "Manual Trade"
    ) -> Dict[str, Any]:
        """
        Executes a simulated BUY or SELL order at current live market price.
        """
        with self._lock:
            ticker = market_data.get_ticker_24h(symbol)
            price = ticker.get("price", 0.0)
            if price <= 0:
                return {"success": False, "error": "Invalid market price"}

            timestamp = int(time.time() * 1000)

            if side.upper() == "BUY":
                # Determine how much USD to spend
                usd_to_spend = amount_usd if amount_usd else (self.cash * self.trade_allocation_pct)
                if usd_to_spend > self.cash:
                    usd_to_spend = self.cash

                if usd_to_spend < 10.0:
                    return {"success": False, "error": "Insufficient virtual cash to buy (minimum $10)."}

                fee = usd_to_spend * self.fee_rate
                net_usd = usd_to_spend - fee
                qty = net_usd / price

                self.cash -= usd_to_spend

                # Update positions
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    total_qty = pos["quantity"] + qty
                    total_cost = pos["cost_basis"] + net_usd
                    pos["quantity"] = total_qty
                    pos["cost_basis"] = total_cost
                    pos["avg_entry_price"] = total_cost / total_qty
                else:
                    self.positions[symbol] = {
                        "quantity": qty,
                        "avg_entry_price": price,
                        "cost_basis": net_usd,
                    }

                trade_entry = {
                    "id": len(self.trade_history) + 1,
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "side": "BUY",
                    "price": price,
                    "quantity": qty,
                    "usd_value": usd_to_spend,
                    "fee": fee,
                    "pnl": 0.0,
                    "pnl_pct": 0.0,
                    "reason": reason,
                }
                self.trade_history.insert(0, trade_entry)
                return {"success": True, "trade": trade_entry}

            elif side.upper() == "SELL":
                if symbol not in self.positions or self.positions[symbol]["quantity"] <= 0:
                    return {"success": False, "error": f"No open position in {symbol} to sell."}

                pos = self.positions[symbol]
                qty = pos["quantity"]
                gross_proceeds = qty * price
                fee = gross_proceeds * self.fee_rate
                net_proceeds = gross_proceeds - fee

                pnl = net_proceeds - pos["cost_basis"]
                pnl_pct = (pnl / pos["cost_basis"]) * 100.0 if pos["cost_basis"] > 0 else 0.0

                self.cash += net_proceeds
                del self.positions[symbol]

                trade_entry = {
                    "id": len(self.trade_history) + 1,
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "side": "SELL",
                    "price": price,
                    "quantity": qty,
                    "usd_value": net_proceeds,
                    "fee": fee,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": reason,
                }
                self.trade_history.insert(0, trade_entry)
                return {"success": True, "trade": trade_entry}

            return {"success": False, "error": "Invalid side (must be BUY or SELL)"}

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Calculates total portfolio equity, unrealized P&L, win rate, and balances."""
        with self._lock:
            invested_value = 0.0
            unrealized_pnl = 0.0
            position_details = []

            for symbol, pos in self.positions.items():
                ticker = market_data.get_ticker_24h(symbol)
                curr_price = ticker.get("price", pos["avg_entry_price"])
                curr_value = pos["quantity"] * curr_price
                cost_basis = pos["cost_basis"]
                pos_pnl = curr_value - cost_basis
                pos_pnl_pct = (pos_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

                invested_value += curr_value
                unrealized_pnl += pos_pnl

                position_details.append({
                    "symbol": symbol,
                    "quantity": round(pos["quantity"], 6),
                    "entry_price": round(pos["avg_entry_price"], 2),
                    "current_price": round(curr_price, 2),
                    "current_value": round(curr_value, 2),
                    "unrealized_pnl": round(pos_pnl, 2),
                    "unrealized_pnl_pct": round(pos_pnl_pct, 2),
                })

            total_equity = self.cash + invested_value
            total_net_pnl = total_equity - self.initial_balance
            total_net_pnl_pct = (total_net_pnl / self.initial_balance) * 100.0 if self.initial_balance > 0 else 0.0

            sell_trades = [t for t in self.trade_history if t["side"] == "SELL"]
            winning_trades = [t for t in sell_trades if t.get("pnl", 0.0) > 0]
            win_rate = round((len(winning_trades) / len(sell_trades) * 100.0), 1) if sell_trades else 0.0

            return {
                "initial_balance": round(self.initial_balance, 2),
                "cash": round(self.cash, 2),
                "invested_value": round(invested_value, 2),
                "total_equity": round(total_equity, 2),
                "total_net_pnl": round(total_net_pnl, 2),
                "total_net_pnl_pct": round(total_net_pnl_pct, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "positions": position_details,
                "total_trades": len(self.trade_history),
                "completed_trades": len(sell_trades),
                "win_rate": win_rate,
                "is_bot_running": self.is_bot_running,
                "active_symbol": self.active_symbol,
                "strategy_id": self.strategy_id,
                "last_signal": self.last_signal,
                "trade_history": self.trade_history[:40],
            }

    def start_bot(self):
        """Starts the automated background trading loop."""
        if self.is_bot_running:
            return
        self.is_bot_running = True
        self._bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
        self._bot_thread.start()

    def stop_bot(self):
        """Stops the automated background trading loop."""
        self.is_bot_running = False

    def _bot_loop(self):
        """Continuous automated polling and trading execution."""
        while self.is_bot_running:
            try:
                self._check_and_trade()
            except Exception as e:
                print(f"Error in bot loop: {e}")
            time.sleep(5)  # evaluate every 5 seconds

    def _check_and_trade(self):
        symbol = self.active_symbol
        candles = market_data.get_klines(symbol=symbol, interval="1h", limit=50)
        if not candles or len(candles) < 25:
            # Fallback to 15m
            candles = market_data.get_klines(symbol=symbol, interval="15m", limit=50)

        ticker = market_data.get_ticker_24h(symbol)
        curr_price = ticker.get("price", 0.0)

        if not candles or curr_price <= 0:
            return

        # 1. First, check Risk Management on open position (Stop-Loss and Take-Profit)
        with self._lock:
            if symbol in self.positions:
                pos = self.positions[symbol]
                entry = pos["avg_entry_price"]
                pnl_pct = (curr_price - entry) / entry

                if pnl_pct <= -self.stop_loss_pct:
                    # Trigger automated Stop-Loss!
                    self.execute_order(
                        symbol,
                        "SELL",
                        reason=f"🛑 Automated Stop-Loss protection (-{abs(pnl_pct*100):.2f}% below entry)"
                    )
                    self.last_signal = {
                        "action": "SELL",
                        "reason": f"Cut loss safely at -{abs(pnl_pct*100):.2f}%",
                        "time": time.time()
                    }
                    return
                elif pnl_pct >= self.take_profit_pct:
                    # Trigger automated Take-Profit!
                    self.execute_order(
                        symbol,
                        "SELL",
                        reason=f"🎯 Automated Take-Profit target (+{pnl_pct*100:.2f}% above entry)"
                    )
                    self.last_signal = {
                        "action": "SELL",
                        "reason": f"Took profit at +{pnl_pct*100:.2f}%",
                        "time": time.time()
                    }
                    return

        # 2. Evaluate Strategy
        eval_result = StrategyEngine.evaluate(self.strategy_id, candles)
        self.last_signal = {
            "action": eval_result["action"],
            "reason": eval_result["reason"],
            "confidence": eval_result.get("confidence", 50),
            "time": time.time()
        }

        # 3. Automated Trade Execution
        action = eval_result["action"]
        if action == "BUY":
            with self._lock:
                has_pos = symbol in self.positions
                has_cash = self.cash >= 20.0

            if not has_pos and has_cash:
                self.execute_order(
                    symbol,
                    "BUY",
                    reason=f"🤖 Strategy BUY: {eval_result['reason']}"
                )
        elif action == "SELL":
            with self._lock:
                has_pos = symbol in self.positions

            if has_pos:
                self.execute_order(
                    symbol,
                    "SELL",
                    reason=f"🤖 Strategy SELL: {eval_result['reason']}"
                )


# Global singleton
paper_trader = PaperTrader(initial_balance=10000.0)
