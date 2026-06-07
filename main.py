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

BOT_USERNAME = ""
try:
    BOT_USERNAME = bot.get_me().username
except:
    BOT_USERNAME = "YourBotUsername"

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

# ==========================================
# ADMIN COMMANDS (Fast Access)
# ==========================================
@bot.message_handler(commands=['addmovie'])
def cmd_add_movie(message):
    if not is_admin(message.from_user.id): return
    set_state(message.from_user.id, "wait_tmdb_query")
    bot.reply_to(message, "🎬 Send Movie Name to search in TMDB:")

@bot.message_handler(commands=['addseries'])
def cmd_add_series(message):
    if not is_admin(message.from_user.id): return
    set_state(message.from_user.id, "wait_tmdb_tv_query")
    bot.reply_to(message, "📺 Send Web Series Name to search in TMDB:")

@bot.message_handler(commands=['addepisode'])
def cmd_add_episode(message):
    if not is_admin(message.from_user.id): return
    series = list(series_col.find({}))
    if not series:
        bot.reply_to(message, "❌ No series found. Add a series first with /addseries")
        return
    buttons = [[telebot.types.InlineKeyboardButton(s['title'], callback_data=f"addsep_{s['_id']}")] for s in series]
    bot.reply_to(message, "📺 Select a series to add episode:", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

@bot.message_handler(commands=['setad1'])
def cmd_set_ad1(message):
    if not is_admin(message.from_user.id): return
    set_state(message.from_user.id, "set_ad_normal_ad1")
    bot.reply_to(message, "🔗 Send the Adsterra Direct URL Link for Normal Ad 1:\n\n_(Example: https://www.profitablecpmrate.com/...)_", parse_mode="Markdown")

@bot.message_handler(commands=['setad2'])
def cmd_set_ad2(message):
    if not is_admin(message.from_user.id): return
    set_state(message.from_user.id, "set_ad_normal_ad2")
    bot.reply_to(message, "🔗 Send the Adsterra Direct URL Link for Normal Ad 2:", parse_mode="Markdown")

@bot.message_handler(commands=['setadultad1'])
def cmd_set_aad1(message):
    if not is_admin(message.from_user.id): return
    set_state(message.from_user.id, "set_ad_adult_ad1")
    bot.reply_to(message, "🔞 Send the Adsterra Direct URL Link for 18+ Ad 1:", parse_mode="Markdown")

@bot.message_handler(commands=['setadultad2'])
def cmd_set_aad2(message):
    if not is_admin(message.from_user.id): return
    set_state(message.from_user.id, "set_ad_adult_ad2")
    bot.reply_to(message, "🔞 Send the Adsterra Direct URL Link for 18+ Ad 2:", parse_mode="Markdown")

@bot.message_handler(commands=['toggleads'])
def cmd_toggle_ads(message):
    if not is_admin(message.from_user.id): return
    s = ads_col.find_one({})
    new_status = not s.get("ads_enabled", True)
    ads_col.update_one({}, {"$set": {"ads_enabled": new_status}})
    status_text = "ON ✅" if new_status else "OFF ❌"
    bot.reply_to(message, f"⚙️ Ads System is now {status_text}")

# ==========================================
# USER COMMANDS & SEARCH
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
        if is_admin(user_id):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🔍 Search TMDB to Add Movie", callback_data=f"tmdb_search_{message.text}"))
            bot.reply_to(message, "❌ No results found in database.\n\nAs an admin, you can add this from TMDB:", reply_markup=markup)
        else:
            bot.reply_to(message, "❌ No results found.")
        return
        
    bot.send_message(user_id, "🔍 Search Results:", reply_markup=telebot.types.InlineKeyboardMarkup(buttons))

# ==========================================
# ALL CALLBACKS
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = call.data

    # --- ADMIN TMDB SEARCH CALLBACK ---
    if data.startswith("tmdb_search_"):
        query = data.replace("tmdb_search_", "")
        results = search_tmdb_movie(query)
        if not results:
            bot.answer_callback_query(call.id, "❌ Not found on TMDB!"); return
        markup = telebot.types.InlineKeyboardMarkup()
        for r in results: markup.add(telebot.types.InlineKeyboardButton(f"{r.get('title', 'N/A')} ({r.get('release_date', '')[:4]})", callback_data=f"tmdb_{r['id']}"))
        bot.send_message(user_id, "Select a movie:", reply_markup=markup)

    elif data.startswith("tmdb_"):
        tmdb_id = data.split('_')[1]
        details = get_tmdb_movie_details(tmdb_id)
        if not details.get('id'):
            bot.answer_callback_query(call.id, "❌ Error fetching details."); return
            
        genres = ", ".join([g['name'] for g in details.get('genres', [])])
        temp_data = {
            "title": details.get('title', 'Unknown'), 
            "description": details.get('overview', 'No description.'), 
            "rating": details.get('vote_average', 0),
            "release_date": details.get('release_date', 'N/A'),
            "genres": genres,
            "poster_url": f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}" if details.get('poster_path') else "",
            "backdrop_url": f"https://image.tmdb.org/t/p/w1280{details.get('backdrop_path')}" if details.get('backdrop_path') else ""
        }
        
        poster_path = details.get('poster_path')
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            msg = bot.send_photo(user_id, poster_url, caption=f"🎬 Selected: *{temp_data['title']}*\n\nNow send Screenshots (Album) or type `skip`:", parse_mode="Markdown")
            temp_data['poster_file_id'] = msg.photo[-1].file_id
        else:
            bot.send_message(user_id, "No poster found. Send Poster Image manually:")
            temp_data['poster_file_id'] = ""
        set_state(user_id, "add_mov_ss", temp_data)

    elif data.startswith("tmdbtv_"):
        tv_id = data.split('_')[1]
        details = get_tmdb_tv_details(tv_id)
        if not details.get('id'):
            bot.answer_callback_query(call.id, "❌ Error fetching details."); return
            
        temp_data = {"title": details.get('name', 'Unknown'), "description": details.get('overview', 'No description.')}
        poster_path = details.get('poster_path')
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            msg = bot.send_photo(user_id, poster_url, caption=f"📺 Selected: *{temp_data['title']}*\n\nSeries saved! Use /addepisode to add episodes.", parse_mode="Markdown")
            temp_data['poster_file_id'] = msg.photo[-1].file_id
        else: temp_data['poster_file_id'] = ""
        series_col.insert_one({"title": temp_data['title'], "poster_file_id": temp_data['poster_file_id'], "description": temp_data['description'], "episodes": [], "is_adult": False})
        clear_state(user_id)

    elif data.startswith("addsep_"):
        ser_id = data.split('_')[1]
        set_state(user_id, "add_ep_name", {"series_id": ser_id})
        bot.send_message(user_id, "📝 Send Episode Name (e.g. Episode 5):")

    # --- USER CALLBACKS ---
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
        file_type = "mov" if data.startswith('dl_mov_') else "ep"
        db_id = data.split('_')[2]
        
        if file_type == "mov":
            movie = movies_col.find_one({"_id": ObjectId(db_id)})
            if movie: is_adult = movie.get('is_adult', False)
        else:
            series = series_col.find_one({"_id": ObjectId(db_id)})
            if series: is_adult = series.get('is_adult', False)
            
        ad1 = ad_config['adult_ad1'] if is_adult else ad_config['normal_ad1']
        ad2 = ad_config['adult_ad2'] if is_adult else ad_config['normal_ad2']
        
        if not ad1 or not ad2:
            bot.send_message(user_id, "⚠️ Ads not configured by admin yet."); return
        
        # AD 1 Display
        wait_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        wait_btn.add(
            telebot.types.InlineKeyboardButton("🔗 Visit Ad Link 1", url=ad1),
            telebot.types.InlineKeyboardButton("⏳ Wait here...", callback_data="ignore")
        )
        ad_msg = bot.send_message(user_id, "⚠️ *Step 1:* Click the ad link below, wait 5 seconds, then come back.", parse_mode="Markdown", reply_markup=wait_btn)
            
        next_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        next_btn.add(telebot.types.InlineKeyboardButton("➡️ Go to Ad 2", callback_data=f"nextad_{file_type}_{db_id}"))
        threading.Thread(target=ad_timer, args=(user_id, ad_msg.message_id, next_btn)).start()

    elif data.startswith('nextad_'):
        # AD 2 Display
        file_type = data.split('_')[1]
        db_id = data.split('_')[2]
        
        ad_config = ads_col.find_one({})
        is_adult = False
        if file_type == "mov":
            movie = movies_col.find_one({"_id": ObjectId(db_id)})
            if movie: is_adult = movie.get('is_adult', False)
        else:
            series = series_col.find_one({"_id": ObjectId(db_id)})
            if series: is_adult = series.get('is_adult', False)
            
        ad2 = ad_config['adult_ad2'] if is_adult else ad_config['normal_ad2']
        
        wait_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        wait_btn.add(
            telebot.types.InlineKeyboardButton("🔗 Visit Ad Link 2", url=ad2),
            telebot.types.InlineKeyboardButton("⏳ Wait here...", callback_data="ignore")
        )
        ad_msg = bot.send_message(user_id, "⚠️ *Step 2:* Click the second ad link below, wait 5 seconds.", parse_mode="Markdown", reply_markup=wait_btn)
            
        final_btn = telebot.types.InlineKeyboardMarkup(row_width=1)
        final_btn.add(telebot.types.InlineKeyboardButton("✅ Get File", callback_data=f"finaldl_{file_type}_{db_id}"))
        threading.Thread(target=ad_timer, args=(user_id, ad_msg.message_id, final_btn)).start()

    elif data.startswith('finaldl_'):
        file_type = data.split('_')[1]
        db_id = data.split('_')[2]
        data_id = f"dl_{file_type}_{db_id}"
        deliver_file(user_id, data_id)
        
    elif data == 'ignore':
        bot.answer_callback_query(call.id, text="Please wait for the timer to finish...")

    elif data.startswith("copy_html_"):
        state = get_state(user_id)
        if state and state.get('temp_data', {}).get('html'):
            html_code = state['temp_data']['html']
            bot.send_message(user_id, f"👇 COPY THE HTML CODE BELOW 👇\n\n{html_code}")
            bot.answer_callback_query(call.id, "Code sent! Copy it from the message above.")
        else:
            bot.answer_callback_query(call.id, "Error: HTML code expired.")

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

