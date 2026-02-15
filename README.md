# ALL-ID2
# Multi-Exchange Intraday Engine (TSX/NASDAQ/NYSE)

This repository contains a **semi-automated intraday trading dashboard** that monitors top TSX, NASDAQ, and NYSE stocks using **technical signals** (EMA10/EMA30 crossover + RSI7).  

It calculates **buy/sell prices, trailing stops, take-profit/stop-loss**, and shows **real-time intraday charts** with equity curve tracking.

---

## Features

- Multi-tab view: TSX, NASDAQ, NYSE
- Intraday charts (5-min for TSX/US)
- Buy & Sell signals with score
- Portfolio allocation simulation
- Trailing stop, stop-loss, take-profit management
- Alerts & equity curve

---

## Installation

```bash
git clone https://github.com/<your_username>/multi-exchange-intraday.git
cd multi-exchange-intraday
pip install -r requirements.txt
