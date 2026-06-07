import os
import telebot
import requests
from pymongo import MongoClient

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
TMDB_API = os.getenv("TMDB_API")

bot = telebot.TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client["movieboxbd_db"]
states_collection = db["user_states"]

def get_state(user_id):
    return states_collection.find_one({"user_id": user_id})

def set_state(user_id, step, data=None):
    if data is None:
        data = {}
    states_collection.update_one(
        {"user_id": user_id},
        {"$set": {"step": step, "data": data}},
        upsert=True
    )

# TMDB থেকে মুভি খোঁজা
def search_tmdb(query, content_type='movie'):
    url = f"https://api.themoviedb.org/3/search/{content_type}"
    params = {"api_key": TMDB_API, "query": query, "language": "bn-BD"}
    try:
        res = requests.get(url, params=params).json()
        if res['results']:
            return res['results'][0] # প্রথম রেজাল্ট নিচ্ছে
    except:
        pass
    return None

# টেলিগ্রাম মেসেজ পার্সিং হেল্পার
def extract_text_and_links(text):
    lines = text.strip().split('\n')
    links = []
    name = lines[0]
    for line in lines[1:]:
        if line.strip():
            links.append(line.strip())
    return name, links

# ============ কমান্ডস ============
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎬 MovieBoxBD Ultra Generator Bot এ স্বাগতম!\n\nমুভি পোস্ট করতে `/movie` লিখুন\nওয়েব সিরিজ/এপিসোড পোস্ট করতে `/series` লিখুন।")
    set_state(message.chat.id, "idle")

# ============ মুভি মোড ============
@bot.message_handler(commands=['movie'])
def movie_mode(message):
    msg = bot.reply_to(message, "🎬 মুভি মোড অন!\n\nমুভির নাম লিখুন (যেমন: Inception):")
    bot.register_next_step_handler(msg, fetch_movie_data)

def fetch_movie_data(message):
    query = message.text.strip()
    bot.reply_to(message, "⏳ অপেক্ষা করুন, পোস্টার ও তথ্য খোঁজা হচ্ছে...")
    
    data = search_tmdb(query, 'movie')
    if not data:
        # বাংলায় না পাওয়া গেলে ইংরেজিতে খোঁজে
        data = search_tmdb(query, 'movie')
        
    state_data = {"type": "movie", "query": query}
    
    if data:
        poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else "https://via.placeholder.com/400x600"
        rating = data.get('vote_average', 'N/A')
        overview = data.get('overview', 'সারসংক্ষেপ পাওয়া যায়নি।')
        
        state_data["poster"] = poster
        state_data["rating"] = rating
        state_data["overview"] = overview
        
        # ৩টা স্ক্রিনশট (ব্যাকড্রপ) লিংক নিচ্ছে
        backdrops = data.get('backdrop_path')
        if backdrops:
            state_data["ss1"] = f"https://image.tmdb.org/t/p/w780{backdrops}"
            state_data["ss2"] = f"https://image.tmdb.org/t/p/w780{backdrops}" # একই ছবি ডেমো হিসেবে
            state_data["ss3"] = f"https://image.tmdb.org/t/p/w780{backdrops}"
        else:
            state_data["ss1"] = "https://via.placeholder.com/600x338"
            state_data["ss2"] = "https://via.placeholder.com/600x338"
            state_data["ss3"] = "https://via.placeholder.com/600x338"
            
        set_state(message.chat.id, "movie_details", state_data)
        msg = bot.reply_to(message, f"✅ পোস্টার ও তথ্য পাওয়া গেছে!\nরেটিং: {rating}\n\nএখন মুভির বাংলা টাইটেল, জেনার, সাইজ লিখুন:\n(যেমন: ইনসেপশন, সাই-ফাই/থ্রিলার, 1.2 GB)")
        bot.register_next_step_handler(msg, get_movie_dl_links)
    else:
        set_state(message.chat.id, "movie_manual", state_data)
        msg = bot.reply_to(message, "❌ ডেটাবেসে খুঁজে পাইনি। ম্যানুয়ালি তথ্য দিন:\nপোস্টার লিংক, রেটিং, জেনার, সাইজ লিখুন:")
        bot.register_next_step_handler(msg, get_movie_dl_links)

