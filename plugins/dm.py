import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import userbots
from utils import sm
from config import OWNER_ID

@Client.on_callback_query(filters.regex("dm_help"))
async def dm_help_msg(client, query):
    await query.message.edit_text(
        f"**{sm('how to dm raid')}**\n\n"
        f"{sm('use the command below:')}\n"
        f"`/dmraid @username your message here`\n\n"
        f"{sm('example:')}\n`/dmraid @sudeep hello brother`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(sm("back"), callback_data="mod_dm")]])
    )

@Client.on_message(filters.command("dmraid") & filters.user(OWNER_ID))
async def dm_raid_logic(client, message):
    if len(message.command) < 3:
        return await message.reply(sm("usage: /dmraid @username [message]"))
        
    target = message.command[1]
    text = message.text.split(None, 2)[2]
    
    status = await message.reply(sm(f"starting dm raid on {target}..."))
    
    count = 0
    for ub in userbots:
        try:
            await ub.send_message(target, text)
            count += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"dm fail: {e}")
            
    await status.edit(f"✅ **{sm(f'raid finished. sent {count} messages.')}**")
  
