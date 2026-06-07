import os
import time
import threading
import requests
from bson.objectid import ObjectId
from dotenv import load_dotenv
import telebot
from flask import Flask
from database import movies_col, series_col, ads_col, admins_col, states_col

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

bot = telebot.TeleBot(TOKEN)

# ==========================================
# FLASK WEB SERVER (For Render Web Service)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ MovieBoxBD Bot is Running Successfully!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
# ==========================================

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

def get_state(user_id):
    return states_col.find_one({"user_id": user_id})

def set_state(user_id, action, temp_data=None):
    states_col.update_one({"user_id": user_id}, {"$set": {"action": action, "temp_data": temp_data or {}}}, upsert=True)

def clear_state(user_id):
    states_col.delete_one({"user_id": user_id})

# --- Unskippable Ad Timer Logic ---
def ad_timer(chat_id, msg_id, next_markup):
    ad_config = ads_col.find_one({})
    duration = ad_config.get("ad_duration", 5) if ad_config else 5
    time.sleep(duration)
    try: bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=next_markup)
    except: pass

# --- Admin Panel Command ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("🎬 Add Movie", callback_data="admin_add_movie"),
        telebot.types.InlineKeyboardButton("📺 Add Web Series", callback_data="admin_add_series"),
        telebot.types.InlineKeyboardButton("🖼 Set Normal Ad 1", callback_data="admin_set_ad1"),
        telebot.types.InlineKeyboardButton("🖼 Set Normal Ad 2", callback_data="admin_set_ad2"),
        telebot.types.InlineKeyboardButton("🔞 Set 18+ Ad 1", callback_data="admin_set_aad1"),
        telebot.types.InlineKeyboardButton("🔞 Set 18+ Ad 2", callback_data="admin_set_aad2"),
        telebot.types.InlineKeyboardButton("⚙️ Toggle Ads ON/OFF", callback_data="admin_toggle_ads")
    )
    bot.send_message(message.chat.id, "🛠 *Admin Control Panel*", parse_mode="Markdown", reply_markup=markup)

