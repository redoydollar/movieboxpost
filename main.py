import os
import time
import threading
import requests
from bson.objectid import ObjectId
from dotenv import load_dotenv
import telebot
from flask import Flask
from database import movies_col, series_col, ads_col, admins_col

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

bot = telebot.TeleBot(TOKEN)

BOT_USERNAME = ""
try:
    BOT_USERNAME = bot.get_me().username
except:
    BOT_USERNAME = "YourBotUsername"

# ==========================================
# FLASK WEB SERVER
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ MovieBoxBD Bot is Running Successfully!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
# ==========================================

# --- BLOGGER HTML GENERATOR ---
def generate_blogger_html(data, movie_id):
    download_link = f"https://t.me/{BOT_USERNAME}?start=movie_{movie_id}"
    safe_title = data.get('title', 'Unknown').replace("'", "")
    safe_desc = data.get('description', '').replace("'", "")
    
    return f"""<!-- MOVIE BOX PREMIUM POST -->
<div style="background-color:#050505; font-family:'Poppins', sans-serif; color:#fff; padding:20px; border-radius:15px; max-width:800px; margin:auto; border:1px solid #222; box-shadow:0 0 30px rgba(0,243,255,0.1);">
    <div style="width:100%; height:300px; background:url('{data.get('backdrop_url', '')}') center/cover; border-radius:12px; position:relative; margin-bottom:20px; box-shadow:0 0 25px rgba(0,0,0,0.8);">
        <div style="position:absolute; bottom:0; left:0; right:0; background:linear-gradient(to top, #050505, transparent); padding:20px; border-radius:0 0 12px 12px;">
            <h1 style="margin:0; color:#fff; text-shadow:0 0 15px #00f3ff; font-size:28px; text-transform:uppercase;">{safe_title}</h1>
            <span style="background:#ff00ff; color:#000; padding:5px 10px; border-radius:5px; font-weight:bold; font-size:12px;">⭐ {data.get('rating', 'N/A')} | {data.get('genres', 'Movie')}</span>
        </div>
    </div>
    <div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(10px); border:1px solid rgba(0,243,255,0.2); border-radius:12px; padding:20px; margin-bottom:20px; display:flex; gap:20px; flex-wrap:wrap;">
        <img src="{data.get('poster_url', '')}" style="width:150px; height:auto; border-radius:8px; box-shadow:0 0 20px rgba(0,243,255,0.3); border:2px solid #00f3ff;"/>
        <div style="flex:1; min-width:200px;">
            <table style="width:100%; border-collapse:collapse; font-size:14px;">
                <tr style="border-bottom:1px solid #222;"><td style="color:#888; padding:8px 0;">Rating</td><td style="color:#f5c518; font-weight:bold;">⭐ {data.get('rating', 'N/A')} / 10</td></tr>
                <tr style="border-bottom:1px solid #222;"><td style="color:#888; padding:8px 0;">Genre</td><td style="color:#00f3ff;">{data.get('genres', 'N/A')}</td></tr>
                <tr style="border-bottom:1px solid #222;"><td style="color:#888; padding:8px 0;">Release</td><td style="color:#fff;">📅 {data.get('release_date', 'N/A')}</td></tr>
            </table>
        </div>
    </div>
    <div style="background:rgba(0,0,0,0.5); border-left:4px solid #ff00ff; padding:15px; margin-bottom:20px; border-radius:0 8px 8px 0;">
        <h3 style="margin:0 0 10px 0; color:#ff00ff; text-transform:uppercase; font-size:16px;">Storyline</h3>
        <p style="margin:0; color:#ccc; line-height:1.6; font-size:13px;">{safe_desc}</p>
    </div>
    <div style="background:rgba(0,243,255,0.05); padding:20px; border-radius:12px; text-align:center; border:1px solid rgba(0,243,255,0.3);">
        <h3 style="margin:0 0 15px 0; color:#fff; text-transform:uppercase; letter-spacing:2px;">Download File</h3>
        <a href="{download_link}" style="display:inline-block; background:#0a0a0a; border:2px solid #00f3ff; color:#00f3ff; padding:12px 35px; border-radius:50px; text-decoration:none; font-weight:bold; font-size:16px; box-shadow:0 0 15px rgba(0,243,255,0.4);">📥 Download Now</a>
    </div>
</div>"""