# ==========================================
# ADMIN WORKFLOW STATE HANDLER
# ==========================================
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
            
            inserted_movie = movies_col.insert_one({
                "title": temp['title'], "poster_file_id": temp.get('poster_file_id', ''), 
                "screenshots": temp.get('screenshots', []), "movie_file_id": temp['movie_file_id'], 
                "description": temp.get('description', ''), "rating": temp.get('rating', 'N/A'), 
                "is_adult": False
            })
            
            html_code = generate_blogger_html(temp, inserted_movie.inserted_id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📋 Copy Blogger HTML", callback_data=f"copy_html_{inserted_movie.inserted_id}"))
            
            bot.reply_to(user_id, "✅ Movie Added Successfully!")
            bot.send_message(user_id, "🔥 *Blogger HTML Code Generated!*\n\nClick the button below to copy.", parse_mode="Markdown", reply_markup=markup)
            set_state(user_id, 'html_generated', {'html': html_code})

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
            if not message.text or not message.text.startswith('http'):
                bot.reply_to(user_id, "❌ Invalid link! Please send a valid Adsterra URL starting with http/https.")
                return
            ads_col.update_one({}, {"$set": {ad_key: message.text.strip()}}); clear_state(user_id)
            bot.reply_to(user_id, f"✅ Ad ({ad_key}) URL Saved Successfully!")

    except Exception as e: clear_state(user_id); bot.reply_to(user_id, f"❌ Error: {e}.")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🤖 Bot & Flask Server are running...")
    bot.infinity_polling()
