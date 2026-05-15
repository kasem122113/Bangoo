# -*- coding: utf-8 -*-
import logging, asyncio, time, aiohttp, os, threading, requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = '8683197663:AAF3mY9QVbLT2XfFLYeTBXYiAsTR8CuClaE'
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

logging.basicConfig(level=logging.INFO)

# Render dummy server to keep bot alive
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running")
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

class BotMemory:
    def __init__(self):
        self.total, self.wins, self.losses = 0, 0, 0
        self.last_id, self.current_bet = None, None

mem = BotMemory()
is_active = False

def get_prediction(items):
    if not items or len(items) < 20: return "WAIT"
    nums = [int(x.get('number')) for x in items[:100]]
    big_cnt = sum(1 for n in nums if n >= 5)
    if big_cnt > 58: return "SMALL"
    if (100 - big_cnt) > 58: return "BIG"
    return "BIG" if nums[0] < 5 else "SMALL"

async def trading_loop(chat_id, context):
    global is_active
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while is_active:
            try:
                ts = int(time.time() * 1000)
                async with session.get(f"{API_URL}?pageSize=100&t={ts}", timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get('data', {}).get('list', [])
                        if items:
                            curr_id = int(items[0].get('issueNumber'))
                            curr_sz = "BIG" if int(items[0].get('number')) >= 5 else "SMALL"
                            
                            if mem.last_id == curr_id:
                                if mem.current_bet:
                                    mem.total += 1
                                    res = "WIN ✅" if mem.current_bet == curr_sz else "LOSS ❌"
                                    if res == "WIN ✅": mem.wins += 1; mem.losses = 0
                                    else: mem.losses += 1
                                    rate = (mem.wins/mem.total)*100 if mem.total > 0 else 0
                                    await context.bot.send_message(chat_id=chat_id, text=f"ID: {curr_id} | {curr_sz} | {res}\nWin Rate: {rate:.1f}%")
                                mem.last_id = None

                            nxt_id = curr_id + 1
                            if mem.last_id != nxt_id:
                                pred = get_prediction(items)
                                mem.current_bet, mem.last_id = pred, nxt_id
                                await context.bot.send_message(chat_id=chat_id, text=f"🔮 TARGET: {nxt_id}\n🎯 BET: {pred}")
            except Exception as e:
                logging.error(f"Loop Error: {e}")
            await asyncio.sleep(5)

async def start_cmd(u, c):
    kb = [[KeyboardButton("START"), KeyboardButton("STOP")]]
    await u.message.reply_text("🚀 ENGINE V35.0 READY", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_msg(u, c):
    global is_active
    if u.message.text == "START" and not is_active:
        is_active = True
        await u.message.reply_text("⚡ ENGINE ACTIVE... SCANNING DATA")
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
  
