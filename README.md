# SDK SMM Services

A starter Telegram SMM services bot with a SQLite database and admin-only commands. Orders are **manual fulfilment** by default; it does not connect to a third-party SMM provider API.

## Features
- `/start` customer menu
- Categories and editable service catalog
- Link + quantity order flow with price calculation
- Balance display and balance deduction at order confirmation
- Order history and order status notifications
- Admin order notifications
- Admin commands to add/toggle services, update order statuses, and credit/debit balances
- Cancelling an order refunds its amount once
- SQLite database persists users, services, balances, and orders

## Setup
1. Install Python 3.10+.
2. Create a bot with Telegram's official BotFather and copy the token.
3. Find your numeric Telegram user ID using a trusted ID bot or another reliable method.
4. Copy `.env.example` to `.env` and fill in the values. The app does not automatically read `.env`; export the variables in your shell or use the hosting provider's environment-variable settings.
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Set environment variables:
   - Linux/macOS:
     ```bash
     export BOT_TOKEN="YOUR_TOKEN"
     export ADMIN_ID="YOUR_NUMERIC_TELEGRAM_ID"
     export BRAND_NAME="Premium SMM Services"
     export PAYMENT_TEXT="bKash/Nagad/Rocket payment instructions here"
     python bot.py
     ```
   - Windows PowerShell:
     ```powershell
     $env:BOT_TOKEN="YOUR_TOKEN"
     $env:ADMIN_ID="YOUR_NUMERIC_TELEGRAM_ID"
     $env:BRAND_NAME="Premium SMM Services"
     python bot.py
     ```

## Admin commands
- `/admin` — help
- `/addservice CATEGORY | NAME | PRICE_PER_1000 | MIN | MAX | DESCRIPTION`
- `/services` — list service IDs and prices
- `/off SERVICE_ID` and `/on SERVICE_ID`
- `/orders` — latest orders
- `/setstatus ORDER_ID In_Progress` (also `Pending`, `Completed`, `Cancelled`)
- `/credit USER_ID AMOUNT`
- `/debit USER_ID AMOUNT`
- `/users` — recent users

Example:
`/addservice Instagram | Story Views | 25 | 100 | 10000 | Manual processing`

## Important notes
- Keep your bot token private. Never upload it in a public ZIP or share it in a group.
- The admin account is identified by `ADMIN_ID`; set it to your own numeric Telegram ID.
- Payment confirmation is manual: the bot shows payment instructions, and the admin credits a user's balance after verifying the transaction.
- This starter does not include a web admin dashboard or automatic payment/provider API integration.
- Use only legitimate promotion methods and follow each platform's terms. Do not use services to fake engagement or mislead people.
