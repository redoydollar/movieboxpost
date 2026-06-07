import os
import asyncio
import threading
import logging
from flask import Flask, render_template, request, jsonify
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from database import db
from utils import is_adult

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def get_ad_url(key, default):
    val = db.get_setting(key, default)
    return val if val else default

# Pyrogram Bot Instance
bot = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============= AUTO DELETE FUNCTION =============
async def delete_message_after_delay(client, chat_id, message_id, delay):
    """নির্দিষ্ট সময় পর মেসেজ অটো ডিলিট করবে"""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception as e:
        print(f"Delete Error: {e}")

# ============= TELEGRAM BOT HANDLERS =============

@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username or "")
    
    # ভেরিফাই করে ফিরে আসলে ফাইল পাঠানো
    if len(message.command) > 1 and message.command[1].startswith("sendfile_"):
        token = message.command[1].split("_")[1]
        record = db.get_verified_token(token)
        if record:
            try:
                msg = await client.send_document(
                    record['user_id'], record['file_id'], 
                    caption=f"**🎬 {record['file_name']}**\n\n⏳ এই ফাইলটি ৩০ মিনিট পর অটো ডিলিট হয়ে যাবে!"
                )
                # ৩০ মিনিট পর ডিলিট করার জন্য ব্যাকগ্রাউন্ডে টাস্ক শুরু
                asyncio.create_task(delete_message_after_delay(client, msg.chat.id, msg.id, AUTO_DELETE_SECONDS))
            except Exception as e:
                print(f"Send Error: {e}")
            return
            
    await message.reply_text(
        f"**স্বাগতম {message.from_user.first_name}! 🎬**\n\nআমি একটি মুভি বট। আপনার পছন্দের মুভি খুঁজতে সরাসরি মুভির নাম লিখুন।",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Search Movie", switch_inline_query_current_chat="")]])
    )

@bot.on_message(filters.private & filters.text & ~filters.command(["start", "stats", "ban", "unban", "set_ad"]))
async def search_movie(client, message):
    if db.is_banned(message.from_user.id):
        return await message.reply("❌ আপনি ব্যান করা আছেন।")

    if FSUB_CHANNELS:
        for ch in FSUB_CHANNELS:
            try:
                member = await client.get_chat_member(ch, message.from_user.id)
                if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                    return await message.reply("**❌ প্রথমে চ্যানেলে জয়েন করুন!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]))
            except: pass

    query = message.text.strip()
    results = db.search_files(query, limit=MAX_RESULTS)
    if not results:
        return await message.reply("**❌ কোনো মুভি পাওয়া যায়নি!** অন্য নামে খুঁজুন।")

    for file in results:
        is_18 = is_adult(file['file_name'])
        token = db.create_token(message.from_user.id, file['file_id'], file['file_name'], is_18)
        ad_type = "adult" if is_18 else "normal"
        verify_url = f"{BASE_URL}/verify?token={token}&type={ad_type}"

        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download File", url=verify_url)]])
        caption = f"**🎬 {file['file_name']}**\n\n📦 Size: `{file['file_size']}`\n{'⚠️ 18+ Content' if is_18 else ''}"
        await message.reply_text(caption, reply_markup=btn, quote=True)

@bot.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message):
    await message.reply(f"**📊 Bot Stats:**\n\n👥 Total Users: {db.total_users()}\n📁 Total Files: {db.total_files()}")

@bot.on_message(filters.command("set_ad") & filters.user(OWNER_ID))
async def set_ad(client, message):
    args = message.text.split()
    if len(args) < 3: return await message.reply("Usage: `/set_ad normal_ad_1 https://link.com`", quote=True)
    db.set_setting(args[1], args[2])
    await message.reply(f"✅ Ad updated for `{args[1]}`")

@bot.on_message(filters.command("ban") & filters.user(OWNER_ID))
async def ban_user(client, message):
    args = message.text.split()
    if len(args) < 2: return await message.reply("Usage: `/ban user_id`", quote=True)
    db.ban_user(int(args[1]))
    await message.reply(f"✅ User `{args[1]}` banned.")

@bot.on_message(filters.command("unban") & filters.user(OWNER_ID))
async def unban_user(client, message):
    args = message.text.split()
    if len(args) < 2: return await message.reply("Usage: `/unban user_id`", quote=True)
    db.unban_user(int(args[1]))
    await message.reply(f"✅ User `{args[1]}` unbanned.")

# অটো-ইনডেক্সিং (চ্যানেল/গ্রুপ থেকে ফাইল সেভ)
@bot.on_message(filters.chat(INDEX_CHANNELS) & (filters.document | filters.video))
async def auto_index(client, message):
    file_id = message.document.file_id if message.document else message.video.file_id
    file_unique_id = message.document.file_unique_id if message.document else message.video.file_unique_id
    file_name = message.document.file_name if message.document else (message.video.file_name or "Unknown")
    file_size = message.document.file_size if message.document else message.video.file_size
    
    if db.add_file(file_id, file_unique_id, file_name, file_size, message.caption, message.id, message.chat.id):
        print(f"✅ Auto-Indexed: {file_name}")

# ============= FLASK WEB SERVER =============

@app.route('/verify')
def verify_page():
    token = request.args.get('token')
    ad_type = request.args.get('type', 'normal')
    if not token: return "Invalid Link!", 404
    
    if ad_type == "adult":
        ad1 = get_ad_url("adult_ad_1", ADULT_AD_1)
        ad2 = get_ad_url("adult_ad_2", ADULT_AD_2)
    else:
        ad1 = get_ad_url("normal_ad_1", NORMAL_AD_1)
        ad2 = get_ad_url("normal_ad_2", NORMAL_AD_2)

    return render_template('verify.html', token=token, ad1=ad1, ad2=ad2, bot_username=BOT_USERNAME)

@app.route('/api/verify', methods=['POST'])
def api_verify():
    data = request.json
    token = data.get('token')
    if not token: return jsonify({"status": "error", "message": "Token missing"}), 400
    
    record = db.verify_token(token)
    if record:
        return jsonify({"status": "success", "bot_username": BOT_USERNAME, "token": token})
    else:
        return jsonify({"status": "error", "message": "আপনি ১০ সেকেন্ড অ্যাড দেখেননি! আবার চেষ্টা করুন।"})

# ============= MAIN RUNNER =============

def run_bot():
    """Pyrogram বট আলাদা থ্রেডে চালানোর জন্য"""
    print("Starting Pyrogram Bot...")
    bot.run()

if __name__ == '__main__':
    # Step 1: বটকে ব্যাকগ্রাউন্ড থ্রেডে চালু করা
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Step 2: Flask ওয়েব সার্ভার মেইন থ্রেডে চালু করা (Render এর জন্য)
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask Server on port {port}...")
    app.run(host='0.0.0.0', port=port)
