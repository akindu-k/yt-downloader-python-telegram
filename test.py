import os
import logging
import tempfile
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token (replace with your actual token from BotFather)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Directory for temporary downloads
TEMP_DOWNLOAD_DIR = tempfile.gettempdir()

# Help message
HELP_MESSAGE = """
🎬 *YouTube Downloader Bot* 🎬

Send me a YouTube link, and I'll download the video for you!

*Commands:*
/start - Start the bot
/help - Show this help message

*How to use:*
1. Simply send a YouTube link
2. Choose the quality you want to download
3. Wait for the download to complete

*Supported links:*
- YouTube videos 
- YouTube Shorts

Developed with ❤️ by Akindu Kalhan
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        f"Welcome to YouTube Downloader Bot. Send me a YouTube link and I'll download the video for you."
    )
    await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")

def is_youtube_url(url: str) -> bool:
    """Check if the URL is a YouTube URL."""
    return "youtube.com" in url or "youtu.be" in url

def get_video_info(url: str) -> Optional[dict]:
    """Get information about a YouTube video."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except DownloadError as e:
        logger.error(f"Error extracting video info: {e}")
        return None

async def process_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a YouTube URL sent by the user."""
    url = update.message.text
    
    # Send a "processing" message
    message = await update.message.reply_text("🔎 Processing YouTube link...")
    
    # Get video info
    info = get_video_info(url)
    if not info:
        await message.edit_text("❌ Sorry, I couldn't process this YouTube link. Please make sure it's valid.")
        return
    
    # Store URL in user data for later use
    context.user_data['youtube_url'] = url
    context.user_data['video_title'] = info.get('title', 'Unknown Title')
    
    # Create quality selection buttons
    keyboard = [
        [InlineKeyboardButton("🎥 Video (High Quality)", callback_data="video_high")],
        [InlineKeyboardButton("🎥 Video (Medium Quality)", callback_data="video_medium")],
        [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="audio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the processing message with the info and buttons
    await message.edit_text(
        f"📽️ *{info.get('title', 'Unknown Title')}*\n\n"
        f"▶️ Duration: {format_duration(info.get('duration', 0))}\n"
        f"👁️ Views: {format_number(info.get('view_count', 0))}\n\n"
        "Please select download format:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def format_duration(seconds: int) -> str:
    """Format duration in seconds to mm:ss or hh:mm:ss."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_number(num: int) -> str:
    """Format numbers with comma separators."""
    return f"{num:,}"

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks for download quality selection."""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    url = context.user_data.get('youtube_url')
    title = context.user_data.get('video_title', 'video')
    
    if not url:
        await query.edit_message_text("❌ Session expired. Please send the YouTube link again.")
        return
    
    # Update message to show download has started
    await query.edit_message_text(f"⏱️ Starting download for: {title}...")
    
    # Set download options based on user choice
    if choice == "video_high":
        file_path = await download_video(url, "high", update, context)
    elif choice == "video_medium":
        file_path = await download_video(url, "medium", update, context)
    elif choice == "audio":
        file_path = await download_audio(url, update, context)
    else:
        await query.edit_message_text("❌ Invalid option selected.")
        return
    
    if not file_path:
        await query.edit_message_text("❌ Download failed. Please try again later.")
        return

async def download_video(url: str, quality: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    """Download a YouTube video and send it to the user."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    # Set format based on quality - with fallback options
    if quality == "high":
        # Try progressively lower quality options if high quality fails
        format_options = [
            'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best',
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best'
        ]
        quality_text = "high quality"
    else:  # medium
        format_options = [
            'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best',
            'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]/best[ext=mp4]/best'
        ]
        quality_text = "medium quality"
    
    # Create a temporary filename
    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"tg_ytdl_{chat_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    success = False
    file_path = None
    
    # Try each format option until one works
    for format_option in format_options:
        if success:
            break
            
        # Download options
        ydl_opts = {
            'format': format_option,
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: download_progress_hook(d, update, context)],
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'noplaylist': True,
        }
        
        try:
            # Update status message
            await query.edit_message_text(f"⬇️ Downloading {quality_text} video...")
            
            # Download the video
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # If the file extension changed during download
                if not os.path.exists(file_path):
                    base_path = os.path.splitext(file_path)[0]
                    for ext in ['mp4', 'mkv', 'webm']:
                        possible_path = base_path + f".{ext}"
                        if os.path.exists(possible_path):
                            file_path = possible_path
                            break
                
                # Check if file exists
                if os.path.exists(file_path):
                    success = True
                    break
                
        except Exception as e:
            logger.error(f"Error with format {format_option}: {e}")
            # Continue to the next format option
            continue
    
    # If all format options failed
    if not success or not file_path or not os.path.exists(file_path):
        # Try a last resort format
        ydl_opts = {
            'format': 'best/bestvideo+bestaudio',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: download_progress_hook(d, update, context)],
        }
        
        try:
            await query.edit_message_text(f"⬇️ Trying alternative download method...")
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # If the file extension changed during download
                if not os.path.exists(file_path):
                    base_path = os.path.splitext(file_path)[0]
                    for ext in ['mp4', 'mkv', 'webm']:
                        possible_path = base_path + f".{ext}"
                        if os.path.exists(possible_path):
                            file_path = possible_path
                            break
                
                if os.path.exists(file_path):
                    success = True
                
        except Exception as e:
            logger.error(f"Error with last resort format: {e}")
            await query.edit_message_text("❌ Download failed. The video might be unavailable or restricted.")
            return None
    
    # If we still don't have a file
    if not success or not file_path or not os.path.exists(file_path):
        await query.edit_message_text("❌ Download failed. File not found after multiple attempts.")
        return None
    
    # Check file size
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 50:
        await query.edit_message_text(
            f"⚠️ The video is too large ({file_size_mb:.1f} MB) to send via Telegram (limit: 50 MB).\n"
            f"Please try a lower quality option."
        )
        try:
            os.remove(file_path)
        except:
            pass
        return None
    
    # Send the video file
    await query.edit_message_text(f"📤 Uploading {quality_text} video to Telegram...")
    
    try:
        with open(file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=f"🎬 {info.get('title', 'YouTube Video')}",
                supports_streaming=True,
            )
        
        await query.edit_message_text(f"✅ Video downloaded and sent successfully!")
        
        # Clean up
        try:
            os.remove(file_path)
        except:
            pass
        return file_path
    
    except Exception as e:
        logger.error(f"Error sending video: {e}")
        await query.edit_message_text(f"❌ Failed to send the video: {str(e)}")
        try:
            os.remove(file_path)
        except:
            pass
        return None

