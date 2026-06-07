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

def set_state(user_id, step, data=None):
    if data is None: data = {}
    states_collection.update_one(
        {"user_id": user_id},
        {"$set": {"step": step, "data": data}},
        upsert=True
    )

# TMDB থেকে মুভি/সিরিজ খোঁজা
def search_tmdb(query, content_type='movie'):
    url = f"https://api.themoviedb.org/3/search/{content_type}"
    params = {"api_key": TMDB_API, "query": query}
    try:
        res = requests.get(url, params=params).json()
        if res['results']: return res['results'][0]
    except: pass
    return None

# ============ পেজের মূল টেমপ্লেট (ভেরিফিকেশন + ২ অ্যাড + JS সহ) ============
def get_full_html(content_html):
    return """<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MovieBoxBD</title>
    <link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Hind Siliguri', sans-serif; background: #0a0a0f; color: #e0e0e0; }
        .movie-container { max-width: 1200px; margin: 0 auto; padding: 24px 16px 60px; }
        .movie-hero { display: grid; grid-template-columns: 280px 1fr; gap: 30px; background: linear-gradient(145deg, #12121c, #1a1a2e); border-radius: 16px; padding: 24px; border: 1px solid rgba(229,9,20,0.1); position: relative; overflow: hidden; }
        .movie-hero::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #e50914, #ff6b35, #e50914); }
        .poster-wrap { position: relative; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 30px rgba(0,0,0,0.5); aspect-ratio: 2/3; }
        .poster-wrap img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .poster-badge { position: absolute; top: 12px; left: 12px; background: linear-gradient(135deg, #e50914, #ff3030); color: #fff; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; }
        .poster-rating { position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.85); color: #ffd700; padding: 6px 12px; border-radius: 8px; font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 5px; }
        .movie-info { display: flex; flex-direction: column; gap: 14px; }
        .movie-title { font-size: 28px; font-weight: 700; color: #fff; }
        .movie-meta { display: flex; flex-wrap: wrap; gap: 8px; }
        .meta-tag { background: rgba(229,9,20,0.1); border: 1px solid rgba(229,9,20,0.2); color: #ff6b6b; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .meta-tag.green { background: rgba(76,175,80,0.1); border-color: rgba(76,175,80,0.2); color: #66bb6a; }
        .movie-synopsis { font-size: 14px; line-height: 1.8; color: #999; border-left: 3px solid #e50914; padding-left: 16px; }
        .section-title { font-size: 20px; font-weight: 700; color: #fff; margin: 40px 0 16px; display: flex; align-items: center; gap: 10px; }
        .section-title i { color: #e50914; }
        .screenshots-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
        .screenshot-item { border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); }
        .screenshot-item img { width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; }
        .download-section { margin-top: 40px; background: linear-gradient(145deg, #12121c, #1a1a2e); border-radius: 16px; padding: 28px; border: 1px solid rgba(229,9,20,0.1); position: relative; overflow: hidden; }
        .download-section::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #e50914, #ff6b35, #e50914); }
        .download-btn { background: linear-gradient(135deg, #e50914, #ff3030); color: #fff; border: none; padding: 16px; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; transition: all 0.3s; font-family: 'Hind Siliguri', sans-serif; width: 100%; box-shadow: 0 4px 15px rgba(229,9,20,0.3); }
        .download-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(229,9,20,0.5); }
        
        /* Episode CSS */
        .episode-section { margin-top: 40px; background: linear-gradient(145deg, #12121c, #1a1a2e); border-radius: 16px; padding: 28px; border: 1px solid rgba(229,9,20,0.1); }
        .episode-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
        .episode-card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; overflow: hidden; transition: all 0.3s; }
        .episode-card.new-ep { border-color: rgba(76,175,80,0.3); }
        .episode-card.new-ep .ep-number { background: linear-gradient(135deg, #4caf50, #2e7d32); }
        .episode-card-inner { display: flex; align-items: center; padding: 14px 16px; gap: 14px; }
        .ep-number { width: 48px; height: 48px; min-width: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 800; color: #fff; background: linear-gradient(135deg, #e50914, #ff3030); }
        .ep-info { flex: 1; min-width: 0; }
        .ep-info h4 { font-size: 15px; font-weight: 600; color: #fff; }
        .new-badge { background: linear-gradient(135deg, #4caf50, #2e7d32); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; animation: newPulse 2s infinite; }
        @keyframes newPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
        .ep-downloads { display: flex; gap: 8px; flex-shrink: 0; }
        .ep-dl-btn { background: linear-gradient(135deg, #e50914, #ff3030); border: none; color: #fff; padding: 10px 22px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.3s; font-family: 'Hind Siliguri', sans-serif; display: flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(229,9,20,0.2); }
        .ep-dl-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(229,9,20,0.4); }

        /* Verification Modal CSS */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.88); backdrop-filter: blur(8px); z-index: 9999; align-items: center; justify-content: center; padding: 20px; }
        .modal-overlay.active { display: flex; }
        .modal-box { background: linear-gradient(145deg, #15151f, #1e1e32); border-radius: 20px; width: 100%; max-width: 480px; border: 1px solid rgba(229,9,20,0.15); overflow: hidden; }
        .modal-header { background: linear-gradient(135deg, #e50914, #ff3030); padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
        .modal-header h3 { color: #fff; font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
        .modal-close { background: rgba(255,255,255,0.2); border: none; color: #fff; width: 30px; height: 30px; border-radius: 8px; cursor: pointer; font-size: 13px; display: flex; align-items: center; justify-content: center; }
        .modal-body { padding: 24px; }
        .step-indicator { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 20px; }
        .step-dot { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; border: 2px solid rgba(255,255,255,0.1); color: #555; transition: all 0.3s; }
        .step-dot.active { border-color: #e50914; color: #e50914; background: rgba(229,9,20,0.1); }
        .step-dot.completed { border-color: #4caf50; color: #fff; background: #4caf50; }
        .step-line { width: 35px; height: 2px; background: rgba(255,255,255,0.1); }
        .step-line.completed { background: #4caf50; }
        .verification-message { text-align: center; margin-bottom: 16px; }
        .verification-message h4 { font-size: 17px; color: #fff; margin-bottom: 6px; }
        .verification-message p { font-size: 13px; color: #888; }
        .ad-container { background: rgba(0,0,0,0.3); border: 2px dashed rgba(229,9,20,0.2); border-radius: 12px; min-height: 100px; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; overflow: hidden; }
        .timer-section { text-align: center; }
        .timer-bar { width: 100%; height: 5px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 10px; }
        .timer-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #e50914, #ff6b35); border-radius: 3px; transition: width 0.1s linear; }
        .timer-text { font-size: 14px; color: #aaa; font-weight: 500; }
        .timer-text span { color: #e50914; font-weight: 700; font-size: 18px; }
        .unlock-btn { display: none; width: 100%; padding: 13px; background: linear-gradient(135deg, #4caf50, #2e7d32); color: #fff; border: none; border-radius: 12px; font-size: 15px; font-weight: 700; cursor: pointer; font-family: 'Hind Siliguri', sans-serif; margin-top: 14px; box-shadow: 0 4px 20px rgba(76,175,80,0.3); }
        .unlock-btn:hover { transform: translateY(-2px); }
        .success-state { text-align: center; padding: 16px 0; }
        .success-icon { width: 64px; height: 64px; background: linear-gradient(135deg, #4caf50, #2e7d32); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; font-size: 28px; color: #fff; animation: successPop 0.5s ease-out; }
        @keyframes successPop { 0% { transform: scale(0); } 50% { transform: scale(1.2); } 100% { transform: scale(1); } }
        .success-state h3 { font-size: 18px; color: #fff; margin-bottom: 18px; }
        .final-download-btn { display: inline-flex; align-items: center; gap: 8px; padding: 13px 36px; background: linear-gradient(135deg, #e50914, #ff3030); color: #fff; text-decoration: none; border-radius: 12px; font-size: 15px; font-weight: 700; font-family: 'Hind Siliguri', sans-serif; box-shadow: 0 4px 20px rgba(229,9,20,0.4); }
        .final-download-btn:hover { transform: translateY(-2px); }
        
        @media (max-width: 768px) { .movie-hero { grid-template-columns: 1fr; } .poster-wrap { max-width: 200px; margin: 0 auto; } .screenshots-grid { grid-template-columns: 1fr; } .episode-card-inner { flex-wrap: wrap; } .ep-downloads { width: 100%; } .ep-dl-btn { flex: 1; justify-content: center; } }
    </style>
</head>
<body>

<div class="movie-container">
    """ + content_html + """
</div>

<!-- ============ VERIFICATION MODAL (2 Ads + 2 Steps) ============ -->
<div class="modal-overlay" id="verificationModal">
    <div class="modal-box">
        <div class="modal-header">
            <h3><i class="fas fa-shield-alt"></i> ভেরিফিকেশন</h3>
            <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
            <div class="step-indicator">
                <div class="step-dot active" id="step1Dot">1</div>
                <div class="step-line" id="step1Line"></div>
                <div class="step-dot" id="step2Dot">2</div>
                <div class="step-line" id="step2Line"></div>
                <div class="step-dot" id="step3Dot"><i class="fas fa-check" style="font-size:11px"></i></div>
            </div>
            <div id="stepContent">
                <!-- STEP 1 -->
                <div id="step1Content">
                    <div class="verification-message"><h4>ধাপ ১: ভেরিফিকেশন</h4><p>অনুগ্রহ করে ৫ সেকেন্ড অপেক্ষা করুন</p></div>
                    
                    <!-- ========== AD 1 START ========== -->
                    <div class="ad-container" id="adContainer1">
                        <!-- তোমার প্রথম অ্যাড কোড এখানে বসাও -->
                    </div>
                    <!-- ========== AD 1 END ========== -->
                    
                    <div class="timer-section" id="timer1Section">
                        <div class="timer-bar"><div class="timer-fill" id="timer1Fill"></div></div>
                        <p class="timer-text">অপেক্ষা করুন... <span id="timer1Count">5</span> সেকেন্ড</p>
                    </div>
                    <button class="unlock-btn" id="step1Unlock" onclick="goToStep2()"><i class="fas fa-arrow-right"></i> পরবর্তী ধাপে যান</button>
                </div>
                <!-- STEP 2 -->
                <div id="step2Content" style="display:none">
                    <div class="verification-message"><h4>ধাপ ২: চূড়ান্ত ভেরিফিকেশন</h4><p>আরো ৫ সেকেন্ড অপেক্ষা করুন</p></div>
                    
                    <!-- ========== AD 2 START ========== -->
                    <div class="ad-container" id="adContainer2">
                        <!-- তোমার দ্বিতীয় অ্যাড কোড এখানে বসাও -->
                    </div>
                    <!-- ========== AD 2 END ========== -->
                    
                    <div class="timer-section" id="timer2Section">
                        <div class="timer-bar"><div class="timer-fill" id="timer2Fill"></div></div>
                        <p class="timer-text">অপেক্ষা করুন... <span id="timer2Count">5</span> সেকেন্ড</p>
                    </div>
                    <button class="unlock-btn" id="step2Unlock" onclick="goToStep3()"><i class="fas fa-unlock"></i> ডাউনলোড আনলক করুন</button>
                </div>
                <!-- STEP 3 -->
                <div id="step3Content" style="display:none">
                    <div class="success-state">
                        <div class="success-icon"><i class="fas fa-check"></i></div>
                        <h3>ডাউনলোড রেডি!</h3>
                        <a href="#" class="final-download-btn" id="finalDownloadBtn" target="_blank"><i class="fas fa-download"></i> সরাসরি ডাউনলোড</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    let currentLink = ''; let timer1Interval = null; let timer2Interval = null;
    function startVerification(id, link) { currentLink = link; resetModal(); document.getElementById('verificationModal').classList.add('active'); document.body.style.overflow = 'hidden'; startTimer1(); }
    function resetModal() { if(timer1Interval) clearInterval(timer1Interval); if(timer2Interval) clearInterval(timer2Interval); document.getElementById('step1Dot').className='step-dot active'; document.getElementById('step2Dot').className='step-dot'; document.getElementById('step3Dot').className='step-dot'; document.getElementById('step1Line').className='step-line'; document.getElementById('step2Line').className='step-line'; document.getElementById('step1Content').style.display='block'; document.getElementById('step2Content').style.display='none'; document.getElementById('step3Content').style.display='none'; document.getElementById('timer1Fill').style.width='0%'; document.getElementById('timer1Count').textContent='5'; document.getElementById('timer1Section').style.display='block'; document.getElementById('step1Unlock').style.display='none'; document.getElementById('timer2Fill').style.width='0%'; document.getElementById('timer2Count').textContent='5'; document.getElementById('timer2Section').style.display='block'; document.getElementById('step2Unlock').style.display='none'; }
    function startTimer1() { let t=5; timer1Interval=setInterval(()=>{t--; document.getElementById('timer1Count').textContent=t; document.getElementById('timer1Fill').style.width=((5-t)/5*100)+'%'; if(t<=0){clearInterval(timer1Interval); document.getElementById('timer1Section').style.display='none'; document.getElementById('step1Unlock').style.display='block';}},1000); }
    function goToStep2() { document.getElementById('step1Dot').className='step-dot completed'; document.getElementById('step1Line').className='step-line completed'; document.getElementById('step2Dot').className='step-dot active'; document.getElementById('step1Content').style.display='none'; document.getElementById('step2Content').style.display='block'; startTimer2(); }
    function startTimer2() { let t=5; timer2Interval=setInterval(()=>{t--; document.getElementById('timer2Count').textContent=t; document.getElementById('timer2Fill').style.width=((5-t)/5*100)+'%'; if(t<=0){clearInterval(timer2Interval); document.getElementById('timer2Section').style.display='none'; document.getElementById('step2Unlock').style.display='block';}},1000); }
    function goToStep3() { document.getElementById('step2Dot').className='step-dot completed'; document.getElementById('step2Line').className='step-line completed'; document.getElementById('step3Dot').className='step-dot completed'; document.getElementById('step2Content').style.display='none'; document.getElementById('step3Content').style.display='block'; document.getElementById('finalDownloadBtn').href=currentLink; }
    function closeModal() { document.getElementById('verificationModal').classList.remove('active'); document.body.style.overflow=''; if(timer1Interval)clearInterval(timer1Interval); if(timer2Interval)clearInterval(timer2Interval); }
    document.getElementById('verificationModal').addEventListener('click',function(e){if(e.target===this)closeModal();});
</script>
</body>
</html>"""


