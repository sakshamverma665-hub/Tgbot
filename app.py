import logging
import requests
import json
from telegram import (
    Update, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# Bot details
BOT_TOKEN = "8323399462:AAEWgzQlGSMu3BEG88BIJO_EerL41wIXIXE"
ADMIN_ID = 6192055280
ADMIN_USERNAME = "@Saksham24_11"

# Logging
logging.basicConfig(level=logging.INFO)

# User storage
user_data = {}  # {user_id: {"credits": int, "unlimited": bool}}

# Stylish Keyboards
def get_main_keyboard(user_id):
    keyboard = [
        ["🚗 Vehicle Search", "📱 Phone Search"],
        ["💳 My Credits", "💰 Buy Credits"]
    ]
    if user_id == ADMIN_ID:
        keyboard.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

admin_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ Add Credits", "➖ Deduct Credits"],
        ["♾️ Add Unlimited", "❌ Remove Unlimited"],
        ["⬅ Back"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

SEARCHING, SEARCHING_PHONE, ADMIN_ACTION, ADMIN_USER, ADMIN_AMOUNT = range(5)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"credits": 3, "unlimited": False}
    await update.message.reply_text(
        f"👋 Welcome {update.effective_user.first_name}!\n\n"
        f"💳 Credits: {user_data[user_id]['credits']}\n"
        f"♾️ Unlimited: {user_data[user_id]['unlimited']}",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END

# Main Menu Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text in ["🚗 Vehicle Search", "Vehicle Search🔍"]:
        await update.message.reply_text("🚘 Please send vehicle number (e.g., MH01AB1234)")
        return SEARCHING

    elif text in ["📱 Phone Search", "Phone Search🔍"]:
        await update.message.reply_text("📱 Please send 10-digit phone number (without +91)")
        return SEARCHING_PHONE

    elif text in ["💳 My Credits", "My Credits"]:
        u = user_data.get(user_id, {"credits": 0, "unlimited": False})
        msg = f"💳 Credits: {u['credits']}\n♾️ Unlimited: {u['unlimited']}"
        await update.message.reply_text(msg)
        return ConversationHandler.END

    elif text in ["💰 Buy Credits", "Buy Credits"]:
        await update.message.reply_text(f"💰 To buy credits, contact admin: {ADMIN_USERNAME}")
        return ConversationHandler.END

    elif text == "⚙️ Admin Panel":
        if user_id == ADMIN_ID:
            await update.message.reply_text("⚙️ Admin Panel", reply_markup=admin_keyboard)
            return ADMIN_ACTION
        else:
            await update.message.reply_text("⛔ You are not authorized.")
            return ConversationHandler.END

    else:
        await update.message.reply_text("❌ Invalid option. Please use the menu.")
        return ConversationHandler.END

# Vehicle Search
async def search_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await perform_search(update, context, mode="vehicle")

# Phone Search
async def search_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await perform_search(update, context, mode="phone")

# Generic Search Function
async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, mode="vehicle"):
    user_id = update.effective_user.id
    query = update.message.text.strip()

    if user_id not in user_data:
        user_data[user_id] = {"credits": 0, "unlimited": False}

    if not user_data[user_id]["unlimited"] and user_data[user_id]["credits"] <= 0:
        await update.message.reply_text("❌ Not enough credits! Please buy credits.")
        return ConversationHandler.END

    if mode == "vehicle":
        api_url = f"https://rc-info-ng.vercel.app/?rc={query.upper()}"
        filename = f"{query.upper()}_info.txt"
    else:
        if not query.isdigit() or len(query) != 10:
            await update.message.reply_text("⚠️ Invalid phone number. Please enter 10 digits only.")
            return SEARCHING_PHONE
        phone_number = query
        api_url = f"https://sakshamxosintapi.onrender.com/get?num={phone_number}"
        filename = f"{phone_number}_info.txt"

    try:
        response = requests.get(api_url)
        data = response.json()
    except Exception:
        await update.message.reply_text("⚠️ Error fetching data.")
        return ConversationHandler.END

    if not user_data[user_id]["unlimited"]:
        user_data[user_id]["credits"] -= 1

    text_data = json.dumps(data, indent=4, ensure_ascii=False)

    cleaned_lines = []
    for line in text_data.splitlines():
        if "owner" in line.lower() and "@" in line:
            continue
        cleaned_lines.append(line)
    cleaned_lines.append(f'\n"Owner" : "{ADMIN_USERNAME}"')
    cleaned_text = "\n".join(cleaned_lines)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    context.user_data["last_file"] = filename

    keyboard = [[InlineKeyboardButton("📥 Download", callback_data="download_file")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Info fetched successfully:\n\n<pre>{cleaned_text}</pre>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

# Download Button Callback
async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filename = context.user_data.get("last_file")
    if filename:
        with open(filename, "rb") as f:
            await query.message.reply_document(f, caption="📥 Here is your file")

# Admin Actions
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["➕ Add Credits", "➖ Deduct Credits", "♾️ Add Unlimited", "❌ Remove Unlimited"]:
        context.user_data["action"] = text
        await update.message.reply_text("👤 Send User ID:")
        return ADMIN_USER
    elif text == "⬅ Back":
        await update.message.reply_text("↩️ Back to main menu", reply_markup=get_main_keyboard(ADMIN_ID))
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Invalid option.", reply_markup=admin_keyboard)
        return ADMIN_ACTION

async def admin_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Invalid User ID. Try again.")
        return ADMIN_USER

    if target_id not in user_data:
        user_data[target_id] = {"credits": 0, "unlimited": False}

    context.user_data["target_id"] = target_id
    action = context.user_data["action"]

    if action in ["➕ Add Credits", "➖ Deduct Credits"]:
        await update.message.reply_text("🔢 Enter amount:")
        return ADMIN_AMOUNT
    else:
        if action == "♾️ Add Unlimited":
            user_data[target_id]["unlimited"] = True
            msg = "✅ Unlimited Access Granted!"
        else:
            user_data[target_id]["unlimited"] = False
            msg = "❌ Unlimited Access Removed!"
        await update.message.reply_text(msg, reply_markup=admin_keyboard)
        return ADMIN_ACTION

async def admin_get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Invalid number. Try again.")
        return ADMIN_AMOUNT

    target_id = context.user_data["target_id"]
    action = context.user_data["action"]

    if action == "➕ Add Credits":
        user_data[target_id]["credits"] += amount
        msg = f"✅ Added {amount} credits to {target_id}"
    else:
        user_data[target_id]["credits"] = max(0, user_data[target_id]["credits"] - amount)
        msg = f"✅ Deducted {amount} credits from {target_id}"

    await update.message.reply_text(msg, reply_markup=admin_keyboard)
    return ADMIN_ACTION

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start),
                      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            SEARCHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_vehicle)],
            SEARCHING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_phone)],
            ADMIN_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_action)],
            ADMIN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_user)],
            ADMIN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_amount)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(download_callback, pattern="download_file"))

    app.run_polling()

if __name__ == "__main__":
    main()