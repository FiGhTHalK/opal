import asyncio
import json
from scraper import debug_transactions

if __name__ == "__main__":
    username = "wushichu2000@gmail.com" # your_email@example.com
    password = "Halk0825" # YourPassword
    results = asyncio.run(debug_transactions(username, password))

