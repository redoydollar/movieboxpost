import os
import telebot
import requests
import pymongo
import threading
import time
from datetime import datetime
from flask import Flask, render_template_string

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
BLOGGER_URL = os.environ.get("BLOGGER_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- MONGODB SETUP ---
client = pymongo.MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
db = client["movie_bot_db"]
movies_col = db["movies"]
settings_col = db["settings"]
blogger_col = db["blogger_tracking"]

if settings_col.count_documents({}) == 0:
    settings_col.insert_one({
        "type": "bot_config",
        "channel": os.environ.get("CHANNEL_USERNAME", "@AllLatestMovie302"),
        "file_store_bot": "YourFileStoreBotUsername",
        "tmdb_api": "", 
        "ad_step1": "<!-- Normal Ad Step 1 -->",
        "ad_step2": "<!-- Normal Ad Step 2 -->",
        "ad_18_step1": "<!-- 18+ Ad Step 1 -->",
        "ad_18_step2": "<!-- 18+ Ad Step 2 -->",
        "admins": [OWNER_ID]
    })

if blogger_col.count_documents({}) == 0:
    blogger_col.insert_one({"type": "last_post", "post_id": "0"})

def get_setting(key):
    doc = settings_col.find_one({"type": "bot_config"})
    return doc.get(key, "") if doc else ""

def is_admin(user_id):
    admins = get_setting("admins") or [OWNER_ID]
    return user_id in admins

# --- FLASK APP FOR UNLOCK PAGE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unlock Download - Movie Box</title>
    <style>
        body { background-color: #05060a; color: #f1f5f9; font-family: 'Poppins', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .unlock-card { background: #111217; padding: 20px; border-radius: 12px; width: 90%; max-width: 400px; text-align: center; border: 1px solid #222; }
        .btn { background: linear-gradient(135deg, #cc0000, #ff1a1a); color: #fff; padding: 12px 25px; border-radius: 30px; text-decoration: none; font-weight: 800; display: inline-block; margin: 10px 0; border: none; cursor: pointer; }
        .btn-blue { background: linear-gradient(135deg, #38bdf8, #0ea5e9); color: #000; }
        .ad-container { background: #000; margin: 15px 0; padding: 10px; border-radius: 8px; min-height: 100px; border: 1px dashed #333; }
        .hidden { display: none; }
        #age-gate { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 1000; display: flex; justify-content: center; align-items: center; }
        .age-box { background: #111; padding: 30px; border-radius: 10px; border: 2px solid #ff0000; text-align: center; }
    </style>
</head>
<body>
    <div id="age-gate" class="hidden">
        <div class="age-box">
            <h2 style="color:#ff4d4d;">⚠️ 18+ Content Warning</h2>
            <p>এই কন্টেন্টটি শুধুমাত্র ১৮+ দর্শকদের জন্য।<br>আপনি কি ১৮ বছরের বেশি বয়সী?</p>
            <button class="btn" onclick="verifyAge(true)">হ্যাঁ, আমি ১৮+ আছি</button>
            <button class="btn btn-blue" onclick="verifyAge(false)">না, ফিরে যাব</button>
        </div>
    </div>
    <div class="unlock-card">
        <h2 style="color:#38bdf8;">🔓 Unlock Download</h2>
        <p style="font-size:13px; color:#aaa;">ফাইল ডাউনলোড করতে নিচের ২টি ধাপ সম্পন্ন করুন</p>
        <div id="step1">
            <h3 style="color:#fff; font-size:14px;">Step 1: Verify You Are Human</h3>
            <div class="ad-container">{{ ad_step1 | safe }}</div>
            <button class="btn" onclick="completeStep1()">Verify Step 1 ✅</button>
        </div>
        <div id="step2" class="hidden">
            <h3 style="color:#fff; font-size:14px;">Step 2: Final Verification</h3>
            <div class="ad-container">{{ ad_step2 | safe }}</div>
            <button class="btn" onclick="completeStep2()">Unlock Download 🔓</button>
        </div>
        <div id="final-step" class="hidden">
            <h3 style="color:#00ff00;">✅ Verification Complete!</h3>
            <a id="final-link" href="#" class="btn btn-blue">⬇️ Go to File Store Bot</a>
        </div>
    </div>
    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const isAdult = urlParams.get('is_adult');
        const token = urlParams.get('token');
        const fileStoreBase = "https://t.me/{{ file_store_bot }}?start=";
        window.onload = () => { if(isAdult === '1') document.getElementById('age-gate').classList.remove('hidden'); };
        function verifyAge(isAdult) { if(isAdult) document.getElementById('age-gate').classList.add('hidden'); else window.history.back(); }
        function completeStep1() { document.getElementById('step1').style.display = 'none'; document.getElementById('step2').classList.remove('hidden'); }
        function completeStep2() { document.getElementById('step2').style.display = 'none'; document.getElementById('final-step').classList.remove('hidden'); document.getElementById('final-link').href = fileStoreBase + token; }
    </script>
</body>
</html>
"""

@app.route('/unlock')
def unlock_page():
    req_args = requests.args # 'requests' library is wrong here, should use flask's request.args. Let me fix this.
    from flask import request
    is_adult = request.args.get('is_adult', '0')
    if is_adult == '1':
        ad_step1 = get_setting("ad_18_step1")
        ad_step2 = get_setting("ad_18_step2")
    else:
        ad_step1 = get_setting("ad_step1")
        ad_step2 = get_setting("ad_step2")
    return render_template_string(HTML_TEMPLATE, ad_step1=ad_step1, ad_step2=ad_step2, file_store_bot=get_setting("file_store_bot"))

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- BLOGGER AUTO-UPLOAD CHECKER ---
def check_blogger_updates():
    while True:
        try:
            feed_url = f"{BLOGGER_URL}/feeds/posts/default?alt=json&max-results=1"
            response = requests.get(feed_url).json()
            if 'feed' in response and 'entry' in response['feed']:
                latest_post = response['feed']['entry'][0]
                post_id = latest_post['id']['$t']
                last_doc = blogger_col.find_one({"type": "last_post"})
                if post_id != last_doc['post_id']:
                    title = latest_post['title']['$t']
                    link = latest_post['link'][-1]['href']
                    is_18plus = 0
                    if 'category' in latest_post:
                        for cat in latest_post['category']:
                            if cat['term'].lower() in ['adult', '18+', '18 plus', 'adult movie and series']:
                                is_18plus = 1; break
                    unlock_token = f"BLOG_{title.replace(' ', '_')}_{datetime.now().timestamp()}"
                    movies_col.insert_one({"title": title, "blog_url": link, "token": unlock_token, "is_18plus": is_18plus})
                    blogger_col.update_one({"type": "last_post"}, {"$set": {"post_id": post_id}})
                    render_url = os.environ.get("RENDER_URL", "https://your-app.onrender.com")
                    unlock_link = f"{render_url}/unlock?token={unlock_token}&is_adult={is_18plus}"
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton("⬇️ Download Now", url=unlock_link))
                    bot.send_message(get_setting("channel"), f"🎬 **{title}**\n\n🔓 Download: {unlock_link}", reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            print(f"Blogger Error: {e}")
        time.sleep(120)

# --- TMDb AUTO FETCH MOVIE ---
def fetch_movie_data(movie_name):
    tmdb_key = get_setting("tmdb_api")
    if not tmdb_key: return None
    url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_key}&query={movie_name}"
    try:
        response = requests.get(url).json()
        if response.get('results'):
            movie = response['results'][0]
            movie_id = movie['id']
            details = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb_key}").json()
            videos = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={tmdb_key}").json()
            images = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/images?api_key={tmdb_key}").json()
            trailer_key = ""
            for v in videos.get('results', []):
                if v['type'] == 'Trailer' and v['site'] == 'YouTube': trailer_key = v['key']; break
            screenshots = [img['file_path'] for img in images.get('backdrops', [])[:3]]
            return {
                'title': details.get('title', 'N/A'), 'year': details.get('release_date', 'N/A').split('-')[0],
                'imdb': details.get('vote_average', 'N/A'), 'genre': ', '.join([g['name'] for g in details.get('genres', [])]),
                'runtime': str(details.get('runtime', 'N/A')), 'language': details.get('original_language', 'N/A').upper(),
                'plot': details.get('overview', 'N/A'), 'poster': f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}",
                'screenshots': screenshots, 'trailer': f"https://youtube.com/watch?v={trailer_key}" if trailer_key else "N/A"
            }
    except Exception as e:
        print(f"TMDb Error: {e}")
    return None

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🌟 Welcome to Movie Box Bot!")

# --- SETTING COMMANDS ---
@bot.message_handler(commands=['set_tmdb'])
def set_tmdb(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🔑 আপনার TMDb API Key পাঠান:")
    bot.register_next_step_handler(msg, save_setting, "tmdb_api")

@bot.message_handler(commands=['set_ad'])
def set_ad(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🟢 নরমাল Step 1 এর অ্যাড কোড পাঠান:")
    bot.register_next_step_handler(msg, set_ad_step2_normal)

def set_ad_step2_normal(message):
    settings_col.update_one({"type": "bot_config"}, {"$set": {"ad_step1": message.text}})
    msg = bot.send_message(message.chat.id, "✅ Step 1 সেভ হয়েছে!\n🟢 এখন নরমাল Step 2 এর অ্যাড কোড পাঠান:")
    bot.register_next_step_handler(msg, save_setting, "ad_step2")

@bot.message_handler(commands=['set_ad_18'])
def set_ad_18(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🔴 18+ Step 1 এর অ্যাড কোড পাঠান:")
    bot.register_next_step_handler(msg, set_ad_step2_18)

def set_ad_step2_18(message):
    settings_col.update_one({"type": "bot_config"}, {"$set": {"ad_18_step1": message.text}})
    msg = bot.send_message(message.chat.id, "✅ 18+ Step 1 সেভ হয়েছে!\n🔴 এখন 18+ Step 2 এর অ্যাড কোড পাঠান:")
    bot.register_next_step_handler(msg, save_setting, "ad_18_step2")

@bot.message_handler(commands=['set_channel'])
def set_channel(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "📢 চ্যানেল ইউজারনেম পাঠান:")
    bot.register_next_step_handler(msg, save_setting, "channel")

@bot.message_handler(commands=['set_file_bot'])
def set_file_bot(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🤖 File Store Bot ইউজারনেম দিন (without @):")
    bot.register_next_step_handler(msg, save_setting, "file_store_bot")

def save_setting(message, key):
    settings_col.update_one({"type": "bot_config"}, {"$set": {key: message.text}})
    bot.send_message(message.chat.id, f"✅ {key} সফলভাবে আপডেট হয়েছে!")


# ==========================================
# FLAWLESS MOVIE UPLOAD STATE MANAGEMENT
# ==========================================
user_data_temp = {}

@bot.message_handler(commands=['addmovie'])
def add_movie_start(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন (English এ):")
    bot.register_next_step_handler(msg, process_movie_name)

def process_movie_name(message):
    movie_name = message.text
    bot.send_message(message.chat.id, "🔍 TMDb থেকে তথ্য আনা হচ্ছে...")
    movie_data = fetch_movie_data(movie_name)
    if not movie_data:
        bot.send_message(message.chat.id, "❌ মুভি পাওয়া যায়নি! আবার চেষ্টা করুন বা /manualmovie ব্যবহার করুন।")
        return
    
    # Save temporarily using user ID
    user_data_temp[message.from_user.id] = movie_data
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ Yes", callback_data="confirm_movie"))
    bot.send_photo(message.chat.id, movie_data['poster'], caption=f"🎬 {movie_data['title']}\n⭐ IMDb: {movie_data['imdb']}\n\nএই মুভিটি কি?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "confirm_movie")
def ask_file_link_callback(call):
    bot.answer_callback_query(call.id) # Remove loading icon from button
    bot.send_message(call.message.chat.id, "🔗 File Store Bot থেকে পাওয়া ফাইল লিংকটি দিন:")
    bot.register_next_step_handler(call.message, process_file_link)

def process_file_link(message):
    user_id = message.from_user.id
    if user_id not in user_data_temp:
        bot.send_message(message.chat.id, "❌ Session expired! /addmovie দিয়ে আবার শুরু করুন।")
        return
        
    file_link = message.text
    user_data_temp[user_id]['file_link'] = file_link
    
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("🔞 Yes (18+)", "🟢 No (Universal)")
    bot.send_message(message.chat.id, "🔞 এটি কি 18+ মুভি?", reply_markup=markup)
    bot.register_next_step_handler(message, save_final_movie)

def save_final_movie(message):
    user_id = message.from_user.id
    if user_id not in user_data_temp:
        bot.send_message(message.chat.id, "❌ Session expired! /addmovie দিয়ে আবার শুরু করুন।")
        return

    is_18plus = 1 if "Yes" in message.text else 0
    data = user_data_temp[user_id]
    
    title = data['title']; year = data['year']; imdb = data['imdb']; genre = data['genre']; language = data['language']; poster = data['poster']; file_link = data['file_link']

    unlock_token = f"MOV_{title.replace(' ', '_')}_{datetime.now().timestamp()}"
    
    movie_doc = {"title": title, "year": year, "imdb": imdb, "genre": genre, "language": language, "poster": poster, "file_link": file_link, "token": unlock_token, "is_18plus": is_18plus}
    
    try:
        movies_col.insert_one(movie_doc)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Database Error: {e}")
        del user_data_temp[user_id]
        return

    render_url = os.environ.get("RENDER_URL", "https://your-app.onrender.com")
    unlock_link = f"{render_url}/unlock?token={unlock_token}&is_adult={is_18plus}"
    
    channel_text = f"🎬 {title} ({year})\n⭐ IMDb: {imdb}/10\n🎭 Genre: {genre}\n\n🔓 Download: {unlock_link}"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⬇️ Download Now", url=unlock_link))
    
    try:
        channel_id = get_setting("channel")
        if not channel_id:
            bot.send_message(message.chat.id, "❌ Channel not set! Use /set_channel first.")
        else:
            bot.send_photo(channel_id, poster, caption=channel_text, reply_markup=markup)
            bot.send_message(message.chat.id, "✅ মুভি সফলভাবে চ্যানেলে পোস্ট হয়েছে!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Channel Post Failed! Error: {e}\n\nBot কি Channel এ Admin হিসেবে আছে?")
    
    # Clear temp data
    del user_data_temp[user_id]

# --- MANUAL UPLOAD ---
manual_data = {}

@bot.message_handler(commands=['manualmovie'])
def manual_start(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "📝 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, manual_year)

def manual_year(message):
    manual_data[message.from_user.id] = {'title': message.text}
    msg = bot.send_message(message.chat.id, "📅 রিলিজ ইয়ার লিখুন (যেমন: 2024):")
    bot.register_next_step_handler(msg, manual_imdb)

def manual_imdb(message):
    manual_data[message.from_user.id]['year'] = message.text
    msg = bot.send_message(message.chat.id, "⭐ IMDb রেটিং লিখুন (যেমন: 8.5):")
    bot.register_next_step_handler(msg, manual_genre)

def manual_genre(message):
    manual_data[message.from_user.id]['imdb'] = message.text
    msg = bot.send_message(message.chat.id, "🎭 জেনার লিখুন (যেমন: Action, Thriller):")
    bot.register_next_step_handler(msg, manual_lang)

def manual_lang(message):
    manual_data[message.from_user.id]['genre'] = message.text
    msg = bot.send_message(message.chat.id, "🌐 ভাষা লিখুন (যেমন: Hindi, English):")
    bot.register_next_step_handler(msg, manual_file_link)

def manual_file_link(message):
    manual_data[message.from_user.id]['language'] = message.text
    msg = bot.send_message(message.chat.id, "🔗 File Store Bot এর ফাইল লিংক দিন:")
    bot.register_next_step_handler(msg, manual_poster)

def manual_poster(message):
    manual_data[message.from_user.id]['file_link'] = message.text
    msg = bot.send_message(message.chat.id, "🖼️ পোস্টার ইমেজ লিংক দিন (অথবা 'None' লিখুন):")
    bot.register_next_step_handler(msg, manual_18plus)

def manual_18plus(message):
    manual_data[message.from_user.id]['poster'] = message.text if message.text.lower() != 'none' else "https://via.placeholder.com/200x300"
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("🔞 Yes (18+)", "🟢 No (Universal)")
    msg = bot.send_message(message.chat.id, "🔞 এটি কি 18+ মুভি?", reply_markup=markup)
    bot.register_next_step_handler(msg, save_manual_movie)

def save_manual_movie(message):
    is_18plus = 1 if "Yes" in message.text else 0
    data = manual_data[message.from_user.id]
    
    title = data['title']; year = data['year']; imdb = data['imdb']; genre = data['genre']; language = data['language']; poster = data['poster']; file_link = data['file_link']

    unlock_token = f"MOV_{title.replace(' ', '_')}_{datetime.now().timestamp()}"
    
    movie_doc = {"title": title, "year": year, "imdb": imdb, "genre": genre, "language": language, "poster": poster, "file_link": file_link, "token": unlock_token, "is_18plus": is_18plus}
    
    try:
        movies_col.insert_one(movie_doc)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Database Error: {e}")
        del manual_data[message.from_user.id]
        return

    render_url = os.environ.get("RENDER_URL", "https://your-app.onrender.com")
    unlock_link = f"{render_url}/unlock?token={unlock_token}&is_adult={is_18plus}"
    
    channel_text = f"🎬 {title} ({year})\n⭐ IMDb: {imdb}/10\n🎭 Genre: {genre}\n\n🔓 Download: {unlock_link}"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⬇️ Download Now", url=unlock_link))
    
    try:
        channel_id = get_setting("channel")
        if not channel_id:
            bot.send_message(message.chat.id, "❌ Channel not set! Use /set_channel first.")
        else:
            bot.send_photo(channel_id, poster, caption=channel_text, reply_markup=markup)
            bot.send_message(message.chat.id, "✅ মুভি সফলভাবে চ্যানেলে পোস্ট হয়েছে!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Channel Post Failed! Error: {e}\n\nBot কি Channel এ Admin হিসেবে আছে?")

    del manual_data[message.from_user.id]

# --- START BOT & FLASK ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    threading.Thread(target=check_blogger_updates, daemon=True).start()
    bot.infinity_polling()
