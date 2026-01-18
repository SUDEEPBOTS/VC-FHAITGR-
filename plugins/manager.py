import sys
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import add_session
from utils import sm
from config import OWNER_ID

@Client.on_callback_query(filters.regex("sess_add_help"))
async def add_help(client, query):
    await query.message.edit_text(
        f"**{sm('add new session')}**\n\n"
        f"{sm('send your pyrogram string session like this:')}\n"
        f"`/addsession 1bvts...`\n\n"
        f"{sm('after adding, click restart bot.')}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("back"), callback_data="mod_manager")]])
    )

@Client.on_message(filters.command("addsession") & filters.user(OWNER_ID))
async def add_session_logic(client, message):
    if len(message.command) < 2:
        return await message.reply(sm("error: provide string session."))
        
    session = message.text.split(None, 1)[1]
    
    # using message id as unique key for simplicity or just pushing to list
    # in a real case, you should extract user_id from the session string
    # but here we just store it blindly to load later.
    await add_session(message.id, session)
    
    await message.reply(sm("session added! restart bot to load it."))

@Client.on_callback_query(filters.regex("sess_restart"))
async def restart_bot(client, query):
    await query.message.edit_text(sm("restarting system..."))
    os.execl(sys.executable, sys.executable, *sys.argv)
  
