import asyncio
import os
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioQuality

from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING_2

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING_2)
call = PyTgCalls(assistant)

queues = {}


def download_audio(query: str) -> str:
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if query.startswith("http"):
            info = ydl.extract_info(query, download=True)
        else:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            info = info["entries"][0]
        return f"downloads/{info['id']}.mp3"


async def play_next(chat_id: int):
    if chat_id not in queues or not queues[chat_id]:
        try:
            await call.leave_group_call(chat_id)
        except Exception:
            pass
        return
    file_path = queues[chat_id].pop(0)
    try:
        await call.join_group_call(chat_id, AudioPiped(file_path, AudioQuality.HIGH))
    except Exception as e:
        print(f"Error: {e}")
        await play_next(chat_id)


@bot.on_message(filters.command("start") & filters.group)
async def start_cmd(_, message: Message):
    await message.reply(
        "🎵 **ربات موزیک فعاله!**\n\n"
        "• `/play اسم آهنگ`\n"
        "• `/skip` - بعدی\n"
        "• `/stop` - توقف\n"
        "• `/queue` - صف"
    )


@bot.on_message(filters.command("play") & filters.group)
async def play_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ مثال: `/play despacito`")
    query = " ".join(message.command[1:])
    msg = await message.reply("🔍 در حال دانلود...")
    try:
        file_path = await asyncio.to_thread(download_audio, query)
    except Exception as e:
        return await msg.edit(f"❌ خطا:\n`{e}`")
    chat_id = message.chat.id
    queues.setdefault(chat_id, [])
    if not queues[chat_id]:
        queues[chat_id].append(file_path)
        try:
            await call.join_group_call(chat_id, AudioPiped(file_path, AudioQuality.HIGH))
            queues[chat_id].pop(0)
            await msg.edit("▶️ در حال پخش")
        except Exception as e:
            await msg.edit(f"❌ خطا:\n`{e}`")
    else:
        queues[chat_id].append(file_path)
        await msg.edit(f"✅ صف: {len(queues[chat_id])}")


@bot.on_message(filters.command("skip") & filters.group)
async def skip_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call.leave_group_call(chat_id)
        await message.reply("⏭")
        await asyncio.sleep(1)
        await play_next(chat_id)
    except Exception:
        await message.reply("❌ چیزی پخش نمی‌شه")


@bot.on_message(filters.command("stop") & filters.group)
async def stop_cmd(_, message: Message):
    chat_id = message.chat.id
    queues[chat_id] = []
    try:
        await call.leave_group_call(chat_id)
        await message.reply("⏹")
    except Exception:
        await message.reply("❌")


@call.on_stream_end()
async def on_end(_, update):
    await asyncio.sleep(1)
    await play_next(update.chat_id)


async def main():
    await bot.start()
    await assistant.start()
    await call.start()
    print("✅ ربات آماده‌ست!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