def get_movie_dl_links(message):
    details = message.text.strip()
    state = get_state(message.chat.id)
    data = state.get("data", {})
    data["details"] = details
    set_state(message.chat.id, "movie_links", data)
    msg = bot.reply_to(message, "📝 এখন ডাউনলোড লিংক দিন (কোয়ালিটি অনুযায়ী):\n\n480p_link\n720p_link\n1080p_link\n\n(প্রতিটি লাইনে একটা করে লিংক দিন)")
    bot.register_next_step_handler(msg, generate_movie_html)

def generate_movie_html(message):
    name, links = extract_text_and_links(message.text)
    state = get_state(message.chat.id)
    data = state.get("data", {})
    
    poster = data.get("poster", "https://via.placeholder.com/400x600")
    rating = data.get("rating", "N/A")
    overview = data.get("overview", "")
    details = data.get("details", "")
    ss1 = data.get("ss1", "https://via.placeholder.com/600x338")
    ss2 = data.get("ss2", "https://via.placeholder.com/600x338")
    ss3 = data.get("ss3", "https://via.placeholder.com/600x338")
    
    link_480 = links[0] if len(links) > 0 else "#"
    link_720 = links[1] if len(links) > 1 else "#"
    link_1080 = links[2] if len(links) > 2 else "#"

    html_code = f'''<!-- ========== মুভি পোস্ট শুরু ========== -->
<div class="movie-hero">
    <div class="poster-wrap">
        <img src="{poster}" alt="Movie Poster">
        <div class="poster-badge">HD</div>
        <div class="poster-rating"><i class="fas fa-star"></i> {rating}</div>
    </div>
    <div class="movie-info">
        <h1 class="movie-title">{details.split(",")[0].strip()}</h1>
        <div class="movie-meta">
            <span class="meta-tag green"><i class="fas fa-check-circle"></i> হাই কোয়ালিটি</span>
            <span class="meta-tag blue"><i class="fas fa-language"></i> বাংলা ডাব</span>
        </div>
        <p class="movie-synopsis">{overview}</p>
    </div>
</div>

<h2 class="section-title"><i class="fas fa-images"></i> স্ক্রিনশট</h2>
<div class="screenshots-grid">
    <div class="screenshot-item"><img src="{ss1}" alt="Screenshot 1"></div>
    <div class="screenshot-item"><img src="{ss2}" alt="Screenshot 2"></div>
    <div class="screenshot-item"><img src="{ss3}" alt="Screenshot 3"></div>
</div>

<h2 class="section-title"><i class="fas fa-download"></i> ডাউনলোড লিংক</h2>
<div class="download-section">
    <div class="quality-cards">
        <div class="quality-card">
            <div class="quality-left"><div class="quality-badge fhd">1080p</div><div class="quality-details"><h4>Full HD</h4></div></div>
            <button class="download-btn" onclick="startVerification('Movie-1080p', '{link_1080}')"><i class="fas fa-download"></i> ডাউনলোড</button>
        </div>
        <div class="quality-card">
            <div class="quality-left"><div class="quality-badge hd">720p</div><div class="quality-details"><h4>HD</h4></div></div>
            <button class="download-btn" onclick="startVerification('Movie-720p', '{link_720}')"><i class="fas fa-download"></i> ডাউনলোড</button>
        </div>
        <div class="quality-card">
            <div class="quality-left"><div class="quality-badge uhd">480p</div><div class="quality-details"><h4>SD</h4></div></div>
            <button class="download-btn" onclick="startVerification('Movie-480p', '{link_480}')"><i class="fas fa-download"></i> ডাউনলোড</button>
        </div>
    </div>
</div>
<!-- ========== মুভি পোস্ট শেষ ========== -->'''

    bot.reply_to(message, f"✅ **মুভি পোস্ট রেডি!**\n\nকোড কপি করে ওয়েবসাইটে পেস্ট করো:\n\n```html\n{html_code}\n```", parse_mode="Markdown")
    set_state(message.chat.id, "idle")


