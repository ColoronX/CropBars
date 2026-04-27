# CropBarsTelegramBot

A Telegram bot that automatically detects and removes black bars (letterboxing/pillarboxing) from videos using FFmpeg. It features an asynchronous worker queue to handle processing-heavy tasks efficiently.

## Features

- Automatic black bar detection using FFmpeg's cropdetect filter.
- Support for custom padding: Top, Bottom, Both, or None.
- Queue-based processing with a configurable number of workers.
- Per-user concurrency limits to prevent resource exhaustion.
- Built-in health check server for compatibility with hosting platforms like Render.
- Handles videos sent directly or via the /crop reply command.

## Usage

1. Send a video or document directly to the bot.
2. Alternatively, reply to an existing video with the /crop command.
3. The bot will present an inline keyboard asking for the padding position:
   - No Text: Strict crop to detected content.
   - Top: Adds 30px padding to the top (useful for UI).
   - Bottom: Adds 30px padding to the bottom (useful for subtitles).
   - Both: Adds 30px padding to both top and bottom.

## Commands

| Command | Description |
|---------|-------------|
| /start | Display welcome message |
| /crop | Reply to a video with this command to initiate cropping |

## Configuration

The bot is configured via environment variables.

| Variable | Description | Default |
|----------|-------------|---------|
| BOT_TOKEN | Your Telegram bot token from @BotFather | Required |


## Self-Hosting

### Requirements

- Python 3.x
- FFmpeg installed and accessible in the system PATH.
- A public-facing port (if using health checks for monitoring).

### Installation

```bash
pip install -r requirements.txt
```

# Running the Bot

## Bash

```bash
export BOT_TOKEN="your_bot_token_here"
python main.py
```

The bot runs in **polling mode** but also starts a **web server on `0.0.0.0:7860`** for health checks.

---

# Deployment to Render

1. Create a new **Web Service** on Render.  
2. Connect your repository.  
3. Set **Runtime** to *Python*.  
4. Set the **Start Command** to:
 ```bash
   python main.py
   ```

5. Add `BOT_TOKEN` to the **Environment Variables**.  
6. Render will automatically detect the server on **port 7860** to verify the service is live.

---

# Technical Details

### Framework  
- **aiogram 3.x** for asynchronous Telegram interaction.

### Processing Engine  
- **FFmpeg**

### Workflow

1. The bot downloads the video to a temporary directory.  
2. It runs a **cropdetect** pass to determine the bounding box of the content.  
3. It applies user-selected **padding adjustments** to the crop parameters.  
4. It re-encodes the video using **libx264** (`fast` preset) while copying the audio stream to preserve quality.  
5. The processed file is uploaded back to the user, and temporary files are cleaned up.

---

# Dependencies

- **aiogram** — Telegram Bot framework  
- **aiohttp** — Asynchronous HTTP server and client  
- **FFmpeg** — Video processing and analysis tool  
