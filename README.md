# CropBarsTelegramBot

A Telegram bot that automatically detects and removes black bars (letterboxing/pillarboxing) from videos using FFmpeg.

## Features

- Auto-detects black bars using FFmpeg's `cropdetect` filter
- Supports top, bottom, or both padding adjustments
- Handles videos sent directly or via the `/crop` reply command
- Queue-based processing with per-user concurrency limits
- Webhook-based (no polling)

## Usage

**Send a video directly** — the bot will ask where to add padding:

```
[Send video] → Bot: "Position?"
→ Choose: No Text / Top / Bottom / Both
```

**Reply to an existing video** with `/crop` — same flow.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/crop` | Reply to a video to crop it |

## Self-Hosting

### Requirements

- Python 3.10+
- FFmpeg installed and on `$PATH`
- A Telegram bot token ([@BotFather](https://t.me/BotFather))
- A public HTTPS URL for the webhook (e.g. Render, Railway)

### Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Your Telegram bot token |
| `BASE_URL` | Your public server URL|
| `WEBHOOK_SECRET` | Optional secret token for webhook verification (default: `secret`) |

### Install & Run

```bash
pip install -r requirements.txt
python main.py
```

The server starts on `0.0.0.0:7860`.

### Deploy to Render (free)

1. Push this repo to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set the start command to `python main.py`
4. Add `BOT_TOKEN`, `BASE_URL`, and `WEBHOOK_SECRET` as environment variables
5. Done — Render exposes the port and Telegram will connect automatically

## Dependencies

- [aiogram](https://github.com/aiogram/aiogram) — Telegram Bot framework
- [aiohttp](https://github.com/aio-libs/aiohttp) — Async HTTP server/client
- FFmpeg — video processing

## License

MIT