async def download_audio(url: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    """Download a YouTube video as audio and send it to the user."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    # Create a temporary filename
    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"tg_ytdl_{chat_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Download options - with fallback
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [lambda d: download_progress_hook(d, update, context)],
        'noplaylist': True,
    }
    
    try:
        # Update status message
        await query.edit_message_text("⬇️ Downloading audio...")
        
        # Download the audio
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = os.path.splitext(ydl.prepare_filename(info))[0] + '.mp3'
            
            # Check if file exists
            if not os.path.exists(file_path):
                # Try alternative path
                base_path = os.path.splitext(ydl.prepare_filename(info))[0]
                for ext in ['mp3', 'm4a', 'ogg', 'opus']:
                    possible_path = base_path + f".{ext}"
                    if os.path.exists(possible_path):
                        file_path = possible_path
                        break
            
            if not os.path.exists(file_path):
                await query.edit_message_text("❌ Audio download failed. File not found.")
                return None
            
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 50:
                await query.edit_message_text(
                    f"⚠️ The audio is too large ({file_size_mb:.1f} MB) to send via Telegram (limit: 50 MB)."
                )
                os.remove(file_path)
                return None
            
            # Send the audio file
            await query.edit_message_text("📤 Uploading audio to Telegram...")
            
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=info.get('title', 'YouTube Audio'),
                    performer=info.get('uploader', 'Unknown Artist'),
                )
            
            await query.edit_message_text("✅ Audio downloaded and sent successfully!")
            
            # Clean up
            try:
                os.remove(file_path)
            except:
                pass
            return file_path
            
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        await query.edit_message_text(f"❌ Audio download failed: {str(e)}")
        return None

def download_progress_hook(d: dict, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hook to track download progress."""
    if d['status'] == 'downloading':
        try:
            percent = d.get('_percent_str', '0%').strip()
            if percent and update.callback_query and int(float(percent.replace('%', ''))) % 10 == 0:
                # Update progress every 10% to avoid flooding
                context.application.create_task(
                    update.callback_query.edit_message_text(
                        f"⬇️ Downloading: {percent} complete...\n"
                        f"Speed: {d.get('_speed_str', 'N/A')}\n"
                        f"ETA: {d.get('_eta_str', 'N/A')}"
                    )
                )
        except Exception as e:
            logger.error(f"Error in progress hook: {e}")

async def handle_regular_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages that are not commands or YouTube URLs."""
    await update.message.reply_text(
        "Please send me a YouTube link or use /help to see available commands."
    )

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Handle YouTube URLs
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r"(youtube\.com|youtu\.be)"), 
            process_youtube_url
        )
    )
    
    # Handle other messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_regular_message))
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()