# ============ কমান্ডস ============
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎬 MovieBoxBD Bot এ স্বাগতম!\n\nমুভি পোস্ট করতে `/movie` লিখুন\nওয়েব সিরিজ/এপিসোড পোস্ট করতে `/series` লিখুন।")

# ============ মুভি মোড ============
@bot.message_handler(commands=['movie'])
def movie_mode(message):
    msg = bot.reply_to(message, "🎬 মুভির নাম লিখুন (যেমন: Inception):")
    bot.register_next_step_handler(msg, get_movie_link)

def get_movie_link(message):
    query = message.text.strip()
    bot.reply_to(message, "⏳ পোস্টার খোঁজা হচ্ছে...")
    
    data = search_tmdb(query, 'movie')
    state_data = {"query": query}
    
    if data:
        poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else ""
        rating = data.get('vote_average', 'N/A')
        overview = data.get('overview', '')
        backdrop = f"https://image.tmdb.org/t/p/w780{data.get('backdrop_path')}" if data.get('backdrop_path') else ""
        
        state_data["poster"] = poster
        state_data["rating"] = rating
        state_data["overview"] = overview
        state_data["ss1"] = backdrop
    
    set_state(message.chat.id, "movie_link", state_data)
    msg = bot.reply_to(message, "📝 এখন শুধু ডাউনলোড লিংকটা দিন:")
    bot.register_next_step_handler(msg, generate_movie_html)

