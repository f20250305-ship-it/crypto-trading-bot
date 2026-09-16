/**
 * ApexTrade • Real-Time Frontend Controller
 * Handles Chart.js visualization, real-time polling, trade execution,
 * and historical backtest rendering.
 */

// State Management
const state = {
  activeSymbol: "BTCUSDT",
  activeInterval: "1h",
  isBotRunning: false,
  previousPrice: 0,
  chartInstance: null,
  backtestChartInstance: null,
};

// DOM Elements
const el = {
  symbolSelect: document.getElementById("symbolSelect"),
  livePrice: document.getElementById("livePrice"),
  liveChange: document.getElementById("liveChange"),
  liveHigh: document.getElementById("liveHigh"),
  liveLow: document.getElementById("liveLow"),
  botToggle: document.getElementById("botToggle"),
  botStateLabel: document.getElementById("botStateLabel"),
  totalEquity: document.getElementById("totalEquity"),
  pnlBadge: document.getElementById("pnlBadge"),
  cashBalance: document.getElementById("cashBalance"),
  netProfitVal: document.getElementById("netProfitVal"),
  openPositionVal: document.getElementById("openPositionVal"),
  unrealizedPnlSub: document.getElementById("unrealizedPnlSub"),
  winRateVal: document.getElementById("winRateVal"),
  completedTradesCount: document.getElementById("completedTradesCount"),
  chartTitle: document.getElementById("chartTitle"),
  marketChartCanvas: document.getElementById("marketChart"),
  signalAction: document.getElementById("signalAction"),
  signalSummary: document.getElementById("signalSummary"),
  signalExplanation: document.getElementById("signalExplanation"),
  strategySelect: document.getElementById("strategySelect"),
  strategyDesc: document.getElementById("strategyDesc"),
  stopLossInput: document.getElementById("stopLossInput"),
  takeProfitInput: document.getElementById("takeProfitInput"),
  runBacktestBtn: document.getElementById("runBacktestBtn"),
  backtestResults: document.getElementById("backtestResults"),
  tradeLogBody: document.getElementById("tradeLogBody"),
  manualAmount: document.getElementById("manualAmount"),
  manualBuyBtn: document.getElementById("manualBuyBtn"),
  manualSellBtn: document.getElementById("manualSellBtn"),
  resetBtn: document.getElementById("resetBtn"),
  guideBtn: document.getElementById("guideBtn"),
  guideModal: document.getElementById("guideModal"),
  modalCloseBtn: document.getElementById("modalCloseBtn"),
  modalUnderstoodBtn: document.getElementById("modalUnderstoodBtn"),
};

// ==========================================
// Initialization
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  initChart();
  bindEvents();
  fetchMarketData();
  fetchPortfolioStatus();
  fetchCandles();

  // Start 2-second real-time polling loop
  setInterval(fetchMarketData, 2000);
  setInterval(fetchPortfolioStatus, 2500);
  setInterval(fetchCandles, 8000); // refresh candles every 8s
});

// ==========================================
// Event Listeners
// ==========================================
function bindEvents() {
  // Symbol change
  el.symbolSelect.addEventListener("change", (e) => {
    state.activeSymbol = e.target.value;
    el.chartTitle.textContent = `${formatSymbol(state.activeSymbol)} Real-Time Market`;
    updateBotSettings();
    fetchMarketData();
    fetchCandles();
  });

  // Timeframe pills
  document.querySelectorAll(".timeframe-pills .pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".timeframe-pills .pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeInterval = pill.dataset.interval;
      fetchCandles();
    });
  });

  // Bot master switch
  el.botToggle.addEventListener("change", async (e) => {
    const isChecked = e.target.checked;
    try {
      const res = await fetch("/api/bot/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: isChecked }),
      });
      const data = await res.json();
      setBotStateUI(data.is_bot_running);
    } catch (err) {
      console.error("Failed to toggle bot:", err);
      el.botToggle.checked = !isChecked;
    }
  });

  // Strategy descriptions
  el.strategySelect.addEventListener("change", (e) => {
    const descMap = {
      ema_crossover: "Buys when short-term momentum (EMA 9) crosses above long-term trend (EMA 21).",
      rsi_reversal: "Buys when asset is oversold (RSI < 30) and recovering. Sells when overbought (RSI > 70).",
      macd_momentum: "Trades based on MACD histogram expansion and momentum crossovers.",
    };
    el.strategyDesc.textContent = descMap[e.target.value] || "";
    updateBotSettings();
  });

  // Risk inputs
  el.stopLossInput.addEventListener("change", updateBotSettings);
  el.takeProfitInput.addEventListener("change", updateBotSettings);

  // Run Backtest
  el.runBacktestBtn.addEventListener("click", runHistoricalBacktest);

  // Manual Trades
  el.manualBuyBtn.addEventListener("click", () => executeManualTrade("BUY"));
  el.manualSellBtn.addEventListener("click", () => executeManualTrade("SELL"));

  // Reset Account
  el.resetBtn.addEventListener("click", async () => {
    if (confirm("Reset virtual account back to $10,000.00 virtual cash and clear trade history?")) {
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ balance: 10000.0 }),
      });
      fetchPortfolioStatus();
    }
  });

  // Guide Modal
  el.guideBtn.addEventListener("click", () => el.guideModal.classList.add("active"));
  el.modalCloseBtn.addEventListener("click", () => el.guideModal.classList.remove("active"));
  el.modalUnderstoodBtn.addEventListener("click", () => el.guideModal.classList.remove("active"));
  el.guideModal.addEventListener("click", (e) => {
    if (e.target === el.guideModal) el.guideModal.classList.remove("active");
  });
}