# --- User: Search & Display ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎬 Welcome to *MOVIE BOX BD*!\n\nSend a movie or series name to search.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: not m.text.startswith('/'))
def search_content(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    if state: return

    query = message.text.lower()
    movies = list(movies_col.find({"title": {"$regex": query, "$options": "i"}}).limit(5))
    series = list(series_col.find({"title": {"$regex": query, "$options": "i"}}).limit(5))

    buttons = []
    for m in movies: buttons.append([telebot.types.InlineKeyboardButton(f"🎬 {m['title']}", callback_data=f"mov_{m['_id']}")])
    for s in series: buttons.append([telebot.types.InlineKeyboardButton(f"📺 {s['title']}", callback_data=f"ser_{s['_id']}")])

    if not buttons:
        bot.reply_to(message, "❌ No results found.")
        return
    bot.send_message(user_id, "🔍 Search Results:", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

# --- All Callbacks ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = call.data

    # ============ ADMIN CALLBACKS ============
    if data == "admin_add_movie":
        if not is_admin(user_id): return
        set_state(user_id, "wait_tmdb_query")
        bot.send_message(user_id, "🎬 Send Movie Name to search in TMDB:")
        
    elif data == "admin_add_series":
        if not is_admin(user_id): return
        set_state(user_id, "wait_tmdb_tv_query")
        bot.send_message(user_id, "📺 Send Web Series Name to search in TMDB:")
        
    elif data.startswith("admin_set_"):
        if not is_admin(user_id): return
        mapping = {"admin_set_ad1": "set_ad_normal_ad1", "admin_set_ad2": "set_ad_normal_ad2", "admin_set_aad1": "set_ad_adult_ad1", "admin_set_aad2": "set_ad_adult_ad2"}
        set_state(user_id, mapping[data])
        bot.send_message(user_id, "🖼 Send the Ad Image:")
        
    elif data == "admin_toggle_ads":
        if not is_admin(user_id): return
        s = ads_col.find_one({})
        new_status = not s.get("ads_enabled", True)
        ads_col.update_one({}, {"$set": {"ads_enabled": new_status}})
        status_text = "ON ✅" if new_status else "OFF ❌"
        bot.answer_callback_query(call.id, f"Ads are now {status_text}", show_alert=True)

    elif data.startswith("tmdb_"):
        tmdb_id = data.split('_')[1]
        details = get_tmdb_movie_details(tmdb_id)
        temp_data = {"title": details.get('title', 'Unknown'), "description": details.get('overview', 'No description.'), "rating": details.get('vote_average', 0)}
        poster_path = details.get('poster_path')
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            msg = bot.send_photo(user_id, poster_url, caption=f"🎬 Selected: *{temp_data['title']}*\n\nNow send Screenshots (Album) or type `skip`:", parse_mode="Markdown")
            temp_data['poster_file_id'] = msg.photo[-1].file_id
        else:
            bot.send_message(user_id, "No poster. Send Poster Image manually:")
            temp_data['poster_file_id'] = ""
        set_state(user_id, "add_mov_ss", temp_data)

    elif data.startswith("tmdbtv_"):
        tv_id = data.split('_')[1]
        details = get_tmdb_tv_details(tv_id)
        temp_data = {"title": details.get('name', 'Unknown'), "description": details.get('overview', 'No description.')}
        poster_path = details.get('poster_path')
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            msg = bot.send_photo(user_id, poster_url, caption=f"📺 Selected: *{temp_data['title']}*\n\nSeries saved! Use /admin -> Add Episode.", parse_mode="Markdown")
            temp_data['poster_file_id'] = msg.photo[-1].file_id
        else: temp_data['poster_file_id'] = ""
        series_col.insert_one({"title": temp_data['title'], "poster_file_id": temp_data['poster_file_id'], "description": temp_data['description'], "episodes": [], "is_adult": False})
        clear_state(user_id)

    elif data.startswith("addsep_"):
        ser_id = data.split('_')[1]
        set_state(user_id, "add_ep_name", {"series_id": ser_id})
        bot.send_message(user_id, "📝 Send Episode Name (e.g. Episode 5):")

    # ============ USER CALLBACKS ============
    elif data.startswith('mov_'):
        movie = movies_col.find_one({"_id": ObjectId(data.split('_')[1])})
        if not movie: return
        caption = f"🎬 *{movie['title']}*\n⭐ Rating: {movie.get('rating', 'N/A')}\n\n{movie['description']}"
        buttons = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("📥 Download File", callback_data=f"dl_mov_{movie['_id']}")]])
        if movie.get('screenshots'):
            media = [telebot.types.InputMediaPhoto(fid) for fid in movie['screenshots']]
            bot.send_media_group(user_id, media)
        bot.send_photo(user_id, movie['poster_file_id'], caption=caption, parse_mode="Markdown", reply_markup=buttons)

    elif data.startswith('ser_'):
        series = series_col.find_one({"_id": ObjectId(data.split('_')[1])})
        if not series: return
        caption = f"📺 *{series['title']}*\n\n{series['description']}"
        buttons = []
        for ep in series.get('episodes', []): buttons.append([telebot.types.InlineKeyboardButton(f"Episode {ep['ep_num']} - {ep['name']}", callback_data=f"dl_ep_{series['_id']}_{ep['ep_num']}")])
        bot.send_photo(user_id, series['poster_file_id'], caption=caption, parse_mode="Markdown", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

    elif data.startswith('dl_mov_') or data.startswith('dl_ep_'):
        ad_config = ads_col.find_one({})
        if not ad_config or not ad_config.get("ads_enabled"):
            deliver_file(user_id, data); return
        is_adult = False
        if data.startswith('dl_mov_'):
            movie = movies_col.find_one({"_id": ObjectId(data.split('_')[2])})
            if movie: is_adult = movie.get('is_adult', False)
            file_identifier = data 
        else:
            series = series_col.find_one({"_id": ObjectId(data.split('_')[2])})
            if series: is_adult = series.get('is_adult', False)
            file_identifier = data 
        ad1 = ad_config['adult_ad1'] if is_adult else ad_config['normal_ad1']
        ad2 = ad_config['adult_ad2'] if is_adult else ad_config['normal_ad2']
        if not ad1 or not ad2:
            bot.send_message(user_id, "⚠️ Ads not set. Use /admin"); return
        wait_btn = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("⏳ Ad 1: Wait...", callback_data="ignore")]])
        ad_msg = bot.send_photo(user_id, ad1, reply_markup=wait_btn)
        next_btn = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("➡️ Next Ad", callback_data=f"ad2_{file_identifier}_{ad2}")]])
        threading.Thread(target=ad_timer, args=(user_id, ad_msg.message_id, next_btn)).start()

    elif data.startswith('ad2_'):
        parts = data.split('_'); file_identifier = parts[1]; ad2_file_id = parts[2]
        wait_btn = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("⏳ Ad 2: Wait...", callback_data="ignore")]])
        ad_msg = bot.send_photo(user_id, ad2_file_id, reply_markup=wait_btn)
        final_btn = telebot.types.InlineKeyboardMarkup([[telebot.types.InlineKeyboardButton("✅ Get File", callback_data=f"finaldl_{file_identifier}")]])
        threading.Thread(target=ad_timer, args=(user_id, ad_msg.message_id, final_btn)).start()

    elif data.startswith('finaldl_'):
        deliver_file(user_id, data[8:])
    elif data == 'ignore':
        bot.answer_callback_query(call.id, text="Please wait...")