# --- TMDB API Functions ---
def search_tmdb_movie(query):
    url = f"{TMDB_BASE}/search/movie?api_key={TMDB_API_KEY}&query={query}"
    try: return requests.get(url).json().get('results', [])[:5]
    except: return []

def get_tmdb_movie_details(movie_id):
    url = f"{TMDB_BASE}/movie/{movie_id}?api_key={TMDB_API_KEY}"
    try: return requests.get(url).json()
    except: return {}

def search_tmdb_tv(query):
    url = f"{TMDB_BASE}/search/tv?api_key={TMDB_API_KEY}&query={query}"
    try: return requests.get(url).json().get('results', [])[:5]
    except: return []

def get_tmdb_tv_details(tv_id):
    url = f"{TMDB_BASE}/tv/{tv_id}?api_key={TMDB_API_KEY}"
    try: return requests.get(url).json()
    except: return {}

# --- Helper Functions ---
def is_admin(user_id):
    if user_id == OWNER_ID: return True
    return admins_col.find_one({"user_id": user_id}) is not None

# --- Ad Timer Logic ---
def ad_timer(chat_id, msg_id, next_markup):
    ad_config = ads_col.find_one({})
    duration = ad_config.get("ad_duration", 5) if ad_config else 5
    time.sleep(duration)
    try: bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=next_markup)
    except: pass

# ==========================================
# BASIC COMMANDS
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    payload = message.text.split()[1] if len(message.text.split()) > 1 else None
    if payload and payload.startswith("movie_"):
        movie_id = payload.split("_")[1]
        try:
            movie = movies_col.find_one({"_id": ObjectId(movie_id)})
            if movie:
                caption = f"🎬 *{movie['title']}*\n⭐ Rating: {movie.get('rating', 'N/A')}\n\n{movie['description']}"
                buttons = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("📥 Download File", callback_data=f"dl_mov_{movie['_id']}")]])
                if movie.get('screenshots'):
                    media = [telebot.types.InputMediaPhoto(fid) for fid in movie['screenshots']]
                    bot.send_media_group(message.from_user.id, media)
                bot.send_photo(message.from_user.id, movie['poster_file_id'], caption=caption, parse_mode="Markdown", reply_markup=buttons)
                return
        except: pass
    bot.reply_to(message, "🎬 Welcome to *MOVIE BOX BD*!\n\nSend a movie or series name to search.", parse_mode="Markdown")

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    bot.reply_to(message, "✅ Process cancelled. You can now search normally.")

@bot.message_handler(commands=['toggleads'])
def cmd_toggle_ads(message):
    if not is_admin(message.from_user.id): return
    s = ads_col.find_one({})
    new_status = not s.get("ads_enabled", True)
    ads_col.update_one({}, {"$set": {"ads_enabled": new_status}})
    status_text = "ON ✅" if new_status else "OFF ❌"
    bot.reply_to(message, f"⚙️ Ads System is now {status_text}")

# ==========================================
# ADMIN ADD MOVIE FLOW
# ==========================================
@bot.message_handler(commands=['addmovie'])
def cmd_add_movie(message):
    if not is_admin(message.from_user.id): return
    msg = bot.reply_to(message, "🎬 Send Movie Name to search in TMDB:")
    bot.register_next_step_handler(msg, process_movie_name)