function setBotStateUI(isRunning) {
  state.isBotRunning = isRunning;
  el.botToggle.checked = isRunning;
  if (isRunning) {
    el.botStateLabel.textContent = "ON";
    el.botStateLabel.className = "bot-state-text state-on";
  } else {
    el.botStateLabel.textContent = "OFF";
    el.botStateLabel.className = "bot-state-text state-off";
  }
}

async function updateBotSettings() {
  try {
    await fetch("/api/bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: state.activeSymbol,
        strategy_id: el.strategySelect.value,
        stop_loss_pct: parseFloat(el.stopLossInput.value) || 2.5,
        take_profit_pct: parseFloat(el.takeProfitInput.value) || 5.0,
      }),
    });
  } catch (err) {
    console.error("Failed to update bot settings:", err);
  }
}

// ==========================================
// Market Data & Ticker
// ==========================================
async function fetchMarketData() {
  try {
    const res = await fetch(`/api/ticker?symbol=${state.activeSymbol}`);
    const data = await res.json();
    if (!data || !data.price) return;

    const price = data.price;
    const formattedPrice = formatCurrency(price);
    el.livePrice.textContent = formattedPrice;

    // Price flash animation
    if (state.previousPrice > 0) {
      if (price > state.previousPrice) {
        el.livePrice.classList.add("price-flash-green");
        setTimeout(() => el.livePrice.classList.remove("price-flash-green"), 400);
      } else if (price < state.previousPrice) {
        el.livePrice.classList.add("price-flash-red");
        setTimeout(() => el.livePrice.classList.remove("price-flash-red"), 400);
      }
    }
    state.previousPrice = price;

    // 24h stats
    const change = data.change_24h || 0;
    el.liveChange.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
    el.liveChange.style.color = change >= 0 ? "var(--color-green)" : "var(--color-red)";

    el.liveHigh.textContent = formatCurrency(data.high_24h || 0);
    el.liveLow.textContent = formatCurrency(data.low_24h || 0);
  } catch (err) {
    console.error("Error fetching ticker:", err);
  }
}

