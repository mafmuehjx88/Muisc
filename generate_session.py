"""
Helper script to generate Pyrogram String Session for the Telegram Music Bot Assistant.
Run this in terminal: python generate_session.py
"""

import asyncio
from pyrogram import Client

API_ID = 38953431
API_HASH = "2ba6fc60c837d5dfa52352304831a7c1"

async def main():
    print("\n" + "=" * 50)
    print(" Telegram Music Bot - String Session Generator")
    print("=" * 50 + "\n")
    print("Please follow the Telegram login prompts.\n")
    
    async with Client(
        name="session_generator",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    ) as app:
        session_str = await app.export_session_string()
        print("\n" + "=" * 50)
        print("YOUR PYROGRAM STRING SESSION (Copy this):")
        print("=" * 50)
        print(f"\n{session_str}\n")
        print("=" * 50)
        print("Set this as STRING_SESSION environment variable or in config.py!\n")

if __name__ == "__main__":
    asyncio.run(main())
