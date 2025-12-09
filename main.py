import asyncio
import logging
import os
import base64
from io import BytesIO

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from openai import AsyncOpenAI

from database import add_user, get_users, ban_user, unban_user, is_user_banned
# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Bot, Dispatcher, and OpenAI client
# usage of these variables will be checked in main() to allow import without error if env is missing
bot = None
dp = Dispatcher()
client = None

@dp.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer("Asalawma aleykum Men Ai botpan hamde sizge jardem bere alaman photo yaki galasavoy taslan men oni analy etip islep beremen.Bul bot Qoylibaev JAsur tarepinen islendi")

@dp.message(F.photo)
async def handle_photo(message: Message):
    processing_msg = await message.answer("Analyzing image...")
    
    try:
        # Get the highest resolution photo
        photo = message.photo[-1]
        
        # Download the photo
        # bot.download returns a BytesIO object if destination is not specified
        photo_file = await bot.download(photo)
        
        # Encode to base64
        base64_image = base64.b64encode(photo_file.read()).decode('utf-8')
        
        # Get caption if any
        caption = message.caption or "Solve this or describe this image."
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": caption},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
        )
        
        answer = response.choices[0].message.content
        await message.answer(answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Error handling photo: {e}")
        await message.answer("Sorry, I encountered an error checking that image.")
    finally:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass

@dp.message(F.text)
async def handle_text(message: Message):
    # Indicate typing status
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": message.text}
            ],
        )
        answer = response.choices[0].message.content
        await message.answer(answer, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error handling text: {e}")
        await message.answer("Sorry, something went wrong.")

async def main():
    global bot, client
    
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
        return
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in .env file")
        return

    bot = Bot(token=BOT_TOKEN)
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    print("Bot is starting...")
    await dp.start_polling(bot)

# Admin utilities
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

async def admin_check(message: Message) -> bool:
    """Add user to DB, check ban status, and enforce admin restrictions."""
    user = message.from_user
    add_user(user.id, user.username, f"{user.full_name}")
    if is_user_banned(user.id):
        await message.answer("You are banned from using this bot.")
        return False
    return True

@dp.message(F.text)
async def handle_text(message: Message):
    if not await admin_check(message):
        return
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message.text}],
        )
        answer = response.choices[0].message.content
        await message.answer(answer, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error handling text: {e}")
        await message.answer("Sorry, something went wrong.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    if not await admin_check(message):
        return
    processing_msg = await message.answer("Analyzing image...")
    try:
        photo = message.photo[-1]
        photo_file = await bot.download(photo)
        base64_image = base64.b64encode(photo_file.read()).decode('utf-8')
        caption = message.caption or "Solve this or describe this image."
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            }],
        )
        answer = response.choices[0].message.content
        await message.answer(answer, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error handling photo: {e}")
        await message.answer("Sorry, I encountered an error checking that image.")
    finally:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass

# Admin command handlers
@dp.message(F.command("users"))
async def admin_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Unauthorized.")
        return
    users = get_users()
    if not users:
        await message.answer("No users recorded.")
        return
    lines = []
    for uid, username, full_name, joined, last, banned in users:
        lines.append(f"ID: {uid}, Username: {username or 'N/A'}, Name: {full_name or 'N/A'}, Banned: {banned}")
    text = "\n".join(lines)
    await message.answer(text if len(text) < 4000 else "Too many users, check the DB file.")

@dp.message(F.command("ban"))
async def admin_ban(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Unauthorized.")
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /ban <user_id>")
        return
    uid = int(parts[1])
    ban_user(uid)
    await message.answer(f"User {uid} has been banned.")

@dp.message(F.command("unban"))
async def admin_unban(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Unauthorized.")
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /unban <user_id>")
        return
    uid = int(parts[1])
    unban_user(uid)
    await message.answer(f"User {uid} has been unbanned.")

if __name__ == "__main__":
    asyncio.run(main())