# ============ সিরিজ মোড ============
@bot.message_handler(commands=['series'])
def series_mode(message):
    msg = bot.reply_to(message, "📺 সিরিজ মোড অন!\n\nসিরিজের নাম লিখুন (যেমন: Squid Game):")
    bot.register_next_step_handler(msg, series_ask_episode)

def series_ask_episode(message):
    query = message.text.strip()
    bot.reply_to(message, "⏳ সিরিজের তথ্য খোঁজা হচ্ছে...")
    
    data = search_tmdb(query, 'tv')
    state_data = {"type": "series", "query": query}
    
    if data:
        poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else "https://via.placeholder.com/400x600"
        rating = data.get('vote_average', 'N/A')
        state_data["poster"] = poster
        state_data["rating"] = rating
        set_state(message.chat.id, "series_ep", state_data)
    else:
        set_state(message.chat.id, "series_ep", state_data)

    msg = bot.reply_to(message, "📝 এপিসোডের তথ্য দিন এভাবে:\n\nএপিসোড নম্বর\nএপিসোড নাম\nসাইজ ও ডিউরেশন\n480p_link\n720p_link\n1080p_link\n\n(যেমন:\n05\nমোড\n350 MB | 60 মিনিট\nhttps://link1.com\nhttps://link2.com\nhttps://link3.com)")
    bot.register_next_step_handler(msg, generate_series_html)

def generate_series_html(message):
    lines = message.text.strip().split('\n')
    if len(lines) < 6:
        bot.reply_to(message, "❌ সব তথ্য দেওয়া হয়নি! আবার `/series` চেষ্টা করুন।")
        set_state(message.chat.id, "idle")
        return

    ep_num = lines[0].strip()
    ep_name = lines[1].strip()
    ep_size = lines[2].strip()
    link_480 = lines[3].strip()
    link_720 = lines[4].strip()
    link_1080 = lines[5].strip()

    state = get_state(message.chat.id)
    data = state.get("data", {})
    
    # নতুন এপিসোড হলে NEW ব্যাজ, পুরনো হলে ব্যাজ থাকবে না
    is_new = "new-ep"
    new_badge = ' <span class="new-badge">NEW</span>'
    
    # যদি পুরনো এপিসোড হিসেবে অ্যাড করতে চাও, তবে উপরের দুটো ভ্যারিয়েবল এভাবে করবে:
    # is_new = ""
    # new_badge = ""

    html_code = f'''<!-- ▸ এপিসোড {ep_num} -->
<div class="episode-card {is_new}">
    <div class="episode-card-inner">
        <div class="ep-number">{ep_num}</div>
        <div class="ep-info">
            <h4>এপিসোড {ep_num} — {ep_name}{new_badge}</h4>
            <p><i class="fas fa-hdd"></i> {ep_size}</p>
        </div>
        <div class="ep-downloads">
            <button class="ep-dl-btn" onclick="startVerification('S01E{ep_num}-480p', '{link_480}')"><i class="fas fa-download"></i> 480p</button>
            <button class="ep-dl-btn" onclick="startVerification('S01E{ep_num}-720p', '{link_720}')"><i class="fas fa-download"></i> 720p</button>
            <button class="ep-dl-btn" onclick="startVerification('S01E{ep_num}-1080p', '{link_1080}')"><i class="fas fa-download"></i> 1080p</button>
        </div>
    </div>
</div>'''

    bot.reply_to(message, f"✅ **এপিসোড কোড রেডি!**\n\nএটা কপি করে `episode-grid` এর ভেতর পেস্ট করো:\n\n```html\n{html_code}\n```", parse_mode="Markdown")
    set_state(message.chat.id, "idle")

# বট চালু রাখা
if __name__ == '__main__':
    bot.infinity_polling()
