# YouTube Downloader Telegram Bot

A Telegram bot that allows users to download YouTube videos and audio directly from YouTube links.

## Features

- Download YouTube videos in high or medium quality
- Extract audio from YouTube videos as MP3
- Simple and user-friendly interface
- Progress tracking during downloads
- File size checking to comply with Telegram's limits (50MB)
- Support for YouTube videos and Shorts

## Requirements

- Python 3.7+
- python-telegram-bot
- yt-dlp
- python-dotenv
- FFmpeg (for audio extraction)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/akindu-k/yt-downloader-python-telegram.git
cd yt-downloader-python-telegram
```

2. Install the required dependencies:
```bash
pip install python-telegram-bot yt-dlp python-dotenv
```

3. Install FFmpeg (required for audio extraction):
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Windows:**
   Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH

4. Create a `.env` file in the project root directory:
```
BOT_TOKEN=your_bot_token_here
```

## Getting a Bot Token

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot`
3. Follow the instructions to create a new bot
4. Copy the token provided by BotFather and add it to your `.env` file

## Running the Bot

Run the bot with the following command:
```bash
python main.py
```

## Usage

1. Start a chat with your bot on Telegram
2. Send a `/start` command to begin
3. Send a YouTube link (video or shorts)
4. Select your preferred download format:
   - High quality video
   - Medium quality video
   - Audio only (MP3)
5. Wait for the download to complete
6. The bot will send you the downloaded file

## Bot Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show help information

## Limitations

- Maximum file size is 50MB (Telegram API limitation)
- For larger videos, the bot will suggest trying a lower quality
- Some videos may be restricted and cannot be downloaded

## License

[MIT License](LICENSE)

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
