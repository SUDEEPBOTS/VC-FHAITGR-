import asyncio
from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN
from database.mongo import get_all_sessions
from shared import userbots, pytgcalls_clients

async def start_network():
    print("--- starting network ---")

    bot = Client(
        "ControllerBot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        plugins=dict(root="plugins")
    )

    await bot.start()
    print("✅ Controller bot started")

    session_strings = await get_all_sessions()

    if not session_strings:
        print("⚠️ No sessions found in database")

    for session in session_strings:
        try:
            ub = Client(
                name=f"ub_{len(userbots)}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session,
                in_memory=True
            )
            await ub.start()
            userbots.append(ub)
            print(f"✅ started userbot: {ub.me.first_name}")
        except Exception as e:
            print(f"❌ failed to load session: {e}")

    print(f"--- network ready: {len(userbots)} bots active ---")

    # ✅ YOUR PYROGRAM NEEDS AWAIT IDLE
    await idle()

    # cleanup
    await bot.stop()
    for ub in userbots:
        await ub.stop()

if __name__ == "__main__":
    asyncio.run(start_network())