def generate_movie_html(message):
    link = message.text.strip()
    state = states_collection.find_one({"user_id": message.chat.id})
    data = state.get("data", {})
    
    poster = data.get("poster", "https://via.placeholder.com/400x600")
    rating = data.get("rating", "N/A")
    overview = data.get("overview", "")
    ss1 = data.get("ss1", "https://via.placeholder.com/600x338")
    query = data.get("query", "Movie")

    content = f"""<div class="movie-hero">
        <div class="poster-wrap">
            <img src="{poster}" alt="Poster">
            <div class="poster-badge">HD</div>
            <div class="poster-rating"><i class="fas fa-star"></i> {rating}</div>
        </div>
        <div class="movie-info">
            <h1 class="movie-title">{query}</h1>
            <div class="movie-meta">
                <span class="meta-tag green"><i class="fas fa-check-circle"></i> হাই কোয়ালিটি</span>
            </div>
            <p class="movie-synopsis">{overview}</p>
        </div>
    </div>

    <h2 class="section-title"><i class="fas fa-images"></i> স্ক্রিনশট</h2>
    <div class="screenshots-grid">
        <div class="screenshot-item"><img src="{ss1}" alt="Screenshot"></div>
    </div>

    <h2 class="section-title"><i class="fas fa-download"></i> ডাউনলোড</h2>
    <div class="download-section">
        <button class="download-btn" onclick="startVerification('movie-download', '{link}')">
            <i class="fas fa-download"></i> ডাউনলোড করুন
        </button>
    </div>"""

    final_html = get_full_html(content)
    bot.reply_to(message, f"✅ **মুভি পোস্ট রেডি!**\n(ভেরিফিকেশন + ২ অ্যাড সহ পুরো কোড)\n\n```html\n{final_html}\n```", parse_mode="Markdown")


