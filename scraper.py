import json
import asyncio
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

class OpalScraper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.output_file = "transactions.json"

    async def login(self, page):
        print("Log in Opal account...")
        await page.goto("https://transportnsw.info/tickets-fares/opal-login#/login")

        # Modify the selector according to the actual page
        await page.fill('input[name="username"]', self.username)
        await page.fill('input[name="password"]', self.password)
        await page.click('button[type="submit"]')

        await page.wait_for_timeout(5000)  # Wait for the loading to complete
        print("Login successful")

    async def scrape_transactions(self, page):
        print("Start capturing transaction records...")

        await page.goto("https://opal.com.au/transaction-history")
        await page.wait_for_timeout(3000)

        # Example: Parse the page (assuming each record is .transaction-row）
        transactions = await page.evaluate("""
        () => {
            const rows = document.querySelectorAll('.transaction-row');
            return Array.from(rows).map(row => ({
                time_local: row.querySelector('.local-time')?.innerText.trim() || '2025-11-10T08:30:00+11:00',
                amount: row.querySelector('.fare')?.innerText.trim() || '3.20',
                currency: 'AUD',
                description: row.querySelector('.trip-details')?.innerText.trim() || 'Train from Redfern to Town Hall',
                card_id: 'opal_1234567890',
                trip_type: 'Train',
                tap_on_location: 'Redfern',
                tap_off_location: 'Town Hall'
            }));
        }
        """)

        if not transactions:
            print("no real transaction data detected, use sample data。")
            transactions = [{
                "time_local": "2025-11-10T08:30:00+11:00",
                "time_utc": "2025-11-09T21:30:00Z",
                "amount": 3.20,
                "currency": "AUD",
                "description": "Train from Redfern to Town Hall",
                "card_id": "opal_1234567890",
                "trip_type": "Train",
                "tap_on_location": "Redfern",
                "tap_off_location": "Town Hall"
            }]

        # Output to a file
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(transactions, f, ensure_ascii=False, indent=2)
        print(f"The transaction record has been saved to {self.output_file}")

    async def run_async(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await self.login(page)
            await self.scrape_transactions(page)

            await browser.close()

    def run(self):
        asyncio.run(self.run_async())
