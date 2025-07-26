# Discord Bot Orchestrator Setup Guide

## 🔧 Prerequisites

1. **Python 3.8+** installed
2. **FFmpeg** installed for voice functionality
3. **Discord Bot Tokens** for each bot

## 📦 Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg:
   - **Windows**: Download from https://ffmpeg.org/download.html
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

## 🔑 Environment Setup

Create a `.env` file in the project root with your bot tokens:

```env
APP_BOT_TOKEN=your_application_bot_token_here
GIVEAWAY_BOT_TOKEN=your_giveaway_bot_token_here
INVITES_BOT_TOKEN=your_invites_bot_token_here
TICKET_BOT_TOKEN=your_ticket_bot_token_here
MUSIC_BOT_TOKEN=your_music_bot_token_here
```

## 🤖 Bot Setup

For each bot, you need to:

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create 5 separate applications (one for each bot)
3. Go to "Bot" section for each application
4. Copy the token and add it to your `.env` file
5. Enable required intents:
   - Message Content Intent
   - Server Members Intent
   - Voice States Intent (for music bot)

## 🎵 Voice Setup (Music Bot)

The music bot requires:
- **PyNaCl**: `pip install PyNaCl`
- **FFmpeg**: Must be installed and accessible in PATH
- **Voice permissions**: Bot must have "Connect" and "Speak" permissions

## 🚀 Running the Bots

```bash
python all_bots.py
```

## 🔍 Troubleshooting

### Error 4006 - Authentication Issues
- Check that all bot tokens are correct
- Ensure bots are added to your server
- Verify environment variables are loaded

### Voice Connection Issues
- Install PyNaCl: `pip install PyNaCl`
- Install FFmpeg and ensure it's in PATH
- Check bot has voice permissions in Discord

### Multiple Connection Attempts
- Each bot should have a unique token
- Don't reuse tokens across multiple bots
- Check Discord rate limits

## 📋 Bot Permissions

Each bot needs these permissions:
- **Application Bot**: Manage Channels, Send Messages
- **Giveaway Bot**: Send Messages, Manage Messages
- **Invites Bot**: Send Messages, Read Message History
- **Ticket Bot**: Manage Channels, Send Messages
- **Music Bot**: Connect, Speak, Send Messages, Use Voice Activity 