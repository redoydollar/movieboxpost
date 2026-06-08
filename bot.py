import os
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
from database import save_thumbnail, get_thumbnail, delete_thumbnail
from keep_alive import keep_alive
from PIL import Image

# Render স্লিপ হওয়া ঠেকানো
keep_alive()

# Pyrogram ক্লায়েন্ট শুরু
app = Client("rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ইউজারের অস্থায়ী ডেটা রাখার জন্য ডিকশনারি
pending_files = {}

# --- থাম্বনেইল অপটিমাইজেশন ফাংশন (Full HD এবং শার্প রাখার জন্য) ---
def optimize_thumbnail(image_path):
    try:
        im = Image.open(image_path)
        
        # ছবিকে RGB তে কনভার্ট করা (PNG থেকে JPEG এ আনার জন্য)
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
            
        # টেলিগ্রাম ভিডিও থাম্বনেইলের জন্য সেরা সাইজ 1280x720 (16:9)
        # আসপেক্ট রেশিও ঠিক রেখে রিসাইজ করা
        im.thumbnail((1280, 720), Image.LANCZOS)
        
        # কম্প্রেস করে সেভ করা (টেলিগ্রাম 200KB এর বেশি থাম্বনেইল ব্লারি করে দেয়)
        quality = 95
        while os.path.getsize(image_path) > 200000 and quality > 20:
            im.save(image_path, "JPEG", quality=quality, optimize=True)
            quality -= 5
            
        return image_path
        
    except Exception as e:
        print(f"Thumbnail optimization error: {e}")
        return image_path

@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    await message.reply_text(
        "👋 স্বাগতম! আমি একটি হাই-স্পিড রিনেম ও ফুল এইচডি থাম্বনেইল বট।\n\n"
        "📌 **কীভাবে ব্যবহার করবেন:**\n"
        "1. আমাকে যেকোনো ভিডিও/ফাইল পাঠান।\n"
        "2. আমি নতুন নাম জিজ্ঞেস করব, আপনি নাম লিখে দিন।\n"
        "3. আমি ফাইলটি নতুন নামে আপনাকে ফেরত দেব!\n\n"
        "🖼 **থাম্বনেইল কমান্ড:**\n"
        "/setthumb - কাস্টম থাম্বনেইল সেট করতে ছবি পাঠান (ছবি অটো HD হবে)\n"
        "/delthumb - কাস্টম থাম্বনেইল মুছে ফেলুন"
    )

# থাম্বনেইল সেট করা
@app.on_message(filters.command("setthumb") & filters.private)
async def set_thumb(client, message: Message):
    await message.reply_text("🖼 অনুগ্রহ করে আপনার কাস্টম থাম্বনেইল হিসেবে যে ছবিটি ব্যবহার করতে চান, সেটি পাঠান।\n\n(ছবিটি অটোমেটিক Full HD 1280x720 তে অপটিমাইজ হবে)")

@app.on_message(filters.photo & filters.private)
async def save_thumb(client, message: Message):
    # ছবিটি ডাউনলোড করা
    file_path = await message.download(file_name="thumb_temp.jpg")
    
    # ছবিটি অপটিমাইজ (ফুল এইচডি) করা
    optimized_path = optimize_thumbnail(file_path)
    
    # অপটিমাইজ করা ছবি টেলিগ্রামে আপলোড করে file_id নেওয়া
    thumb_msg = await message.reply_document(document=optimized_path, caption="✅ এই ছবিটি অটো HD করা হয়েছে!")
    file_id = thumb_msg.document.file_id
    
    # ডেটাবেসে সেভ করা
    save_thumbnail(message.from_user.id, file_id)
    await message.reply_text("✅ কাস্টম ফুল এইচডি থাম্বনেইল সফলভাবে সেভ হয়েছে! এখন থেকে ভিডিওতে এটিই শো করবে।")
    
    # অস্থায়ী ফাইল মুছে ফেলা
    if os.path.exists(optimized_path):
        os.remove(optimized_path)

# থাম্বনেইল মুছে ফেলা
@app.on_message(filters.command("delthumb") & filters.private)
async def del_thumb(client, message: Message):
    delete_thumbnail(message.from_user.id)
    await message.reply_text("✅ কাস্টম থাম্বনেইল সফলভাবে মুছে ফেলা হয়েছে!")

# ফাইল গ্রহণ ও নতুন নাম চাওয়া
@app.on_message((filters.document | filters.video) & filters.private)
async def ask_new_name(client, message: Message):
    pending_files[message.from_user.id] = message
    
    old_name = ""
    if message.document:
        old_name = message.document.file_name
    elif message.video:
        old_name = message.video.file_name if message.video.file_name else "video.mp4"

    await message.reply_text(
        f"📁 ফাইল পাওয়া গেছে!\nআগের নাম: `{old_name}`\n\n"
        "এখন আমাকে নতুন নাম লিখে পাঠান (ফাইল এক্সটেনশন সহ, যেমন .mp4, .mkv):"
    )

# নতুন নাম গ্রহণ ও ফাইল রিনেম করা
@app.on_message(filters.text & filters.private & ~filters.command(["start", "setthumb", "delthumb"]))
async def rename_file(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in pending_files:
        await message.reply_text("❌ আমি আপনার কোনো ফাইল পাইনি। অনুগ্রহ করে আগে একটি ফাইল পাঠান।")
        return

    new_name = message.text.strip()
    original_msg = pending_files[user_id]
    
    status_msg = await message.reply_text("⏳ ফাইল ডাউনলোড হচ্ছে...")
    
    try:
        file_path = await original_msg.download(file_name=f"downloads/{new_name}")
        await status_msg.edit_text("🚀 ফাইল আপলোড হচ্ছে...")
        
        # থাম্বনেইল চেক করা
        thumb_path = None
        thumb_id = get_thumbnail(user_id)
        if thumb_id:
            thumb_path = await client.download_media(thumb_id, file_name="temp_thumb.jpg")
            # আপলোডের আগে আবার একবার নিশ্চিত করা সেটি HD এবং কম্প্রেসড 
            thumb_path = optimize_thumbnail(thumb_path)
            
        # ফাইল আপলোড
        if original_msg.document:
            await message.reply_document(
                document=file_path,
                thumb=thumb_path,
                caption=f"✅ রিনেম করা হয়েছে: `{new_name}`"
            )
        elif original_msg.video:
            await message.reply_video(
                video=file_path,
                thumb=thumb_path,
                caption=f"✅ রিনেম করা হয়েছে: `{new_name}`"
            )
            
        await status_msg.edit_text("✅ সফলভাবে সম্পন্ন হয়েছে!")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ ত্রুটি হয়েছে: {str(e)}")
        
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        if user_id in pending_files:
            del pending_files[user_id]

if __name__ == "__main__":
    if not os.path.exists("downloads"):
        os.mkdir("downloads")
        
    print("Bot is Starting...")
    app.run()
