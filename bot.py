# -*- coding: utf-8 -*-
import logging, asyncio, time, aiohttp, os, threading
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = '8683197663:AAF3mY9QVbLT2XfFLYeTBXYiAsTR8CuClaE'
# আপনার দেওয়া নতুন বেস লিঙ্ক
BASE_API = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

logging.basicConfig(level=logging.INFO)

def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Live")
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

class BotMemory:
    def __init__(self):
        self.total, self.wins, self.losses = 0, 0, 0
        self.last_id, self.current_bet = None, None

mem = BotMemory()
is_active = False

async def trading_loop(chat_id, context):
    global is_active
    # ব্রাউজার হেডার যা ক্লাউডফ্লেয়ার বাইপাস করতে সাহায্য করবে
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://hg-nice.com/',
        'Origin': 'https://hg-nice.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        while is_active:
            try:
                # আপনার দেওয়া ts ফরম্যাট (১৩ ডিজিট মিলিসেকেন্ড)
                ts = int(time.time() * 1000)
                full_url = f"{BASE_API}?ts={ts}"
                
                async with session.get(full_url, timeout=20) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(10); continue
                    
                    data = await resp.json()
                    # এপিআই রেসপন্স ফরম্যাট চেক (data -> list)
                    items = data.get('data', {}).get('list', [])
                    
                    if not items:
                        await asyncio.sleep(5); continue

                    curr_id = int(items[0].get('issueNumber'))
                    curr_num = int(items[0].get('number'))
                    curr_sz = "BIG" if curr_num >= 5 else "SMALL"

                    # অটো রেজাল্ট ট্র্যাকিং
                    if mem.last_id == curr_id:
                        if mem.current_bet:
                            mem.total += 1
                            res = "WIN ✅" if mem.current_bet == curr_sz else "LOSS ❌"
                            if res == "WIN ✅": mem.wins += 1; mem.losses = 0
                            else: mem.losses += 1
                            rate = (mem.wins/mem.total)*100
                            await context.bot.send_message(chat_id=chat_id, text=f"ID: {curr_id} | {curr_sz} | {res}\nWin Rate: {rate:.1f}%")
                        mem.last_id = None

                    # প্রেডিকশন (১০০ পিরিয়ড স্ট্যাটস এনালাইসিস)
                    nxt_id = curr_id + 1
                    if mem.last_id != nxt_id:
                        # গত ১০০ ড্র-এর বিগ/স্মল কাউন্ট
                        history_nums = [int(x.get('number')) for x in items[:100]]
                        big_count = sum(1 for n in history_nums if n >= 5)
                        
                        # আপনার ফেভারিট স্ট্যাটস লজিক
                        if big_count > 58: pred = "SMALL"
                        elif (100 - big_count) > 58: pred = "BIG"
                        else: pred = "BIG" if history_nums[0] < 5 else "SMALL"
                        
                        mem.current_bet, mem.last_id = pred, nxt_id
                        await context.bot.send_message(chat_id=chat_id, text=f"🔮 TARGET: {nxt_id}\n🎯 BET: {pred}")

            except Exception as e:
                logging.error(f"Sync Error: {e}")
            await asyncio.sleep(5)

async def start_cmd(u, c):
    kb = [[KeyboardButton("START"), KeyboardButton("STOP")]]
    await u.message.reply_text("🚀 ENGINE V38.0 PERFECTED", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_msg(u, c):
    global is_active
    if u.message.text == "START" and not is_active:
        is_active = True
        await u.message.reply_text("⚡ SYNCING WITH API... SCANNING HISTORY")
        asyncio.create_task(trading_loop(u.effective_chat.id, c))
    elif u.message.text == "STOP":
        is_active = False
        await u.message.reply_text("🛑 ENGINE OFFLINE")

if __name__ == '__main__':
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling()
