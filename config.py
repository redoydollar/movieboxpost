import os

# ======== Telegram API ========
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "") # @ ছাড়া লিখবেন

# ======== Admin ========
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# ======== Channels ========
# যেসব চ্যানেল বা গ্রুপ থেকে মুভি ইনডেক্স করতে চান, সেগুলোর আইডি (কমা দিয়ে দেবেন, -100 দিয়ে শুরু)
INDEX_CHANNELS = [int(x.strip()) for x in os.environ.get("INDEX_CHANNELS", "").split(",") if x.strip()]
# ফোর্স জয়েন চ্যানেল
FSUB_CHANNELS = [int(x.strip()) for x in os.environ.get("FSUB_CHANNELS", "").split(",") if x.strip()]
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/SakibMovieBox")

# ======== MongoDB ========
MONGODB_URI = os.environ.get("MONGODB_URI", "")
DB_NAME = os.environ.get("DB_NAME", "ctg_movie_bot")

# ======== Adsterra Direct Links ========
NORMAL_AD_1 = os.environ.get("NORMAL_AD_1", "https://www.effectivecpmnetwork.com/t0t62pprhs?key=1952b9f3548cd57e994e610fde24e41f")
NORMAL_AD_2 = os.environ.get("NORMAL_AD_2", "https://www.effectivecpmnetwork.com/ay5wm8biv?key=121d92bb75df4fb70c7ca614c6684fb9")
ADULT_AD_1 = os.environ.get("ADULT_AD_1", "https://www.effectivecpmnetwork.com/w6j7gscv?key=1b6df569ebc094e3e8e592d2fd017b4f")
ADULT_AD_2 = os.environ.get("ADULT_AD_2", "https://www.effectivecpmnetwork.com/d9b8fv4t?key=ef5b10414fe8fdd3f602e74bcdd4225c")

# ======== Web Server ========
BASE_URL = os.environ.get("BASE_URL", "")

# ======== সেটিংস ========
AUTO_DELETE_SECONDS = int(os.environ.get("AUTO_DELETE_SECONDS", "1800")) # 30 মিনিট
VERIFY_EXPIRE_SECONDS = int(os.environ.get("VERIFY_EXPIRE_SECONDS", "3600"))
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "6"))
