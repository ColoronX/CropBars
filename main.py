import asyncio
import os
import re
import json
import uuid
import logging
from collections import Counter

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton



# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")

FFMPEG_PATH = "ffmpeg"
PADDING = 30
WORKERS = 2

TMP = "/tmp"
SESSION_DIR = f"{TMP}/sessions"

os.makedirs(SESSION_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

task_queue = asyncio.Queue()
active_users = set()
active_lock = asyncio.Lock()


# ================= SESSION STORAGE =================

def save_session(data: dict) -> str:
    sid = str(uuid.uuid4())
    with open(f"{SESSION_DIR}/{sid}.json", "w") as f:
        json.dump(data, f)
    return sid


def load_session(sid: str):
    path = f"{SESSION_DIR}/{sid}.json"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def delete_session(sid: str):
    path = f"{SESSION_DIR}/{sid}.json"
    if os.path.exists(path):
        os.remove(path)


# ================= UI =================

def kb(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="No Text", callback_data=f"{session_id}:none")],
        [
            InlineKeyboardButton(text="Top", callback_data=f"{session_id}:top"),
            InlineKeyboardButton(text="Bottom", callback_data=f"{session_id}:bottom"),
        ],
        [InlineKeyboardButton(text="Both", callback_data=f"{session_id}:both")]
    ])


# ================= STREAM DOWNLOAD =================

async def download_stream(file_path: str, out_path: str):
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in r.content.iter_chunked(1024 * 64):
                    f.write(chunk)


# ================= FFMPEG =================

async def get_crop_params(path: str, pref: str):
    cmd = [
        FFMPEG_PATH, "-i", path,
        "-vf", "cropdetect=24:16:0",
        "-f", "null", "-"
    ]

    p = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    _, err = await p.communicate()
    out = err.decode(errors="ignore")

    crops = re.findall(r"crop=([0-9:]+)", out)
    if not crops:
        return None

    crop = Counter(crops).most_common(1)[0][0]
    w, h, x, y = map(int, crop.split(":"))

    if pref in ["top", "both"]:
        y -= min(PADDING, y)
    if pref in ["bottom", "both"]:
        h += PADDING

    return f"{w}:{h}:{x}:{y}"


async def crop_video(inp, out, crop):
    cmd = [
        FFMPEG_PATH, "-y",
        "-i", inp,
        "-vf", f"crop={crop}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "copy",
        out
    ]

    p = await asyncio.create_subprocess_exec(*cmd)
    await p.communicate()


# ================= QUEUE WORKER =================

async def worker():
    while True:
        job = await task_queue.get()
        try:
            await process_job(**job)
        except Exception as e:
            logging.error(f"Worker error: {e}")
        finally:
            task_queue.task_done()


async def start_workers():
    for _ in range(WORKERS):
        asyncio.create_task(worker())


# ================= CORE JOB =================

async def process_job(query, data, pref, uid):
    msg = query.message

    file_id = data["file_id"]
    reply_id = data["reply_to_id"]

    inp = f"{TMP}/in_{file_id}.mp4"
    out = f"{TMP}/out_{file_id}.mp4"

    try:
        await msg.edit_text("Downloading...")

        file = await bot.get_file(file_id)
        await download_stream(file.file_path, inp)

        await msg.edit_text("Analyzing...")
        crop = await get_crop_params(inp, pref)

        if not crop:
            await msg.edit_text("Crop failed")
            return

        await msg.edit_text("Encoding...")
        await crop_video(inp, out, crop)

        await msg.edit_text("Uploading...")

        await msg.answer_video(
            FSInputFile(out),
            reply_to_message_id=reply_id
        )

        await msg.delete()

    finally:
        async with active_lock:
            active_users.discard(uid)

        for f in (inp, out):
            if os.path.exists(f):
                os.remove(f)


# ================= HANDLERS =================

@dp.message(CommandStart())
async def start(m: types.Message):
    await m.answer("Send video or /crop")


@dp.message(F.video | F.document)
async def video(m: types.Message):
    if m.chat.type != "private":
        return

    v = m.video or m.document
    if not v.mime_type.startswith("video/"):
        return

    sid = save_session({
        "file_id": v.file_id,
        "reply_to_id": m.message_id
    })

    await m.reply("Position?", reply_markup=kb(sid))


@dp.message(Command("crop"))
async def crop(m: types.Message):
    if not m.reply_to_message:
        return

    v = m.reply_to_message.video or m.reply_to_message.document
    if not v:
        return

    sid = save_session({
        "file_id": v.file_id,
        "reply_to_id": m.reply_to_message.message_id
    })

    await m.reply("Position?", reply_markup=kb(sid))


@dp.callback_query()
async def cb(q: types.CallbackQuery):
    await q.answer()

    try:
        sid, pref = q.data.split(":")
    except:
        return

    data = load_session(sid)
    if not data:
        await q.message.edit_text("Expired")
        return

    uid = q.from_user.id

    async with active_lock:
        if uid in active_users:
            await q.answer("Busy", show_alert=True)
            return
        active_users.add(uid)

    delete_session(sid)

    await q.message.edit_text("Queued...")

    await task_queue.put({
        "query": q,
        "data": data,
        "pref": pref,
        "uid": uid
    })


# ================= ENTRY =================

async def health(r):
    return web.Response(text="OK")

async def main():
    await start_workers()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot started (polling)")
    
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 7860)
    await site.start()
    
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN env var")

    asyncio.run(main())
