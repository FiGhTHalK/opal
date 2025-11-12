# Opal Card Transaction Scraper

This Python script logs into your Opal account and retrieves your Opal card transactions and balances.  
It uses **Playwright** for browser automation and outputs a JSON file with:

- Current card balances
- Historical transactions with per-transaction balance

---

## Features

- Logs into Opal account using username & password
- Switches date range to a target month (October 2025 by default)
- Retrieves transactions including:
  - Amount, date & time
  - Description
  - Mode of travel (bus/train/metro/ferry/light-rail)
  - Tap on/off locations
  - Balance after each transaction
- Outputs results to JSON and prints to console

---