def process_movie_name(message):
    if message.text.startswith('/'): return cancel_cmd(message)
    results = search_tmdb_movie(message.text)
    if not results:
        msg = bot.reply_to(message, "❌ Not found on TMDB. Send another name or /cancel:")
        bot.register_next_step_handler(msg, process_movie_name)
        return
    markup = telebot.types.InlineKeyboardMarkup()
    for r in results: markup.add(telebot.types.InlineKeyboardButton(f"{r.get('title', 'N/A')} ({r.get('release_date', '')[:4]})", callback_data=f"tmdb_{r['id']}"))
    bot.send_message(message.from_user.id, "Select a movie:", reply_markup=markup)

# ==========================================
# ADMIN ADD SERIES FLOW
# ==========================================
@bot.message_handler(commands=['addseries'])
def cmd_add_series(message):
    if not is_admin(message.from_user.id): return
    msg = bot.reply_to(message, "📺 Send Web Series Name to search in TMDB:")
    bot.register_next_step_handler(msg, process_series_name)

def process_series_name(message):
    if message.text.startswith('/'): return cancel_cmd(message)
    results = search_tmdb_tv(message.text)
    if not results:
        msg = bot.reply_to(message, "❌ Not found on TMDB. Send another name or /cancel:")
        bot.register_next_step_handler(msg, process_series_name)
        return
    markup = telebot.types.InlineKeyboardMarkup()
    for r in results: markup.add(telebot.types.InlineKeyboardButton(f"{r.get('name', 'N/A')} ({r.get('first_air_date', '')[:4]})", callback_data=f"tmdbtv_{r['id']}"))
    bot.send_message(message.from_user.id, "Select a series:", reply_markup=markup)

