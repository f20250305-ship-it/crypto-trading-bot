"""
Backend Server Module
Provides a high-performance, zero-dependency HTTP REST API
and serves the real-time frontend dashboard.
Uses Python's built-in http.server.ThreadingHTTPServer.
"""

import json
import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any

from backend.market_data import market_data
from backend.strategy import StrategyEngine, calculate_ema, calculate_rsi
from backend.backtester import backtester
from backend.paper_trader import paper_trader

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")


class TradingBotHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set frontend directory as root for static assets
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_json(self, data: Any, status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API Routes
        if path == "/api/status":
            summary = paper_trader.get_portfolio_summary()
            self._send_json(summary)
            return

        elif path == "/api/pairs":
            pairs = market_data.get_supported_pairs()
            self._send_json({"pairs": pairs})
            return

        elif path == "/api/ticker":
            symbol = query.get("symbol", [paper_trader.active_symbol])[0].upper()
            ticker = market_data.get_ticker_24h(symbol)
            self._send_json(ticker)
            return

        elif path == "/api/candles":
            symbol = query.get("symbol", [paper_trader.active_symbol])[0].upper()
            interval = query.get("interval", ["1h"])[0]
            limit = int(query.get("limit", ["80"])[0])
            candles = market_data.get_klines(symbol, interval=interval, limit=limit)

            # Enrich with indicators for chart display
            close_prices = [c["close"] for c in candles]
            ema9 = calculate_ema(close_prices, 9)
            ema21 = calculate_ema(close_prices, 21)
            rsi = calculate_rsi(close_prices, 14)

            enriched = []
            for i, c in enumerate(candles):
                enriched.append({
                    **c,
                    "ema9": ema9[i],
                    "ema21": ema21[i],
                    "rsi": rsi[i],
                })

            self._send_json({"symbol": symbol, "interval": interval, "candles": enriched})
            return

        elif path == "/api/strategies":
            strategies = StrategyEngine.get_available_strategies()
            self._send_json({"strategies": strategies})
            return

        # Serve frontend index or static files
        if path == "/" or not os.path.exists(os.path.join(FRONTEND_DIR, path.lstrip("/"))):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        if path == "/api/bot/toggle":
            enabled = payload.get("enabled", not paper_trader.is_bot_running)
            if enabled:
                paper_trader.start_bot()
            else:
                paper_trader.stop_bot()
            self._send_json({"success": True, "is_bot_running": paper_trader.is_bot_running})
            return

        elif path == "/api/bot/settings":
            if "symbol" in payload:
                paper_trader.active_symbol = payload["symbol"].upper()
            if "strategy_id" in payload:
                paper_trader.strategy_id = payload["strategy_id"]
            if "stop_loss_pct" in payload:
                paper_trader.stop_loss_pct = float(payload["stop_loss_pct"]) / 100.0
            if "take_profit_pct" in payload:
                paper_trader.take_profit_pct = float(payload["take_profit_pct"]) / 100.0
            if "allocation_pct" in payload:
                paper_trader.trade_allocation_pct = float(payload["allocation_pct"]) / 100.0

            self._send_json({
                "success": True,
                "settings": {
                    "symbol": paper_trader.active_symbol,
                    "strategy_id": paper_trader.strategy_id,
                    "stop_loss_pct": paper_trader.stop_loss_pct * 100.0,
                    "take_profit_pct": paper_trader.take_profit_pct * 100.0,
                    "allocation_pct": paper_trader.trade_allocation_pct * 100.0,
                }
            })
            return

        elif path == "/api/backtest":
            symbol = payload.get("symbol", paper_trader.active_symbol)
            strat = payload.get("strategy_id", paper_trader.strategy_id)
            initial = float(payload.get("initial_balance", 10000.0))
            days = int(payload.get("days", 365))
            sl = float(payload.get("stop_loss_pct", 3.0)) / 100.0
            tp = float(payload.get("take_profit_pct", 6.0)) / 100.0

            result = backtester.run_backtest(
                symbol=symbol,
                strategy_id=strat,
                initial_balance=initial,
                days=days,
                stop_loss_pct=sl,
                take_profit_pct=tp,
            )
            self._send_json(result)
            return

        elif path == "/api/trade":
            symbol = payload.get("symbol", paper_trader.active_symbol)
            side = payload.get("side", "BUY")
            usd_amount = float(payload.get("amount_usd", 1000.0)) if "amount_usd" in payload else None
            res = paper_trader.execute_order(symbol, side, amount_usd=usd_amount, reason="Manual User Order")
            self._send_json(res)
            return

        elif path == "/api/reset":
            new_bal = float(payload.get("balance", 10000.0))
            paper_trader.reset_account(new_bal)
            self._send_json({"success": True, "message": f"Account reset to ${new_bal:,.2f} virtual USD."})
            return

        self._send_json({"error": "Endpoint not found"}, status_code=404)


def run_server(port: int = 8000):
    server = ThreadingHTTPServer(("127.0.0.1", port), TradingBotHTTPHandler)
    print(f"\n=======================================================")
    print(f"  🚀 Real-Time Crypto Trading Bot & Dashboard")
    print(f"  🌐 Open in your browser: http://localhost:{port}")
    print(f"  💡 Zero financial risk (Paper Trading Mode)")
    print(f"=======================================================\n")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
