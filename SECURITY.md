# Security Policy

## Supported Versions

| Version | Supported          | Description |
| ------- | ------------------ | ----------- |
| 1.0.x   | :white_check_mark: | Active release |
| < 1.0   | :x:                | Unsupported |

---

## 🔒 Security Best Practices & API Key Safety

The **Crypto Trading Bot** includes real-time Binance public feeds and simulated paper-trading engines. To protect user assets and API credentials:

1. **Simulated Paper Trading Mode**:
   - The default configuration operates strictly on **simulated virtual funds** ($10,000 USD virtual balance).
   - No real capital or financial risk is incurred during backtesting and paper trading.

2. **API Keys & Secret Management**:
   - Never commit private API keys, Binance secret keys, or environment files (`.env`) to Git repositories.
   - All sensitive credentials must be loaded via environment variables and excluded by [.gitignore](.gitignore).
   - Read-only permissions should always be used when querying public market order books.

---

## 🚨 Reporting Security Issues

If you discover a vulnerability or security risk, please report it responsibly:

- **Email**: [f20250305@dubai.bits-pilani.ac.in](mailto:f20250305@dubai.bits-pilani.ac.in)
- **Subject**: `[SECURITY VULNERABILITY] Crypto Trading Bot - <Summary>`

Please include a description of the vulnerability, steps to reproduce, and potential impact. We will acknowledge receipt within 48 hours and work on a fix promptly.