def deliver_file(user_id, data):
    try:
        if data.startswith('dl_mov_'):
            movie = movies_col.find_one({"_id": ObjectId(data.split('_')[2])})
            if movie: bot.send_document(user_id, movie['movie_file_id'], caption=f"🎬 {movie['title']}")
        elif data.startswith('dl_ep_'):
            parts = data.split('_'); series = series_col.find_one({"_id": ObjectId(parts[2])}); ep_num = int(parts[3])
            ep = next((ep for ep in series['episodes'] if ep['ep_num'] == ep_num), None)
            if ep: bot.send_document(user_id, ep['file_id'], caption=f"📺 {series['title']} - Ep {ep_num}")
    except Exception as e: bot.send_message(user_id, "❌ Error fetching file.")

# ================= ADMIN WORKFLOW STATE HANDLER =================
@bot.message_handler(func=lambda m: get_state(m.from_user.id) is not None, content_types=['text', 'photo', 'document', 'video'])
def handle_state(message):
    user_id = message.from_user.id; state = get_state(user_id); action = state['action']; temp = state.get('temp_data', {})
    try:
        if action == 'wait_tmdb_query':
            results = search_tmdb_movie(message.text)
            if not results: bot.reply_to(user_id, "❌ Not found. Send another name:"); return
            markup = telebot.types.InlineKeyboardMarkup()
            for r in results: markup.add(telebot.types.InlineKeyboardButton(f"{r.get('title', 'N/A')} ({r.get('release_date', '')[:4]})", callback_data=f"tmdb_{r['id']}"))
            bot.send_message(user_id, "Select a movie:", reply_markup=markup); clear_state(user_id)

        elif action == 'wait_tmdb_tv_query':
            results = search_tmdb_tv(message.text)
            if not results: bot.reply_to(user_id, "❌ Not found. Send another name:"); return
            markup = telebot.types.InlineKeyboardMarkup()
            for r in results: markup.add(telebot.types.InlineKeyboardButton(f"{r.get('name', 'N/A')} ({r.get('first_air_date', '')[:4]})", callback_data=f"tmdbtv_{r['id']}"))
            bot.send_message(user_id, "Select a series:", reply_markup=markup); clear_state(user_id)

        elif action == 'add_mov_ss':
            sids = []; 
            if message.photo: sids = [p.file_id for p in message.photo]
            temp['screenshots'] = sids; set_state(user_id, 'add_mov_file', temp)
            bot.reply_to(user_id, "📁 Send Movie File (Document/Video):")
            
        elif action == 'add_mov_file':
            if not message.document and not message.video: return bot.reply_to(user_id, "Send a file.")
            temp['movie_file_id'] = message.document.file_id if message.document else message.video.file_id
            movies_col.insert_one({"title": temp['title'], "poster_file_id": temp.get('poster_file_id', ''), "screenshots": temp.get('screenshots', []), "movie_file_id": temp['movie_file_id'], "description": temp.get('description', ''), "rating": temp.get('rating', 'N/A'), "is_adult": False})
            clear_state(user_id); bot.reply_to(user_id, "✅ Movie Added Successfully!")

        elif action == 'add_ep_name':
            temp['ep_name'] = message.text; set_state(user_id, 'add_ep_file', temp)
            bot.reply_to(user_id, "📁 Send Episode File (Document/Video):")
            
        elif action == 'add_ep_file':
            if not message.document and not message.video: return bot.reply_to(user_id, "Send a file.")
            file_id = message.document.file_id if message.document else message.video.file_id
            series = series_col.find_one({"_id": ObjectId(temp['series_id'])}); ep_num = len(series['episodes']) + 1
            series_col.update_one({"_id": ObjectId(temp['series_id'])}, {"$push": {"episodes": {"ep_num": ep_num, "name": temp['ep_name'], "file_id": file_id}}})
            clear_state(user_id); bot.reply_to(user_id, f"✅ Episode {ep_num} added!")

        elif action.startswith('set_ad_'):
            ad_key = action.replace('set_ad_', '')
            if not message.photo: return bot.reply_to(user_id, "Send an image.")
            ads_col.update_one({}, {"$set": {ad_key: message.photo[-1].file_id}}); clear_state(user_id)
            bot.reply_to(user_id, f"✅ Ad ({ad_key}) Updated!")

    except Exception as e: clear_state(user_id); bot.reply_to(user_id, f"❌ Error: {e}.")

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🤖 Bot & Flask Server are running...")
    # Start the Telegram Bot
    bot.infinity_polling()
