import os
import telebot
import requests
import pymongo
import threading
import json
from datetime import datetime
from flask import Flask, request

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
BLOGGER_URL = os.environ.get("BLOGGER_URL")
TMDB_KEY = os.environ.get("TMDB_API_KEY") # Add this to Render Environment Variables!

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- MONGODB SETUP ---
client = pymongo.MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
db = client["movie_bot_db"]
settings_col = db["settings"]
user_workflow = {} # To track multi-step user actions

if settings_col.count_documents({}) == 0:
    settings_col.insert_one({
        "type": "bot_config",
        "channel": os.environ.get("CHANNEL_USERNAME", "@AllLatestMovie302"),
        "website": "https://www.movieboxbd.xyz",
        "ad_link": "https://www.effectivecpmnetwork.com/t0t62pphrs?key=your_key",
        "admins": [OWNER_ID]
    })

def get_setting(key):
    doc = settings_col.find_one({"type": "bot_config"})
    return doc.get(key, "") if doc else ""

def is_admin(user_id):
    return user_id in get_setting("admins") or user_id == OWNER_ID

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- PREMIUM HTML GENERATOR (NETFLIX + CYBERPUNK) ---
def generate_premium_html(data):
    lang = data.get('language', 'N/A')
    quality = data.get('quality', 'N/A')
    title = data.get('title', 'N/A')
    year = data.get('year', 'N/A')
    imdb = data.get('imdb', 'N/A')
    genre = data.get('genre', 'N/A')
    runtime = data.get('runtime', 'N/A')
    plot = data.get('plot', 'N/A')
    poster = data.get('poster', '')
    backdrop = data.get('backdrop', '')
    trailer = data.get('trailer', '')
    cast_list = data.get('cast', [])
    dl_link = data.get('dl_link', '#')
    ad_link = get_setting("ad_link")
    website = get_setting("website")

    cast_html = ""
    for c in cast_list[:4]:
        cast_html += f'<div class="cast-card"><img src="{c["img"]}"/><span>{c["name"]}</span></div>'

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1.0'/>
<title>{title} Download - MOVIE BOX</title>
<style>
    :root {{ --neon-cyan: #00f3ff; --neon-green: #39ff14; --neon-pink: #ff00ff; --bg-dark: #050505; --card-bg: rgba(10, 10, 10, 0.8); }}
    body {{ background-color: var(--bg-dark); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 15px; }}
    .movie-container {{ max-width: 500px; margin: 0 auto; border: 1px solid var(--neon-cyan); border-radius: 15px; overflow: hidden; background: var(--card-bg); backdrop-filter: blur(10px); box-shadow: 0 0 20px rgba(0, 243, 255, 0.2); }}
    .backdrop {{ width: 100%; height: 200px; object-fit: cover; opacity: 0.6; mask-image: linear-gradient(to bottom, black, transparent); -webkit-mask-image: linear-gradient(to bottom, black, transparent); }}
    .poster-wrapper {{ display: flex; margin-top: -100px; padding: 0 15px; gap: 15px; align-items: flex-end; }}
    .poster {{ width: 120px; height: 180px; border-radius: 10px; border: 2px solid var(--neon-pink); box-shadow: 0 0 15px rgba(255, 0, 255, 0.4); object-fit: cover; }}
    .title-section {{ padding-bottom: 10px; }}
    .title {{ font-size: 20px; font-weight: bold; color: #fff; text-shadow: 0 0 5px var(--neon-cyan); margin: 0; }}
    .tags {{ display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }}
    .tag {{ background: rgba(0, 243, 255, 0.1); border: 1px solid var(--neon-cyan); color: var(--neon-cyan); padding: 3px 8px; border-radius: 50px; font-size: 11px; font-weight: bold; box-shadow: 0 0 5px rgba(0, 243, 255, 0.2); }}
    .info-table {{ width: 100%; padding: 15px; border-collapse: collapse; }}
    .info-table td {{ padding: 5px 0; font-size: 13px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
    .info-table td:first-child {{ color: #aaa; width: 30%; }}
    .story {{ padding: 0 15px 15px; font-size: 13px; line-height: 1.5; color: #ccc; }}
    .cast-section {{ padding: 0 15px 15px; }}
    .cast-grid {{ display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; }}
    .cast-card {{ display: flex; flex-direction: column; align-items: center; min-width: 70px; }}
    .cast-card img {{ width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 1px solid var(--neon-green); }}
    .cast-card span {{ font-size: 10px; margin-top: 5px; color: #fff; text-align: center; }}
    .btn-container {{ padding: 0 15px 15px; display: flex; flex-direction: column; gap: 10px; }}
    .neon-btn {{ display: block; text-align: center; padding: 12px; border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 14px; transition: 0.3s; }}
    .btn-dl {{ background: #0a0a0a; border: 1px solid var(--neon-cyan); color: var(--neon-cyan); box-shadow: 0 0 10px rgba(0, 243, 255, 0.3); }}
    .btn-dl:hover {{ background: var(--neon-green); color: #000; border-color: var(--neon-green); box-shadow: 0 0 20px rgba(57, 255, 20, 0.5); }}
    .btn-trailer {{ background: transparent; border: 1px solid var(--neon-pink); color: var(--neon-pink); }}
    .footer {{ text-align: center; padding: 15px; font-size: 11px; color: #555; }}
    .footer a {{ color: var(--neon-cyan); text-decoration: none; }}
</style>
</head>
<body>
<div class='movie-container'>
    {f"<img class='backdrop' src='{backdrop}'/>" if backdrop else ""}
    <div class='poster-wrapper'>
        <img class='poster' src='{poster}'/>
        <div class='title-section'>
            <h2 class='title'>{title}</h2>
            <div class='tags'>
                <span class='tag'>⭐ {imdb}</span>
                <span class='tag'>📅 {year}</span>
                <span class='tag'>⏱️ {runtime} min</span>
                <span class='tag'>🎭 {genre.split(",")[0]}</span>
            </div>
        </div>
    </div>
    
    <table class='info-table'>
        <tr><td>Language</td><td>{lang}</td></tr>
        <tr><td>Quality</td><td>{quality}</td></tr>
        <tr><td>Genre</td><td>{genre}</td></tr>
    </table>

    <div class='story'><strong>📖 Storyline:</strong><br/>{plot}</div>
    
    {f"<div class='cast-section'><strong>🌟 Cast:</strong><div class='cast-grid'>{cast_html}</div></div>" if cast_list else ""}
    
    <div class='btn-container'>
        <a href='{ad_link}' class='neon-btn btn-dl' target='_blank'>⬇️ Download {quality} - {lang}</a>
        {f"<a href='{trailer}' class='neon-btn btn-trailer' target='_blank'>▶️ Watch Trailer</a>" if trailer != "N/A" else ""}
    </div>
    
    <div class='footer'>Powered by <a href='{website}'>MOVIE BOX</a></div>
</div>
</body>
</html>
"""

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎬 **MOVIE BOX Bot Premium Edition!**\n\nUse /addmovie to generate a post.", parse_mode="Markdown")

# --- 1. ADD MOVIE (ADVANCED WORKFLOW) ---
@bot.message_handler(commands=['addmovie'])
def add_movie_step1(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন (English):")
    bot.register_next_step_handler(msg, search_tmdb)

def search_tmdb(message):
    movie_name = message.text
    bot.send_message(message.chat.id, "🔍 TMDb থেকে সার্চ করা হচ্ছে...")
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={movie_name}"
    try:
        res = requests.get(url).json()
        if res.get('results'):
            markup = telebot.types.InlineKeyboardMarkup()
            for idx, movie in enumerate(res['results'][:5]):
                title = movie['title']
                year = movie.get('release_date', 'N/A')[:4]
                markup.add(telebot.types.InlineKeyboardButton(f"{title} ({year})", callback_data=f"sel_{movie['id']}"))
            bot.send_message(message.chat.id, "👇 মুভি সিলেক্ট করুন:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "❌ কোনো মুভি পাওয়া যায়নি!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ API Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sel_"))
def movie_selected(call):
    movie_id = call.data.split("_")[1]
    bot.answer_callback_query(call.id, "মুভি সিলেক্ট হয়েছে!")
    
    # Fetch Details
    details = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}").json()
    credits = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_KEY}").json()
    videos = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_KEY}").json()
    images = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/images?api_key={TMDB_KEY}").json()
    
    # Process Data
    trailer_key = ""
    for v in videos.get('results', []):
        if v['type'] == 'Trailer' and v['site'] == 'YouTube': trailer_key = v['key']; break
    
    cast_data = []
    for c in credits.get('cast', [])[:4]:
        cast_data.append({"name": c['name'], "img": f"https://image.tmdb.org/t/p/w200{c['profile_path']}" if c.get('profile_path') else ""})
    
    backdrop = ""
    if images.get('backdrops'):
        backdrop = f"https://image.tmdb.org/t/p/w780{images['backdrops'][0]['file_path']}"

    # Save to user workflow
    user_workflow[call.from_user.id] = {
        'title': details.get('title', 'N/A'),
        'year': details.get('release_date', 'N/A')[:4],
        'imdb': details.get('vote_average', 'N/A'),
        'genre': ', '.join([g['name'] for g in details.get('genres', [])]),
        'runtime': str(details.get('runtime', 'N/A')),
        'plot': details.get('overview', 'N/A'),
        'poster': f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}",
        'backdrop': backdrop,
        'trailer': f"https://youtube.com/watch?v={trailer_key}" if trailer_key else "N/A",
        'cast': cast_data
    }
    
    # Ask Language
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("🇧🇩 Bangla", callback_data="lang_Bangla"),
        telebot.types.InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_Hindi"),
        telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_English"),
        telebot.types.InlineKeyboardButton("🎧 Dual Audio", callback_data="lang_Dual Audio"),
        telebot.types.InlineKeyboardButton("🌍 Multi Audio", callback_data="lang_Multi Audio")
    )
    bot.send_message(call.message.chat.id, "🌐 ভাষা সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def language_selected(call):
    lang = call.data.split("_")[1]
    user_workflow[call.from_user.id]['language'] = lang
    bot.answer_callback_query(call.id, f"{lang} সিলেক্ট হয়েছে!")
    
    # Ask Quality
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("📱 480P", callback_data="qual_480P"),
        telebot.types.InlineKeyboardButton("💻 720P", callback_data="qual_720P"),
        telebot.types.InlineKeyboardButton("🖥️ 1080P", callback_data="qual_1080P"),
        telebot.types.InlineKeyboardButton("🎥 WEB-DL", callback_data="qual_WEB-DL"),
        telebot.types.InlineKeyboardButton("💿 BluRay", callback_data="qual_BluRay")
    )
    bot.send_message(call.message.chat.id, "📐 কোয়ালিটি সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("qual_"))
def quality_selected(call):
    qual = call.data.split("_")[1]
    user_workflow[call.from_user.id]['quality'] = qual
    bot.answer_callback_query(call.id, f"{qual} সিলেক্ট হয়েছে!")
    
    # Ask Download Link
    msg = bot.send_message(call.message.chat.id, "🔗 ডাউনলোড লিংক দিন:")
    bot.register_next_step_handler(msg, generate_final_post)

def generate_final_post(message):
    dl_link = message.text
    user_workflow[message.from_user.id]['dl_link'] = dl_link
    data = user_workflow[message.from_user.id]
    
    # Generate Premium HTML
    html_code = generate_premium_html(data)
    
    # Send HTML Code with Copy Button
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📋 Click to Copy Code", copy_text=html_code))
    
    bot.send_message(message.chat.id, "✅ **Premium Movie Post Generated!**\n\nনিচের বাটনে ক্লিক করে কোড কপি করে Blogger এ paste করুন।", parse_mode="Markdown")
    bot.send_message(message.chat.id, f"`{html_code[:100]}...`", reply_markup=markup, parse_mode="Markdown") # Shows preview
    
    # Also post a simplified version to Telegram Channel (With Ad Unlock)
    channel = get_setting("channel")
    unlock_token = f"MOV_{data['title'].replace(' ', '_')}_{datetime.now().timestamp()}"
    render_url = os.environ.get("RENDER_URL", "https://movieboxpost-1.onrender.com")
    unlock_link = f"{render_url}/unlock?token={unlock_token}&is_adult=0"
    
    channel_text = f"🎬 **{data['title']}** ({data['year']})\n⭐ IMDb: {data['imdb']}\n🌐 {data['language']} | 📐 {data['quality']}"
    markup_ch = telebot.types.InlineKeyboardMarkup()
    markup_ch.add(telebot.types.InlineKeyboardButton("⬇️ Download Now", url=unlock_link))
    
    try:
        bot.send_photo(channel, data['poster'], caption=channel_text, reply_markup=markup_ch, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Channel Post Error: {e}")

    # Clear Workflow
    del user_workflow[message.from_user.id]

# --- START BOT & FLASK ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