# ==========================================
# ADMIN ADD EPISODE FLOW
# ==========================================
@bot.message_handler(commands=['addepisode'])
def cmd_add_episode(message):
    if not is_admin(message.from_user.id): return
    series = list(series_col.find({}))
    if not series:
        bot.reply_to(message, "❌ No series found. Add a series first with /addseries")
        return
    buttons = [[telebot.types.InlineKeyboardButton(s['title'], callback_data=f"addsep_{s['_id']}")] for s in series]
    bot.reply_to(message, "📺 Select a series to add episode:", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

# ==========================================
# ADMIN SET AD LINKS FLOW
# ==========================================
@bot.message_handler(commands=['setad1'])
def cmd_set_ad1(message):
    if not is_admin(message.from_user.id): return
    msg = bot.reply_to(message, "🔗 Send Adsterra Direct URL Link for Normal Ad 1:")
    bot.register_next_step_handler(msg, lambda m: save_ad_url(m, 'normal_ad1'))

@bot.message_handler(commands=['setad2'])
def cmd_set_ad2(message):
    if not is_admin(message.from_user.id): return
    msg = bot.reply_to(message, "🔗 Send Adsterra Direct URL Link for Normal Ad 2:")
    bot.register_next_step_handler(msg, lambda m: save_ad_url(m, 'normal_ad2'))

@bot.message_handler(commands=['setadultad1'])
def cmd_set_aad1(message):
    if not is_admin(message.from_user.id): return
    msg = bot.reply_to(message, "🔞 Send Adsterra Direct URL Link for 18+ Ad 1:")
    bot.register_next_step_handler(msg, lambda m: save_ad_url(m, 'adult_ad1'))

@bot.message_handler(commands=['setadultad2'])
def cmd_set_aad2(message):
    if not is_admin(message.from_user.id): return
    msg = bot.reply_to(message, "🔞 Send Adsterra Direct URL Link for 18+ Ad 2:")
    bot.register_next_step_handler(msg, lambda m: save_ad_url(m, 'adult_ad2'))

def save_ad_url(message, ad_key):
    if message.text.startswith('/'): return cancel_cmd(message)
    if not message.text or not message.text.startswith('http'):
        bot.reply_to(message, "❌ Invalid link! Must start with http/https. Process cancelled.")
        return
    ads_col.update_one({}, {"$set": {ad_key: message.text.strip()}})
    bot.reply_to(message, f"✅ Ad ({ad_key}) URL Saved Successfully!")

# ==========================================
# USER SEARCH HANDLER
# ==========================================
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def search_content(message):
    query = message.text
    movies = list(movies_col.find({"title": {"$regex": query, "$options": "i"}}).limit(5))
    series = list(series_col.find({"title": {"$regex": query, "$options": "i"}}).limit(5))

    buttons = []
    for m in movies: buttons.append([telebot.types.InlineKeyboardButton(f"🎬 {m['title']}", callback_data=f"mov_{m['_id']}")])
    for s in series: buttons.append([telebot.types.InlineKeyboardButton(f"📺 {s['title']}", callback_data=f"ser_{s['_id']}")])

    if not buttons:
        bot.reply_to(message, "❌ No results found.")
        return
    bot.send_message(message.from_user.id, "🔍 Search Results:", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

# ==========================================
# ALL CALLBACK HANDLERS
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = call.data

    # --- ADMIN TMDB MOVIE SELECTION CALLBACK ---
    if data.startswith("tmdb_"):
        tmdb_id = data.split('_')[1]
        details = get_tmdb_movie_details(tmdb_id)
        if not details.get('id'): bot.answer_callback_query(call.id, "❌ Error fetching."); return
            
        genres = ", ".join([g['name'] for g in details.get('genres', [])])
        movie_data = {
            "title": details.get('title', 'Unknown'), 
            "description": details.get('overview', ''), 
            "rating": details.get('vote_average', 0),
            "release_date": details.get('release_date', 'N/A'),
            "genres": genres,
            "poster_url": f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}" if details.get('poster_path') else "",
            "backdrop_url": f"https://image.tmdb.org/t/p/w1280{details.get('backdrop_path')}" if details.get('backdrop_path') else ""
        }
        
        if details.get('poster_path'):
            poster_url = f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}"
            msg = bot.send_photo(user_id, poster_url, caption=f"🎬 Selected: *{movie_data['title']}*\n\nNow send Screenshots or type `skip`:", parse_mode="Markdown")
            movie_data['poster_file_id'] = msg.photo[-1].file_id
        else:
            msg = bot.send_message(user_id, "Send Poster Image manually:")
            bot.register_next_step_handler(msg, process_manual_poster, movie_data)
            return

        bot.register_next_step_handler(msg, process_screenshots, movie_data)

    # --- ADMIN TMDB TV SELECTION CALLBACK ---
    elif data.startswith("tmdbtv_"):
        tv_id = data.split('_')[1]
        details = get_tmdb_tv_details(tv_id)
        if not details.get('id'): bot.answer_callback_query(call.id, "❌ Error fetching."); return
            
        series_data = {"title": details.get('name', 'Unknown'), "description": details.get('overview', '')}
        if details.get('poster_path'):
            poster_url = f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}"
            msg = bot.send_photo(user_id, poster_url, caption=f"📺 Selected: *{series_data['title']}*\n\nSeries saved! Use /addepisode.", parse_mode="Markdown")
            series_data['poster_file_id'] = msg.photo[-1].file_id
        else: series_data['poster_file_id'] = ""
        series_col.insert_one({"title": series_data['title'], "poster_file_id": series_data['poster_file_id'], "description": series_data['description'], "episodes": [], "is_adult": False})

    # --- ADMIN EPISODE SELECTION CALLBACK ---
    elif data.startswith("addsep_"):
        ser_id = data.split('_')[1]
        msg = bot.send_message(user_id, "📝 Send Episode Name (e.g. Episode 5):")
        bot.register_next_step_handler(msg, process_ep_name, ser_id)

    # --- USER MOVIE VIEW CALLBACK ---
    elif data.startswith('mov_'):
        movie = movies_col.find_one({"_id": ObjectId(data.split('_')[1])})
        if not movie: return
        caption = f"🎬 *{movie['title']}*\n⭐ Rating: {movie.get('rating', 'N/A')}\n\n{movie['description']}"
        buttons = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("📥 Download File", callback_data=f"dl_mov_{movie['_id']}")]])
        if movie.get('screenshots'):
            media = [telebot.types.InputMediaPhoto(fid) for fid in movie['screenshots']]
            bot.send_media_group(user_id, media)
        bot.send_photo(user_id, movie['poster_file_id'], caption=caption, parse_mode="Markdown", reply_markup=buttons)

    # --- USER SERIES VIEW CALLBACK ---
    elif data.startswith('ser_'):
        series = series_col.find_one({"_id": ObjectId(data.split('_')[1])})
        if not series: return
        caption = f"📺 *{series['title']}*\n\n{series['description']}"
        buttons = []
        for ep in series.get('episodes', []): buttons.append([telebot.types.InlineKeyboardButton(f"Episode {ep['ep_num']} - {ep['name']}", callback_data=f"dl_ep_{series['_id']}_{ep['ep_num']}")])
        bot.send_photo(user_id, series['poster_file_id'], caption=caption, parse_mode="Markdown", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

    # --- USER DOWNLOAD FLOW CALLBACK ---
    elif data.startswith('dl_mov_') or data.startswith('dl_ep_'):
        ad_config = ads_col.find_one({})
        if not ad_config or not ad_config.get("ads_enabled"):
            deliver_file(user_id, data); return
            
        is_adult = False
        if data.startswith('dl_mov_'):
            movie = movies_col.find_one({"_id": ObjectId(data.split('_')[2])})
            if movie: is_adult = movie.get('is_adult', False)
        else:
            series = series_col.find_one({"_id": ObjectId(data.split('_')[2])})
            if series: is_adult = series.get('is_adult', False)
            
        ad1 = ad_config['adult_ad1'] if is_adult else ad_config['normal_ad1']
        ad2 = ad_config['adult_ad2'] if is_adult else ad_config['normal_ad2']
        
        if not ad1 or not ad2:
            bot.send_message(user_id, "⚠️ Ads not configured by admin."); return
        
        wait_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        wait_btn.add(
            telebot.types.InlineKeyboardButton("🔗 Visit Ad Link 1", url=ad1),
            telebot.types.InlineKeyboardButton("⏳ Wait here...", callback_data="ignore")
        )
        ad_msg = bot.send_message(user_id, "⚠️ *Step 1:* Click the ad link, wait 5 seconds.", parse_mode="Markdown", reply_markup=wait_btn)
            
        next_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        next_btn.add(telebot.types.InlineKeyboardButton("➡️ Go to Ad 2", callback_data=f"nad1_{data}"))
        threading.Thread(target=ad_timer, args=(user_id, ad_msg.message_id, next_btn)).start()

    elif data.startswith('nad1_'):
        original_data = data[5:]
        ad_config = ads_col.find_one({})
        is_adult = False
        if original_data.startswith('dl_mov_'):
            movie = movies_col.find_one({"_id": ObjectId(original_data.split('_')[2])})
            if movie: is_adult = movie.get('is_adult', False)
        else:
            series = series_col.find_one({"_id": ObjectId(original_data.split('_')[2])})
            if series: is_adult = series.get('is_adult', False)
        ad2 = ad_config['adult_ad2'] if is_adult else ad_config['normal_ad2']
        
        wait_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        wait_btn.add(
            telebot.types.InlineKeyboardButton("🔗 Visit Ad Link 2", url=ad2),
            telebot.types.InlineKeyboardButton("⏳ Wait here...", callback_data="ignore")
        )
        ad_msg = bot.send_message(user_id, "⚠️ *Step 2:* Click the second ad link, wait 5 seconds.", parse_mode="Markdown", reply_markup=wait_btn)
            
        final_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        final_btn.add(telebot.types.InlineKeyboardButton("✅ Get File", callback_data=f"fdl_{original_data}"))
        threading.Thread(target=ad_timer, args=(user_id, ad_msg.message_id, final_btn)).start()

    elif data.startswith('fdl_'):
        original_data = data[4:]
        deliver_file(user_id, original_data)
        
    elif data == 'ignore':
        bot.answer_callback_query(call.id, text="Please wait...")

# ==========================================
# STEP BY STEP PROCESSING FUNCTIONS
# ==========================================
def process_manual_poster(message, movie_data):
    if message.text and message.text.startswith('/'): return cancel_cmd(message)
    if not message.photo:
        bot.reply_to(message, "❌ Must be an image. Send again:")
        bot.register_next_step_handler(message, process_manual_poster, movie_data)
        return
    movie_data['poster_file_id'] = message.photo[-1].file_id
    msg = bot.reply_to(message, "✅ Poster saved. Now send Screenshots or type `skip`:")
    bot.register_next_step_handler(msg, process_screenshots, movie_data)

def process_screenshots(message, movie_data):
    if message.text and message.text.startswith('/'): return cancel_cmd(message)
    sids = []
    if message.photo: sids = [p.file_id for p in message.photo]
    movie_data['screenshots'] = sids
    msg = bot.reply_to(message, "📁 Send Movie File (Document/Video):")
    bot.register_next_step_handler(msg, process_movie_file, movie_data)

def process_movie_file(message, movie_data):
    if message.text and message.text.startswith('/'): return cancel_cmd(message)
    if not message.document and not message.video:
        bot.reply_to(message, "❌ Must be a file. Send again:")
        bot.register_next_step_handler(message, process_movie_file, movie_data)
        return
        
    movie_data['movie_file_id'] = message.document.file_id if message.document else message.video.file_id
    
    inserted_movie = movies_col.insert_one({
        "title": movie_data['title'], "poster_file_id": movie_data.get('poster_file_id', ''), 
        "screenshots": movie_data.get('screenshots', []), "movie_file_id": movie_data['movie_file_id'], 
        "description": movie_data.get('description', ''), "rating": movie_data.get('rating', 'N/A'), 
        "is_adult": False
    })
    
    html_code = generate_blogger_html(movie_data, inserted_movie.inserted_id)
    bot.reply_to(message, "✅ Movie Added Successfully!\n\n👇 COPY BLOGGER HTML BELOW 👇\n\n" + html_code)

def process_ep_name(message, ser_id):
    if message.text.startswith('/'): return cancel_cmd(message)
    ep_name = message.text
    msg = bot.reply_to(message, "📁 Send Episode File (Document/Video):")
    bot.register_next_step_handler(msg, process_ep_file, ser_id, ep_name)

def process_ep_file(message, ser_id, ep_name):
    if message.text and message.text.startswith('/'): return cancel_cmd(message)
    if not message.document and not message.video:
        bot.reply_to(message, "❌ Must be a file. Send again:")
        bot.register_next_step_handler(message, process_ep_file, ser_id, ep_name)
        return
        
    file_id = message.document.file_id if message.document else message.video.file_id
    series = series_col.find_one({"_id": ObjectId(ser_id)})
    ep_num = len(series['episodes']) + 1
    series_col.update_one({"_id": ObjectId(ser_id)}, {"$push": {"episodes": {"ep_num": ep_num, "name": ep_name, "file_id": file_id}}})
    bot.reply_to(message, f"✅ Episode {ep_num} added to {series['title']}!")

def deliver_file(user_id, data):
    try:
        if data.startswith('dl_mov_'):
            movie = movies_col.find_one({"_id": ObjectId(data.split('_')[2])})
            if movie: bot.send_document(user_id, movie['movie_file_id'], caption=f"🎬 {movie['title']}")
        elif data.startswith('dl_ep_'):
            parts = data.split('_')
            series = series_col.find_one({"_id": ObjectId(parts[2])})
            ep_num = int(parts[3])
            ep = next((ep for ep in series['episodes'] if ep['ep_num'] == ep_num), None)
            if ep: bot.send_document(user_id, ep['file_id'], caption=f"📺 {series['title']} - Ep {ep_num}")
    except Exception as e: bot.send_message(user_id, "❌ Error fetching file.")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("🤖 Bot is Running Successfully...")
    bot.infinity_polling()