// ==========================================
// Portfolio & Status
// ==========================================
async function fetchPortfolioStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (!data) return;

    // Sync bot state
    if (el.botToggle.checked !== data.is_bot_running) {
      setBotStateUI(data.is_bot_running);
    }

    // Balances
    el.totalEquity.textContent = formatCurrency(data.total_equity);
    el.cashBalance.textContent = formatCurrency(data.cash);

    const netPnl = data.total_net_pnl;
    const netPnlPct = data.total_net_pnl_pct;
    const sign = netPnl >= 0 ? "+" : "";

    el.pnlBadge.textContent = `${sign}${netPnlPct.toFixed(2)}%`;
    el.pnlBadge.style.backgroundColor = netPnl >= 0 ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)";
    el.pnlBadge.style.color = netPnl >= 0 ? "var(--color-green)" : "var(--color-red)";

    el.netProfitVal.textContent = `${sign}${formatCurrency(netPnl)}`;
    el.netProfitVal.style.color = netPnl >= 0 ? "var(--color-green)" : "var(--color-red)";

    // Open positions
    if (data.positions && data.positions.length > 0) {
      const pos = data.positions[0];
      const pnlSign = pos.unrealized_pnl >= 0 ? "+" : "";
      el.openPositionVal.textContent = `${pos.quantity} ${pos.symbol.replace("USDT", "")}`;
      el.unrealizedPnlSub.innerHTML = `Unrealized P&L: <strong style="color:${pos.unrealized_pnl >= 0 ? 'var(--color-green)' : 'var(--color-red)'}">${pnlSign}${formatCurrency(pos.unrealized_pnl)} (${pnlSign}${pos.unrealized_pnl_pct.toFixed(2)}%)</strong>`;
    } else {
      el.openPositionVal.textContent = "No Active Trade";
      el.unrealizedPnlSub.innerHTML = `Unrealized P&L: <span>$0.00</span>`;
    }

    // Performance
    el.winRateVal.textContent = `${data.win_rate}% Win Rate`;
    el.completedTradesCount.textContent = data.completed_trades || 0;

    // Signal Feed
    if (data.last_signal) {
      const sig = data.last_signal;
      el.signalAction.textContent = sig.action;
      el.signalAction.className = `signal-action-pill signal-${sig.action.toLowerCase()}`;
      el.signalSummary.textContent = `${sig.action} Signal • Confidence: ${sig.confidence || 50}%`;
      el.signalExplanation.textContent = sig.reason || "Analyzing market...";
    }

    // Trade Log
    renderTradeLog(data);
  } catch (err) {
    console.error("Error fetching status:", err);
  }
}

// ==========================================
// Chart.js Live Market Chart
// ==========================================
function initChart() {
  const ctx = el.marketChartCanvas.getContext("2d");

  state.chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Price ($)",
          data: [],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.05)",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: true,
          tension: 0.15,
        },
        {
          label: "Fast EMA (9)",
          data: [],
          borderColor: "#06b6d4",
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
        },
        {
          label: "Slow EMA (21)",
          data: [],
          borderColor: "#f59e0b",
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: "#1e293b",
          titleColor: "#94a3b8",
          bodyColor: "#f1f5f9",
          borderColor: "#334155",
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.03)" },
          ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 8 },
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#64748b",
            font: { family: "JetBrains Mono", size: 10 },
            callback: (val) => `$${val.toLocaleString()}`,
          },
        },
      },
    },
  });
}

async function fetchCandles() {
  try {
    const res = await fetch(`/api/candles?symbol=${state.activeSymbol}&interval=${state.activeInterval}&limit=60`);
    const data = await res.json();
    if (!data || !data.candles || data.candles.length === 0) return;

    const labels = [];
    const prices = [];
    const ema9 = [];
    const ema21 = [];

    data.candles.forEach((c) => {
      const dt = new Date(c.timestamp);
      const timeStr = state.activeInterval === "1d" 
        ? `${dt.getMonth() + 1}/${dt.getDate()}` 
        : `${dt.getHours().toString().padStart(2, "0")}:${dt.getMinutes().toString().padStart(2, "0")}`;
      labels.push(timeStr);
      prices.push(c.close);
      ema9.push(c.ema9 > 0 ? c.ema9 : null);
      ema21.push(c.ema21 > 0 ? c.ema21 : null);
    });

    state.chartInstance.data.labels = labels;
    state.chartInstance.data.datasets[0].data = prices;
    state.chartInstance.data.datasets[1].data = ema9;
    state.chartInstance.data.datasets[2].data = ema21;
    state.chartInstance.update();
  } catch (err) {
    console.error("Error fetching candles:", err);
  }
}

