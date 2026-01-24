# BTC Opportunity Cost Bot

Calculate what your purchases would be worth today if you'd bought Bitcoin instead.

## Features

- **AI-Powered Research**: Just tell the bot what you bought in plain English
- **Historical BTC Prices**: Uses CryptoCompare for accurate data back to 2010
- **Clean Chat**: Following telegram-bot design guide principles

## Usage Examples

- "iPhone 16 in September 2024"
- "100 shares of GOOG in January 2020"
- "$500 of ETH in March 2021"

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather |
| `OPENAI_API_KEY` | OpenAI API key for price research |
| `WEBHOOK_URL` | Your Railway app URL + `/webhook` |
| `DATABASE_PATH` | Path to SQLite database (use `/data/bot.db` on Railway) |

## Local Development

```bash
pip install -r requirements.txt
python -m bot.main --polling
```

## Deployment

Deploy to Railway with a persistent volume mounted at `/data`.
