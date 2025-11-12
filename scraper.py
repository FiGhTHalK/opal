import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta
import json

SYDNEY_TZ = timezone(timedelta(hours=11))

async def debug_transactions(username: str, password: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context()
        page = await context.new_page()

        print("The login page is now open...")
        await page.goto("https://transportnsw.info/tickets-fares/opal-login#/login")
        await page.wait_for_load_state("networkidle")

        # Log in iframe
        frames = page.frames
        target_frame = next((f for f in frames if "opal" in f.url.lower()), None)
        if not target_frame:
            print("The login iframe was not found")
            return

        await target_frame.fill('input[name="username"]', username)
        await target_frame.fill('input[name="password"]', password)
        await target_frame.click('button.opal-username-login')

        print("Wait to be redirected to the account page...")
        await page.wait_for_url("**/opal-view/#/account/cards", timeout=30000)
        print("Login successful")

        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        # Switch the date range
        option = await page.query_selector("option:text('the last 7 days')")
        if option:
            select = await option.evaluate_handle("el => el.closest('select')")
            if select:
                await select.select_option(label="October 2025")
        await asyncio.sleep(5)

        # Find the account card frame
        target_frame = None
        for f in page.frames:
            if "opal-view/#/account/cards" in f.url:
                target_frame = f
                break

        if not target_frame:
            print("Account card frame not found")
            return

        # Read the opal card information
        cards = await target_frame.query_selector_all(".opal-selector__item")
        card_data = {}
        for card in cards:
            card_text = (await card.inner_text()).strip()
            lines = card_text.splitlines()
            card_name = lines[0].strip() if len(lines) > 0 else None
            balance = None
            for line in lines[1:]:
                if "$" in line:
                    try:
                        balance = float(line.replace("$", "").strip())
                    except:
                        balance = None
                    break
            if card_name and balance is not None and card_name.lower() != "link card":
                card_data[card_name] = balance

        current_balances = [
            {"card_name": name, "balance": f"{bal:.2f} AUD"}
            for name, bal in card_data.items()
        ]

        # Traverse the transaction
        transactions = []
        date_containers = await target_frame.query_selector_all(".activity-by-date-container")
        for date_container in date_containers:
            date_text_el = await date_container.query_selector(".activity-date")
            date_text = await date_text_el.inner_text() if date_text_el else ""
            try:
                date_base = datetime.strptime(date_text.strip(), "%A %d %b %Y")
            except:
                continue

            tx_items = await date_container.query_selector_all("tni-card-activity .card-activity-item")
            for tx in tx_items:
                time_el = await tx.query_selector(".card-activity-item-middle .date")
                desc_el = await tx.query_selector(".card-activity-item-middle .description")
                amount_el = await tx.query_selector(".card-activity-item-right .amount")
                icons = await tx.query_selector_all(".icons tni-icon")

                time_str = await time_el.inner_text() if time_el else "00:00"
                desc = await desc_el.inner_text() if desc_el else ""
                amt_text = await amount_el.inner_text() if amount_el else "0"
                amt = float(amt_text.replace("$", "").replace("-", "").strip())

                # Mode of travel
                mode = None
                for icon in icons:
                    icon_name = await icon.get_attribute("iconname")
                    if icon_name:
                        mode = icon_name
                        break
                    use_el = await icon.query_selector("use")
                    if use_el:
                        href = await use_el.get_attribute("xlink:href")
                        if href:
                            if "tp_bus" in href:
                                mode = "bus"
                            elif "tp_train" in href:
                                mode = "train"
                            elif "tp_metro" in href:
                                mode = "metro"
                            elif "tp_ferry" in href:
                                mode = "ferry"
                            elif "tp_light-rail" in href:
                                mode = "light-rail"
                            break

                # tap on/off
                tap_on, tap_off = None, None
                from_el = await tx.query_selector(".from")
                to_el = await tx.query_selector(".to")

                if from_el:
                    from_text = (await from_el.inner_text()).strip()
                    if from_text.lower() != "top up":
                        tap_on = from_text
                if to_el:
                    to_text = (await to_el.inner_text()).strip()
                    if tap_on is not None:
                        tap_off = to_text

                # Time processing
                try:
                    time_local = datetime.strptime(time_str, "%H:%M").replace(
                        year=date_base.year, month=date_base.month, day=date_base.day, tzinfo=SYDNEY_TZ
                    )
                    time_utc = time_local.astimezone(timezone.utc)
                except:
                    time_local, time_utc = None, None

                transactions.append({
                    "date": date_text,
                    "time_local": time_local,
                    "time_utc": time_utc,
                    "amount": amt,
                    "currency": "AUD",
                    "description": desc,
                    "card_name": card_name,
                    "mode": mode,
                    "tap_on_location": tap_on,
                    "tap_off_location": tap_off
                })

        # Calculate the historical balance in ascending chronological order
        transactions.sort(key=lambda x: x['time_local'])
        balances = card_data.copy()
        for tx in transactions:
            name = tx['card_name']
            if name in balances:
                if "top up" in tx['description'].lower():
                    balances[name] = amt
                else:
                    balances[name] -= tx['amount']
                tx['balance'] = f"{balances[name]:.2f} AUD"
            else:
                tx['balance'] = None

            # The conversion time is ISO
            tx['time_local'] = tx['time_local'].isoformat() if tx['time_local'] else None
            tx['time_utc'] = tx['time_utc'].isoformat() if tx['time_utc'] else None

        output = {
            "current_balances": current_balances,
            "transactions": transactions
        }

        print(json.dumps(output, indent=2, ensure_ascii=False))
        await browser.close()
