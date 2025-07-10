import os
import json
import time
import threading
import requests
from bs4 import BeautifulSoup
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

PREFS_FILE = "user_prefs.json"
PRODUCTS_FILE = "products.json"

def load_prefs():
    try:
        with open(PREFS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_prefs(prefs):
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f)

def add_keyword(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    keyword = " ".join(context.args).lower()
    prefs = load_prefs()
    user_keywords = prefs.get(user_id, [])
    if keyword and keyword not in user_keywords:
        user_keywords.append(keyword)
        prefs[user_id] = user_keywords
        save_prefs(prefs)
        update.message.reply_text(f"Keyword '{keyword}' added!")
    else:
        update.message.reply_text(f"Keyword '{keyword}' already in your list or invalid.")

def list_keywords(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    prefs = load_prefs()
    user_keywords = prefs.get(user_id, [])
    if user_keywords:
        update.message.reply_text("Your keywords:\n" + "\n".join(user_keywords))
    else:
        update.message.reply_text("You have no keywords yet.")

def remove_keyword(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    keyword = " ".join(context.args).lower()
    prefs = load_prefs()
    user_keywords = prefs.get(user_id, [])
    if keyword in user_keywords:
        user_keywords.remove(keyword)
        prefs[user_id] = user_keywords
        save_prefs(prefs)
        update.message.reply_text(f"Keyword '{keyword}' removed.")
    else:
        update.message.reply_text(f"Keyword '{keyword}' not found in your list.")

def scrape_amazon():
    url = "https://www.amazon.es/gp/bestsellers/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    products = []
    for item in soup.select(".zg-item-immersion")[:5]:
        title = item.select_one(".p13n-sc-truncate")
        link = item.select_one("a.a-link-normal")
        if title and link:
            products.append({
                "title": title.get_text(strip=True),
                "link": "https://www.amazon.es" + link["href"],
                "store": "Amazon"
            })
    return products

def load_products():
    try:
        with open(PRODUCTS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_products(products):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f)

def check_and_alert(bot: Bot):
    products = scrape_amazon()
    save_products(products)
    prefs = load_prefs()

    for user_id, keywords in prefs.items():
        for product in products:
            if any(kw.lower() in product["title"].lower() for kw in keywords):
                text = f"🔥 Oferta detectada en {product['store']}:\n{product['title']}\n{product['link']}"
                try:
                    bot.send_message(chat_id=user_id, text=text)
                except Exception as e:
                    print(f"Error enviando mensaje a {user_id}: {e}")

def alert_loop(bot: Bot):
    while True:
        check_and_alert(bot)
        time.sleep(600)

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN no está configurado")
        return

    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("add", add_keyword))
    dp.add_handler(CommandHandler("list", list_keywords))
    dp.add_handler(CommandHandler("remove", remove_keyword))

    updater.start_polling()
    print("Bot started")

    threading.Thread(target=alert_loop, args=(updater.bot,), daemon=True).start()

    updater.idle()

if __name__ == "__main__":
    main()