// ==========================================
// Historical Backtesting
// ==========================================
async function runHistoricalBacktest() {
  const btn = el.runBacktestBtn;
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Simulating 365 Days on Real Data...</span>`;
  el.backtestResults.innerHTML = `<div class="backtest-placeholder">Simulating algorithmic strategy on historical 365-day candlestick data...</div>`;

  try {
    const res = await fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: state.activeSymbol,
        strategy_id: el.strategySelect.value,
        days: 365,
        stop_loss_pct: parseFloat(el.stopLossInput.value) || 2.5,
        take_profit_pct: parseFloat(el.takeProfitInput.value) || 5.0,
      }),
    });
    const data = await res.json();

    if (!data.success) {
      el.backtestResults.innerHTML = `<div class="backtest-placeholder" style="color:var(--color-red)">${data.error || "Backtest failed."}</div>`;
      return;
    }

    renderBacktestResults(data);
  } catch (err) {
    console.error("Backtest error:", err);
    el.backtestResults.innerHTML = `<div class="backtest-placeholder" style="color:var(--color-red)">Network error running backtest.</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span class="btn-icon">⚡</span> Run 1-Year Historical Backtest`;
  }
}

function renderBacktestResults(res) {
  const isProfit = res.strategy_return_pct >= 0;
  const stratClass = isProfit ? "positive" : "negative";
  const stratSign = isProfit ? "+" : "";
  const bhClass = res.buy_and_hold_return_pct >= 0 ? "positive" : "negative";
  const bhSign = res.buy_and_hold_return_pct >= 0 ? "+" : "";

  el.backtestResults.innerHTML = `
    <div class="bt-stat-grid">
      <div class="bt-stat-box">
        <span class="bt-label">Strategy Return (1-Yr)</span>
        <span class="bt-val ${stratClass}">${stratSign}${res.strategy_return_pct}%</span>
      </div>
      <div class="bt-stat-box">
        <span class="bt-label">Buy & Hold Benchmark</span>
        <span class="bt-val ${bhClass}">${bhSign}${res.buy_and_hold_return_pct}%</span>
      </div>
      <div class="bt-stat-box">
        <span class="bt-label">Win Rate (${res.winning_trades}/${res.total_trades} trades)</span>
        <span class="bt-val">${res.win_rate}%</span>
      </div>
      <div class="bt-stat-box">
        <span class="bt-label">Max Drawdown (Risk)</span>
        <span class="bt-val negative">-${res.max_drawdown_pct}%</span>
      </div>
    </div>
    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.5rem; line-height: 1.4;">
      ${res.outperformed_benchmark 
        ? `🔥 <strong style="color:var(--color-green)">Strategy beat Buy & Hold!</strong> The automated rules protected capital during drops while capturing upside momentum.` 
        : `ℹ️ <em>Strategy yielded ${stratSign}${res.strategy_return_pct}%.</em> Adjust stop-loss or strategy indicators to optimize performance.`}
    </div>
  `;
}

// ==========================================
// Manual Trade Execution
// ==========================================
async function executeManualTrade(side) {
  const amount = parseFloat(el.manualAmount.value) || 1000;
  try {
    const res = await fetch("/api/trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: state.activeSymbol,
        side: side,
        amount_usd: amount,
      }),
    });
    const data = await res.json();
    if (data.success) {
      fetchPortfolioStatus();
    } else {
      alert(`Trade error: ${data.error}`);
    }
  } catch (err) {
    console.error("Trade execution error:", err);
  }
}

// ==========================================
// Render Trade History
// ==========================================
function renderTradeLog(data) {
  const trades = data.trade_history || [];
  if (!trades || trades.length === 0) {
    el.tradeLogBody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center empty-state">No trades executed yet. Toggle the bot ON or place a test order below.</td>
      </tr>
    `;
    return;
  }

  el.tradeLogBody.innerHTML = trades.map((t) => {
    const dt = new Date(t.timestamp);
    const timeStr = `${dt.getHours().toString().padStart(2, '0')}:${dt.getMinutes().toString().padStart(2, '0')}:${dt.getSeconds().toString().padStart(2, '0')}`;
    const isBuy = t.side.toUpperCase() === "BUY";
    const badgeClass = isBuy ? "trade-buy" : "trade-sell";
    const pnlSign = t.pnl >= 0 ? "+" : "";
    const pnlColor = t.pnl > 0 ? "var(--color-green)" : (t.pnl < 0 ? "var(--color-red)" : "var(--text-muted)");
    const pnlDisplay = isBuy ? "—" : `<span style="color:${pnlColor}; font-weight:700;">${pnlSign}$${t.pnl.toFixed(2)} (${pnlSign}${t.pnl_pct.toFixed(2)}%)</span>`;

    return `
      <tr>
        <td style="color: var(--text-muted);">${timeStr}</td>
        <td><span class="trade-badge ${badgeClass}">${t.side}</span></td>
        <td style="font-weight: 600;">${t.symbol.replace("USDT", "")}</td>
        <td>$${t.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        <td>${t.quantity.toFixed(5)}</td>
        <td>$${t.usd_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        <td>${pnlDisplay}</td>
        <td style="font-size: 0.72rem; color: var(--text-secondary); max-width: 220px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${t.reason}">${t.reason}</td>
      </tr>
    `;
  }).join("");
}
// ==========================================
// Helpers
// ==========================================
function formatCurrency(num) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(num);
}

function formatSymbol(sym) {
  return sym.replace("USDT", "/USDT");
}
