from fastapi import FastAPI
from pydantic import BaseModel
import subprocess, shlex
import os
import threading
import requests

app = FastAPI()

class Cmd(BaseModel):
    command: str

class Path(BaseModel):
    path: str

class WebRegister(BaseModel):
    url: str
    credentials: dict

@app.post("/open_url")
def open_url(p: Path):
    subprocess.Popen(shlex.split(f"xdg-open {p.path}"))
    return {"status": "ok", "action": "open_url", "path": p.path}

@app.post("/execute_command")
def execute_command(c: Cmd):
    cmd = c.command.lower()
    if "открой youtube" in cmd:
        return open_url(Path(path="https://www.youtube.com"))
    return {"status": "unknown command", "command": c.command}

@app.post("/web_register")
def web_register(w: WebRegister):
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    drv = webdriver.Chrome(options=opts)
    drv.get(w.url)
    for field, value in w.credentials.items():
        el = drv.find_element_by_name(field)
        el.send_keys(value)
    drv.find_element_by_css_selector("button[type=submit]").click()
    drv.quit()
    return {"status": "registered", "url": w.url}

def start_telegram_bot():
    from telegram import Update
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("No BOT_TOKEN provided, skipping Telegram Bot")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    def start_cmd(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Здравствуйте, Сер! Я Джарвес, ваш голосовой ассистент.")

    def handle_message(update: Update, context: CallbackContext):
        text = update.message.text
        try:
            resp = requests.post("http://localhost:8004/generate", json={"prompt": text})
            if resp.ok:
                data = resp.json()
                reply = data.get("response", "")
            else:
                reply = "Ошибка при запросе к ассистенту."
        except Exception as e:
            reply = f"Произошла ошибка: {e}"
        context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    t = threading.Thread(target=start_telegram_bot)
    t.daemon = True
    t.start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
