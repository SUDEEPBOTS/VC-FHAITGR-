from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from main import userbots

def sm(text: str) -> str:
    return str(text).upper()

@Client.on_message(filters.command("start") & filters.user(OWNER_ID))
async def dashboard(client, message):
    header = sm("userbot network manager")
    info = sm(f"active bots: {len(userbots)}")
    select = sm("select a module below:")

    text = (
        f"**{header}**\n\n"
        f"🤖 **{info}**\n"
        f"👇 **{select}**"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(sm("gc module"), callback_data="mod_gc"),
            InlineKeyboardButton(sm("vc module"), callback_data="mod_vc")
        ],
        [
            InlineKeyboardButton(sm("dm module"), callback_data="mod_dm"),
            InlineKeyboardButton(sm("manager"), callback_data="mod_manager")
        ]
    ])

    await message.reply_text(text, reply_markup=buttons)

# ✅ ONLY handle dashboard + manager callbacks here
@Client.on_callback_query(
    filters.user(OWNER_ID)
    & filters.regex("^(home|mod_gc|mod_dm|mod_manager|sess_add_help|sess_restart|mod_vc)$")
)
async def callback_handler(client, query):
    data = query.data
    await query.answer()

    if data == "home":
        await dashboard(client, query.message)

    elif data == "mod_gc":
        await query.message.edit_text(
            f"**{sm('gc module')}**\n{sm('select action:')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(sm("join via link"), callback_data="gc_join_help")],
                [InlineKeyboardButton(sm("leave current chat"), callback_data="gc_leave_curr")],
                [InlineKeyboardButton(sm("back"), callback_data="home")]
            ])
        )

    elif data == "mod_dm":
        await query.message.edit_text(
            f"**{sm('dm raid module')}**\n{sm('select action:')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(sm("start dm raid"), callback_data="dm_help")],
                [InlineKeyboardButton(sm("back"), callback_data="home")]
            ])
        )

    elif data == "mod_manager":
        await query.message.edit_text(
            f"**{sm('session manager')}**\n{sm('manage your userbots:')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(sm("add session"), callback_data="sess_add_help")],
                [InlineKeyboardButton(sm("restart bot"), callback_data="sess_restart")],
                [InlineKeyboardButton(sm("back"), callback_data="home")]
            ])
        )

    elif data == "sess_add_help":
        await query.message.edit_text(
            f"**{sm('add session')}**\n\n"
            f"{sm('send session string now.')}\n"
            f"{sm('format: /add <session>')}\n\n"
            f"{sm('example:')}\n"
            f"`/add 1AaBbCcDd...`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(sm("back"), callback_data="mod_manager")],
                [InlineKeyboardButton(sm("home"), callback_data="home")]
            ])
        )

    elif data == "sess_restart":
        await query.message.edit_text(sm("restart feature disabled on heroku"))

    # ✅ IMPORTANT: VC ka control vc.py ko de do
    elif data == "mod_vc":
        return