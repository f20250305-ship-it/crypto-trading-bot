# ⚡ ApexTrade: Autonomous Crypto Paper Trading Bot

An intelligent, real-time cryptocurrency trading simulation and backtesting system built for beginners and algorithmic traders.

> **Zero Financial Risk ($0 Real Money Required)**  
> Real crypto exchanges (Binance, Coinbase, Kraken) require deposited funds to buy real crypto assets. This application runs in **Paper Trading Mode** using **100% live, real-time cryptocurrency market feeds** from public exchange endpoints without requiring any real money, account signups, credit cards, or API keys.

---

## 🚀 Quick Start

### 1. Run the Bot
Open PowerShell or Command Prompt, navigate to the folder, and run:
```powershell
python run_bot.py
```

Your web browser will automatically open to:
```
http://localhost:8000
```

---

## 🌟 Key Features

1. **Real-Time Live Market Data**:
   - Live prices, 24h volume, high/low, and price change percentage streamed directly from Binance public feeds.
   - Interactive price chart with **Fast EMA (9)** and **Slow EMA (21)** indicator overlays.
   - Supported pairs: **BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, DOGE/USDT**.

2. **Autonomous Auto-Trading Engine**:
   - Toggle the bot **ON** with a single switch.
   - The bot evaluates market momentum every 5 seconds.
   - Executes simulated paper orders automatically when high-confidence signals occur.

3. **1-Year Historical Backtester**:
   - Run a 365-day backtest with a single click.
   - Compares the algorithm's performance directly against **Buy & Hold**.
   - Displays **Win Rate (%)**, **Total Return (%)**, **Maximum Drawdown (%)**, and full trade history.

4. **Built-In Risk Management**:
   - **Stop-Loss Protection**: Automatically sells if an open position drops below a set threshold (e.g. -2.5%) to prevent big losses.
   - **Take-Profit Target**: Automatically locks in gains when target profit (e.g. +5.0%) is reached.

5. **Beginner "Trading 101" Knowledge Hub**:
   - Embedded interactive guide explaining candlesticks, moving averages, RSI, and risk management in plain English.

---

## 🧠 Trading Concepts Explained for Beginners

### 1. What is Paper Trading?
Paper trading simulates buying and selling using real market prices, but with virtual currency. You start with **$10,000 in virtual USD**. It allows you to learn how trading works without risking real money.

### 2. Moving Average Crossover (Trend Following)
- **Fast EMA (9 periods)**: Reflects short-term price momentum.
- **Slow EMA (21 periods)**: Reflects longer-term market trend.
- **Golden Cross (Buy)**: Fast EMA crosses **above** Slow EMA $\rightarrow$ Buyers are in control.
- **Death Cross (Sell)**: Fast EMA crosses **below** Slow EMA $\rightarrow$ Downward momentum detected.

### 3. Relative Strength Index (RSI)
- Oscillates between 0 and 100.
- **RSI < 30 (Oversold)**: Price may have fallen too fast; potential buying rebound.
- **RSI > 70 (Overbought)**: Price may be overextended; potential profit-taking zone.

### 4. Stop-Loss & Capital Preservation
The most important rule in trading: **cut losses quickly and let winners run**. If the market unexpectedly drops, the Stop-Loss immediately sells the position to preserve virtual capital.

---

## 📂 Project Architecture

```
crypto-trading-bot/
├── backend/
│   ├── market_data.py    # Fetches real-time prices & klines from Binance public API
│   ├── strategy.py       # Pure Python technical indicators (EMA, RSI, MACD, signals)
│   ├── backtester.py     # 365-day historical simulation engine & benchmark comparison
│   ├── paper_trader.py   # Virtual portfolio, order execution, & automated bot thread
│   └── server.py         # Zero-dependency HTTP REST API & static file server
├── frontend/
│   ├── index.html        # Modern dashboard layout & trading controls
│   ├── style.css         # High-aesthetic dark mode financial UI
│   └── app.js            # Real-time polling, Chart.js graphs, & trade execution
├── run_bot.py            # Main launcher script (starts server & opens browser)
└── README.md             # Beginner guide & documentation
```
