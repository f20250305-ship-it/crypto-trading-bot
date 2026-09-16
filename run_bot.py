"""
Crypto Paper Trading Bot Runner
Entry point to launch the local trading server and dashboard.
"""

import sys
import os
import webbrowser
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.server import run_server

def main():
    print("""
    ================================================================
    🤖 CRYPTO TRADING BOT (SIMULATION & BACKTESTING ENGINE)
    ================================================================
    ✔ Live Public Price Feed: Connected (Binance Public API)
    ✔ Account Mode: Zero-Risk Paper Trading ($0 Real Money Required)
    ✔ Virtual Starting Capital: $10,000.00 Simulated USD
    ✔ Backtesting: 365-Day Historical Strategy Performance
    ================================================================
    """)

    port = 8000
    dashboard_url = f"http://localhost:{port}"

    # Auto-open browser after 1 second delay
    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    run_server(port=port)

if __name__ == "__main__":
    main()
