import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from gtts import gTTS

from shared import userbots, pytgcalls_clients
from config import OWNER_ID

def sm(x):
    return str(x)

silent_file = "silent.mp3"
tts_file = "tts_audio.mp3"
user_file = "user_audio.mp3"

user_state = {}
stop_loop_flag = False

def get_duration(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return float(result.stdout)
    except:
        return 10.0  # ✅ fallback (heroku me ffprobe missing ho sakta)

async def switch_to_silent(chat_id):
    for _, vc in pytgcalls_clients.items():
        try:
            await vc.change_stream(chat_id, AudioPiped(silent_file))
        except:
            pass

@Client.on_callback_query(filters.regex("^mod_vc$") & filters.user(OWNER_ID))
async def vc_menu_handler(client, query):
    await query.answer()
    await query.message.edit_text(
        f"**{sm('VC MODULE')}**\n{sm('control voice chats:')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("join & loop silent"), callback_data="vc_join_ask")],
            [InlineKeyboardButton(sm("play tts"), callback_data="vc_tts_ask")],
            [InlineKeyboardButton(sm("play audio file"), callback_data="vc_file_ask")],
            [InlineKeyboardButton(sm("leave vc"), callback_data="vc_leave_ask")],
            [InlineKeyboardButton(sm("back"), callback_data="home")]
        ])
    )

@Client.on_callback_query(filters.regex("^vc_join_ask$") & filters.user(OWNER_ID))
async def vc_join_btn(client, query):
    await query.answer()
    chat_id = query.message.chat.id
    await query.message.edit_text(sm("connecting to vc..."))

    count = 0
    for ub in userbots:
        try:
            if ub.me.id not in pytgcalls_clients:
                vc = PyTgCalls(ub)
                await vc.start()
                pytgcalls_clients[ub.me.id] = vc

            vc = pytgcalls_clients[ub.me.id]
            await vc.join_group_call(chat_id, AudioPiped(silent_file))
            count += 1
        except Exception as e:
            print("VC JOIN ERROR:", e)

    await query.message.edit_text(
        sm(f"connected {count} bots to vc. looping silent file."),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("back"), callback_data="mod_vc")]
        ])
    )

@Client.on_callback_query(filters.regex("^vc_tts_ask$") & filters.user(OWNER_ID))
async def enable_tts_mode(client, query):
    await query.answer()
    user_state[query.from_user.id] = "tts_mode"
    await query.message.edit_text(
        f"**{sm('TTS MODE')}**\n{sm('type anything to speak.')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]
        ])
    )

@Client.on_callback_query(filters.regex("^vc_file_ask$") & filters.user(OWNER_ID))
async def ask_for_file(client, query):
    await query.answer()
    user_state[query.from_user.id] = "waiting_file"
    await query.message.edit_text(
        f"**{sm('FILE PLAY MODE')}**\n\n{sm('send the audio/voice/mp3 file you want to play.')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]
        ])
    )

# ✅ ACCEPT: audio + voice + document
@Client.on_message((filters.audio | filters.voice | filters.document) & filters.user(OWNER_ID))
async def handle_audio_input(client, message):
    user_id = message.from_user.id

    if user_state.get(user_id) != "waiting_file":
        return

    status = await message.reply_text("⬇️ Downloading file...")

    try:
        file_path = await message.download(file_name=user_file)
    except Exception as e:
        return await status.edit_text(f"❌ Download failed: {e}")

    user_state[user_id] = "waiting_loop_count"

    await status.edit_text(
        f"✅ File received!\n\n📂 Saved as: `{file_path}`\n\n🔁 Send loop count number (example: 5)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("CANCEL", callback_data="cancel_action")]
        ])
    )

@Client.on_message(filters.text & filters.user(OWNER_ID))
async def handle_text_input(client, message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    chat_id = message.chat.id

    global stop_loop_flag

    # ✅ TTS Handler
    if state == "tts_mode":
        text = message.text
        status = await message.reply_text(sm(f"speaking: {text}"))

        # ✅ Better voice (less robot)
        tts = gTTS(text=text, lang="en", tld="co.in", slow=False)
        tts.save(tts_file)

        for _, vc in pytgcalls_clients.items():
            try:
                await vc.change_stream(chat_id, AudioPiped(tts_file))
            except:
                pass

        await asyncio.sleep((len(text.split()) / 2.5) + 2)
        await switch_to_silent(chat_id)
        await status.edit_text(sm("✅ done."))
        return

    # ✅ Loop Count Handler
    if state == "waiting_loop_count":
        try:
            loop_count = int(message.text.strip())
        except:
            return await message.reply_text("❌ Send only number like: 3")

        stop_loop_flag = False
        user_state[user_id] = None

        status = await message.reply_text(
            f"▶️ Playing audio {loop_count} times...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ STOP PLAYBACK", callback_data="stop_loop")]
            ])
        )

        duration = get_duration(user_file)

        for i in range(loop_count):
            if stop_loop_flag:
                await status.edit_text("🛑 Playback stopped.")
                break

            for _, vc in pytgcalls_clients.items():
                try:
                    await vc.change_stream(chat_id, AudioPiped(user_file))
                except:
                    pass

            await status.edit_text(f"🔁 Playing loop: {i+1}/{loop_count}")
            await asyncio.sleep(duration)

        await switch_to_silent(chat_id)
        if not stop_loop_flag:
            await status.edit_text("✅ Playback finished. Silent loop resumed.")

@Client.on_callback_query(filters.regex("^cancel_action$") & filters.user(OWNER_ID))
async def cancel_handler(client, query):
    await query.answer()
    user_state[query.from_user.id] = None
    await query.message.edit_text(
        "✅ Cancelled.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("BACK", callback_data="mod_vc")]
        ])
    )

@Client.on_callback_query(filters.regex("^stop_loop$") & filters.user(OWNER_ID))
async def stop_loop_handler(client, query):
    await query.answer("stopping...")
    global stop_loop_flag
    stop_loop_flag = True
    await switch_to_silent(query.message.chat.id)

@Client.on_callback_query(filters.regex("^vc_leave_ask$") & filters.user(OWNER_ID))
async def leave_vc_handler(client, query):
    await query.answer()
    for _, vc in pytgcalls_clients.items():
        try:
            await vc.leave_group_call(query.message.chat.id)
        except:
            pass
    await query.message.edit_text("✅ Disconnected all bots.")