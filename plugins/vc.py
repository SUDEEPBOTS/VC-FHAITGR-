import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from gtts import gTTS
from main import userbots, pytgcalls_clients
from config import OWNER_ID
from utils import sm

silent_file = "silent.mp3"
tts_file = "tts_audio.mp3"

# --- State Management ---
# jin users ka id is list me hoga, unka text tts banega
tts_listening = []

# --- Helper: Switch to Silent ---
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

# --- 1. Join VC Button Handler ---
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
            await vc.join_group_call(
                chat_id,
                AudioPiped(silent_file)
            )
            count += 1
        except Exception as e:
            print(f"vc error: {e}")
            
    # wapas dashboard button
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(sm("back"), callback_data="mod_vc")]])
    await query.message.edit_text(
        sm(f"connected {count} bots to vc. looping silent file."),
        reply_markup=back_btn
    )

# --- 2. TTS Button Handler (Enable Mode) ---
@Client.on_callback_query(filters.regex("vc_tts_ask"))
async def enable_tts_mode(client, query):
    user_id = query.from_user.id
    
    # user ko list me add karo
    if user_id not in tts_listening:
        tts_listening.append(user_id)
        
    # cancel button show karo
    cancel_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton(sm("❌ cancel tts mode"), callback_data="vc_tts_cancel")]
    ])
    
    await query.message.edit_text(
        f"**{sm('🎙️ tts mode activated')}**\n\n"
        f"{sm('type anything in this chat, and the bots will speak it in vc.')}\n"
        f"{sm('click cancel below to stop.')}",
        reply_markup=cancel_btn
    )

# --- 3. Cancel TTS Handler (Disable Mode) ---
@Client.on_callback_query(filters.regex("vc_tts_cancel"))
async def disable_tts_mode(client, query):
    user_id = query.from_user.id
    
    if user_id in tts_listening:
        tts_listening.remove(user_id)
        
    # wapas vc menu pe le jao
    vc_menu = InlineKeyboardMarkup([
        [InlineKeyboardButton(sm("join & loop silent"), callback_data="vc_join_ask")],
        [InlineKeyboardButton(sm("play tts"), callback_data="vc_tts_ask")],
        [InlineKeyboardButton(sm("leave vc"), callback_data="vc_leave_ask")],
        [InlineKeyboardButton(sm("back"), callback_data="home")]
    ])
    
    await query.message.edit_text(
        sm("tts mode deactivated. returned to menu."),
        reply_markup=vc_menu
    )

# --- 4. The Listener (Chat Input -> Audio) ---
@Client.on_message(filters.text & filters.user(OWNER_ID) & ~filters.command(["start", "help"]))
async def tts_listener(client, message):
    # check agar user tts mode me hai ya nahi
    if message.from_user.id not in tts_listening:
        return # ignore message if mode is off

    text = message.text
    chat_id = message.chat.id
    
    # user ko feedback do ki process chal raha hai
    status = await message.reply(sm(f"speaking: {text}"))
    
    # audio generate
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(tts_file)
        
        # play on all bots
        for user_id, vc in pytgcalls_clients.items():
            try:
                await vc.change_stream(
                    chat_id,
                    AudioPiped(tts_file)
                )
            except:
                pass
        
        # wait logic (approximate duration)
        # formula: (word_count / 2.5) + 1 second buffer
        estimated_time = (len(text.split()) / 2.5) + 1
        await asyncio.sleep(estimated_time)
        
        # back to silent
        await switch_to_silent(chat_id)
        await status.edit(sm("✅ done."))
        
    except Exception as e:
        await status.edit(sm(f"error: {str(e)}"))

# --- 5. Leave VC Handler ---
@Client.on_callback_query(filters.regex("vc_leave_ask"))
async def vc_leave_btn(client, query):
    chat_id = query.message.chat.id
    
    for user_id, vc in pytgcalls_clients.items():
        try:
            await vc.leave_group_call(chat_id)
        except:
            pass
            
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(sm("back"), callback_data="mod_vc")]])
    await query.message.edit_text(
        sm("disconnected all bots from vc."),
        reply_markup=back_btn
    )
  
