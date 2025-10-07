# Twitter Bot (Python)

A production-ready Twitter bot with:
- Daily quote posting (9 AM IST) with images/hashtags
- Auto-replies to mentions/DMs using GPT-4
- Hashtag monitoring with lead scoring and engagement
- Sentiment analysis with alerts and daily report
- Analytics dashboard data collection and CSV export

## Tech Stack
- Python 3.10+
- Tweepy (Twitter API v2 + v1.1 media)
- OpenAI GPT-4 (via `openai` Python SDK)
- SQLite (via `sqlite3`)
- APScheduler (cron jobs)
- VADER sentiment
- Pillow (image generation)

## Setup
1. Create virtual environment and install dependencies:
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and fill keys:
```
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
TWITTER_BEARER_TOKEN=...
OPENAI_API_KEY=...
```

3. Run the bot:
```bash
python -m twitter_bot.main
```

The bot will:
- Schedule the daily quote at 09:00 IST
- Poll mentions every minute and reply within 2 minutes
- Monitor hashtags every 10 minutes
- Generate a daily analytics CSV report

## Project Structure
```
twitter_bot/
├── main.py
├── config.py
├── bot/
│   ├── quote_poster.py
│   ├── reply_handler.py
│   ├── hashtag_monitor.py
│   ├── sentiment_analyzer.py
│   └── analytics.py
├── utils/
│   ├── twitter_api.py
│   ├── openai_helper.py
│   └── database.py
├── data/
│   ├── quotes.json
│   └── bot.db (auto-created)
├── requirements.txt
└── .env.example
```

## Notes
- API keys are read from environment variables.
- DB initializes automatically on first run.
- Rate limiting and retries are implemented with backoff.
- If media upload or DMs are restricted for your account level, functions will log warnings and continue gracefully.
