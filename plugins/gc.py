import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import userbots
from utils import sm
from config import OWNER_ID

# --- help handlers (button clicks) ---
@Client.on_callback_query(filters.regex("gc_join_help"))
async def gc_join_help(client, query):
    await query.message.edit_text(
        f"**{sm('how to join groups')}**\n\n"
        f"{sm('use this command to join all bots:')}\n"
        f"`/joinall https://t.me/your_link`\n\n"
        f"{sm('supports both private and public links.')}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("back"), callback_data="mod_gc")]])
    )

# --- logic: join all ---
@Client.on_message(filters.command("joinall") & filters.user(OWNER_ID))
async def join_logic(client, message):
    if len(message.command) < 2:
        return await message.reply(sm("usage: /joinall [link]"))
        
    link = message.command[1]
    status = await message.reply(sm(f"joining {len(userbots)} accounts..."))
    
    count = 0
    for ub in userbots:
        try:
            await ub.join_chat(link)
            count += 1
            await asyncio.sleep(1) # delay
        except Exception as e:
            print(f"join failed: {e}")
            
    await status.edit(f"✅ **{sm(f'completed. joined {count} chats.')}**")

# --- logic: leave current ---
@Client.on_callback_query(filters.regex("gc_leave_curr"))
async def leave_logic_btn(client, query):
    chat_id = query.message.chat.id
    await query.message.edit_text(sm("leaving this chat..."))
    
    count = 0
    for ub in userbots:
        try:
            await ub.leave_chat(chat_id)
            count += 1
        except:
            pass
            
    await query.message.edit_text(f"✅ **{sm(f'removed {count} bots from here.')}**")
  
