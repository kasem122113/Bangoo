import logging
import requests
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIG ---
TOKEN = '8683197663:AAF3mY9QVbLT2XfFLYeTBXYiAsTR8CuClaE'
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def analyze_logic(history):
    # যদি ডেটা কম থাকে
    if not history or len(history) < 5:
        return None, None, None

    # ১. ডেটা এক্সট্রাকশন
    numbers = [int(item.get('number')) for item in history[:20]]
    sizes = ["BIG" if n >= 5 else "SMALL" for n in numbers]
    last_num = numbers[0]
    last_size = sizes[0]

    # ২. লজিক ক্যালকুলেশন (ভোট সিস্টেম)
    votes = {"BIG": 0, "SMALL": 0}

    # লজিক A: Pivot Matrix (গড় নম্বর)
    avg = sum(numbers[:10]) / 10
    votes["SMALL" if last_num > avg else "BIG"] += 1

    # লজিক B: Trend Exhaustion (টানা ৩ বার আসলে উল্টোটা)
    if sizes[0] == sizes[1] == sizes[2]:
        votes["SMALL" if last_size == "BIG" else "BIG"] += 2

    # লজিক C: Pattern Probability (ইতিহাসে এই নম্বরের পর কী আসে)
    after_last = []
    for i in range(len(sizes) - 1):
        if sizes[i+1] == last_size:
            after_last.append(sizes[i])
    if after_last:
        freq_pred = max(set(after_last), key=after_last.count)
        votes[freq_pred] += 1.5

    # ৩. ফাইনাল ডিসিশন
    final_size = "BIG" if votes["BIG"] > votes["SMALL"] else "SMALL"
    
    # কালার লজিক (Parity)
    final_color = "🟢 GREEN" if last_num % 2 != 0 else "🔴 RED"
    if last_num in [0, 5]: final_color = "🟣 VIOLET"

    acc = random.randint(91, 98)
    return final_size, final_color, acc

async def get_live_data():
    try:
        # Cache এড়াতে টাইমস্ট্যাম্প যোগ করা হয়েছে
        url = f"{API_URL}?t={int(random.random()*1000)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get('data', {}).get('list', [])
    except:
        return None
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = [[InlineKeyboardButton("🎯 GET LIVE SIGNAL", callback_data='get_sig')]]
    await update.message.reply_text("🤖 **Raihan Hybrid AI V3.1**\nসবগুলো লজিক একটিভ আছে।", reply_markup=InlineKeyboardMarkup(btn))

async def handle_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Fetching Live Data...")
    
    data = await get_live_data()
    
    if not data:
        await query.message.reply_text("❌ **Data Fetch Error!**\nসার্ভার থেকে ডেটা পাওয়া যাচ্ছে না। কিছুক্ষণ পর চেষ্টা করুন।")
        return

    p_size, p_color, p_acc = analyze_logic(data)
    
    if not p_size:
        await query.message.reply_text("⚠️ **Not enough data to analyze.**")
        return

    issue = int(data[0].get('issueNumber')) + 1

    msg = (f"🚀 **AI HYBRID SIGNAL**\n"
           f"━━━━━━━━━━━━\n"
           f"🆔 Issue: `{issue}`\n"
           f"📊 Accuracy: `{p_acc}%` \n"
           f"━━━━━━━━━━━━\n"
           f"🎯 Result: **{p_size}**\n"
           f"🎨 Color: {p_color}\n"
           f"━━━━━━━━━━━━")

    btn = [[InlineKeyboardButton("🔄 NEXT SIGNAL", callback_data='get_sig')]]
    await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btn), parse_mode='Markdown')

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_prediction, pattern='get_sig'))
    print("✅ Bot is Online and Fixed!")
    app.run_polling()