# ============ সিরিজ মোড ============
@bot.message_handler(commands=['series'])
def series_mode(message):
    msg = bot.reply_to(message, "📺 এপিসোডের তথ্য দিন এভাবে:\n\nএপিসোড নম্বর\nএপিসোড নাম\nডাউনলোড লিংক\n\n(যেমন:\n05\nমোড\nhttps://your-link.com/file.mkv)")
    bot.register_next_step_handler(msg, generate_series_html)

def generate_series_html(message):
    lines = message.text.strip().split('\n')
    if len(lines) < 3:
        bot.reply_to(message, "❌ সব তথ্য দেওয়া হয়নি! আবার `/series` চেষ্টা করুন।")
        return

    ep_num = lines[0].strip()
    ep_name = lines[1].strip()
    link = lines[2].strip()

    # সিরিজের জন্য পুরো পেজের কোড বানাচ্ছে (যাতে ভেরিফিকেশন থাকে)
    content = f"""<div class="episode-section">
        <h2 class="section-title" style="margin-top:0;"><i class="fas fa-tv"></i> এপিসোড লিস্ট</h2>
        <div class="episode-grid">
            <div class="episode-card new-ep">
                <div class="episode-card-inner">
                    <div class="ep-number">{ep_num}</div>
                    <div class="ep-info">
                        <h4>এপিসোড {ep_num} — {ep_name} <span class="new-badge">NEW</span></h4>
                    </div>
                    <div class="ep-downloads">
                        <button class="ep-dl-btn" onclick="startVerification('S01E{ep_num}', '{link}')">
                            <i class="fas fa-download"></i> ডাউনলোড
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>"""

    final_html = get_full_html(content)
    bot.reply_to(message, f"✅ **এপিসোড কোড রেডি!**\n(ভেরিফিকেশন + ২ অ্যাড সহ পুরো কোড)\n\n```html\n{final_html}\n```", parse_mode="Markdown")


# বট চালু রাখা
if __name__ == '__main__':
    bot.infinity_polling()
