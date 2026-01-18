import asyncio
import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from gtts import gTTS
from main import userbots, pytgcalls_clients
from config import OWNER_ID
from utils import sm

# --- constants & paths ---
silent_file = "silent.mp3"
tts_file = "tts_audio.mp3"
user_file = "user_audio.mp3"

# --- state management ---
# stores what the user is currently doing (waiting for file, waiting for loop count)
user_state = {} 
# flag to stop the loop when cancel is pressed
stop_loop_flag = False

# --- helper: get audio duration ---
def get_duration(file_path):
    """gets audio duration in seconds using ffmpeg"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return float(result.stdout)
    except:
        return 5.0 # fallback default

# --- helper: switch to silent ---
async def switch_to_silent(chat_id):
    """reverts all bots back to silent loop"""
    for user_id, vc in pytgcalls_clients.items():
        try:
            await vc.change_stream(
                chat_id,
                AudioPiped(silent_file)
            )
        except:
            pass

# ==========================================
# 1. MAIN VC MENU
# ==========================================

@Client.on_callback_query(filters.regex("mod_vc"))
async def vc_menu_handler(client, query):
    await query.message.edit_text(
        f"**{sm('vc module')}**\n{sm('control voice chats:')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(sm("join & loop silent"), callback_data="vc_join_ask")],
            [InlineKeyboardButton(sm("play tts"), callback_data="vc_tts_ask")],
            [InlineKeyboardButton(sm("play audio file"), callback_data="vc_file_ask")], # <-- New Button
            [InlineKeyboardButton(sm("leave vc"), callback_data="vc_leave_ask")],
            [InlineKeyboardButton(sm("back"), callback_data="home")]
        ])
    )

# ==========================================
# 2. JOIN VC LOGIC
# ==========================================
@Client.on_callback_query(filters.regex("vc_join_ask"))
async def vc_join_btn(client, query):
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
        except:
            pass
            
    await query.message.edit_text(
        sm(f"connected {count} bots to vc. looping silent file."),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("back"), callback_data="mod_vc")]])
    )

# ==========================================
# 3. TTS LOGIC
# ==========================================
@Client.on_callback_query(filters.regex("vc_tts_ask"))
async def enable_tts_mode(client, query):
    user_state[query.from_user.id] = "tts_mode"
    await query.message.edit_text(
        f"**{sm('🎙️ tts mode')}**\n{sm('type anything to speak.')}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]])
    )

# ==========================================
# 4. FILE PLAY LOGIC (NEW FEATURE) 🎵
# ==========================================

# Step 1: Ask for File
@Client.on_callback_query(filters.regex("vc_file_ask"))
async def ask_for_file(client, query):
    user_state[query.from_user.id] = "waiting_file"
    await query.message.edit_text(
        f"**{sm('🎵 file play mode')}**\n\n"
        f"{sm('please send the audio file you want to play.')}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]])
    )

# Step 2: Handle Audio File & Ask for Loop Count
@Client.on_message(filters.audio & filters.user(OWNER_ID))
async def handle_audio_input(client, message):
    user_id = message.from_user.id
    if user_state.get(user_id) == "waiting_file":
        
        status = await message.reply(sm("downloading file..."))
        
        # Download file
        await message.download(user_file)
        
        # Update state
        user_state[user_id] = "waiting_loop_count"
        
        await status.edit(
            f"**{sm('file received!')}**\n"
            f"{sm('how many times to loop? (send number)')}\n"
            f"{sm('example: 5')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("cancel"), callback_data="cancel_action")]])
        )

# Step 3: Handle Loop Count & Start Playing
@Client.on_message(filters.text & filters.user(OWNER_ID))
async def handle_text_input(client, message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    chat_id = message.chat.id
    global stop_loop_flag

    # --- TTS Handler ---
    if state == "tts_mode":
        text = message.text
        status = await message.reply(sm(f"speaking: {text}"))
        tts = gTTS(text=text, lang='en')
        tts.save(tts_file)
        
        for uid, vc in pytgcalls_clients.items():
            try: await vc.change_stream(chat_id, AudioPiped(tts_file))
            except: pass
        
        await asyncio.sleep((len(text.split())/2.5) + 1)
        await switch_to_silent(chat_id)
        await status.edit(sm("✅ done."))
        return

    # --- Loop Count Handler ---
    if state == "waiting_loop_count":
        try:
            loop_count = int(message.text)
        except:
            return await message.reply(sm("please send a valid number."))

        stop_loop_flag = False # reset flag
        user_state[user_id] = None # clear state
        
        status = await message.reply(
            f"**{sm(f'playing audio {loop_count} times...')}**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("❌ stop playback"), callback_data="stop_loop")]])
        )
        
        # Calculate Duration
        duration = get_duration(user_file)
        
        # Start Loop
        for i in range(loop_count):
            if stop_loop_flag:
                await status.edit(sm("🛑 playback stopped by user."))
                break
            
            # Play on all bots
            for uid, vc in pytgcalls_clients.items():
                try: await vc.change_stream(chat_id, AudioPiped(user_file))
                except: pass
            
            await status.edit(sm(f"playing loop: {i+1}/{loop_count}"))
            
            # Wait for song to finish
            await asyncio.sleep(duration)
        
        # Revert to Silent when done
        await switch_to_silent(chat_id)
        if not stop_loop_flag:
            await status.edit(sm("✅ playback finished. reverted to silent."))

# ==========================================
# 5. CANCEL & STOP HANDLERS
# ==========================================

@Client.on_callback_query(filters.regex("cancel_action"))
async def cancel_handler(client, query):
    user_state[query.from_user.id] = None
    await query.message.edit_text(
        sm("action cancelled."),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("back to menu"), callback_data="mod_vc")]])
    )

@Client.on_callback_query(filters.regex("stop_loop"))
async def stop_loop_handler(client, query):
    global stop_loop_flag
    stop_loop_flag = True
    # immediate switch to silent
    await switch_to_silent(query.message.chat.id)
    await query.answer(sm("stopping..."))

@Client.on_callback_query(filters.regex("vc_leave_ask"))
async def leave_vc_handler(client, query):
    for uid, vc in pytgcalls_clients.items():
        try: await vc.leave_group_call(query.message.chat.id)
        except: pass
    await query.message.edit_text(sm("disconnected all bots."))
        
