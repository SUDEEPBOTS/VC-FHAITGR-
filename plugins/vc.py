import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from gtts import gTTS

from main import userbots, pytgcalls_clients
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
        return 5.0

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
        f"**{sm('FILE PLAY MODE')}**\n\n{sm('send the audio file you want to play.')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]
        ])
    )

@Client.on_message(filters.audio & filters.user(OWNER_ID))
async def handle_audio_input(client, message):
    user_id = message.from_user.id
    if user_state.get(user_id) == "waiting_file":
        status = await message.reply_text(sm("downloading file..."))
        await message.download(user_file)
        user_state[user_id] = "waiting_loop_count"

        await status.edit_text(
            f"**{sm('file received!')}**\n{sm('how many times to loop?')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]
            ])
        )

@Client.on_message(filters.text & filters.user(OWNER_ID))
async def handle_text_input(client, message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    chat_id = message.chat.id

    global stop_loop_flag

    if state == "tts_mode":
        text = message.text
        status = await message.reply_text(sm(f"speaking: {text}"))

        tts = gTTS(text=text, lang='en')
        tts.save(tts_file)

        for _, vc in pytgcalls_clients.items():
            try:
                await vc.change_stream(chat_id, AudioPiped(tts_file))
            except:
                pass

        await asyncio.sleep((len(text.split()) / 2.5) + 1)
        await switch_to_silent(chat_id)
        await status.edit_text(sm("✅ done."))
        return

    if state == "waiting_loop_count":
        try:
            loop_count = int(message.text)
        except:
            return await message.reply_text(sm("send a valid number."))

        stop_loop_flag = False
        user_state[user_id] = None

        status = await message.reply_text(
            sm(f"playing audio {loop_count} times..."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(sm("stop playback"), callback_data="stop_loop")]
            ])
        )

        duration = get_duration(user_file)

        for i in range(loop_count):
            if stop_loop_flag:
                await status.edit_text(sm("🛑 stopped."))
                break

            for _, vc in pytgcalls_clients.items():
                try:
                    await vc.change_stream(chat_id, AudioPiped(user_file))
                except:
                    pass

            await status.edit_text(sm(f"playing loop: {i+1}/{loop_count}"))
            await asyncio.sleep(duration)

        await switch_to_silent(chat_id)
        if not stop_loop_flag:
            await status.edit_text(sm("✅ finished. silent loop resumed."))

@Client.on_callback_query(filters.regex("^cancel_action$") & filters.user(OWNER_ID))
async def cancel_handler(client, query):
    await query.answer()
    user_state[query.from_user.id] = None
    await query.message.edit_text(
        sm("action cancelled."),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("back"), callback_data="mod_vc")]
        ])
    )

@Client.on_callback_query(filters.regex("^stop_loop$") & filters.user(OWNER_ID))
async def stop_loop_handler(client, query):
    await query.answer(sm("stopping..."))
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
    await query.message.edit_text(sm("disconnected all bots."))