import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatMemberStatus

# ================= CONFIGURATION =================
BOT_TOKEN = "9076582647:AAHE7i7I1gRykaM5OO5mfUdzjQB4zL6ziek"  # Replace after revoking!
OWNER_ID = 8690715024
OWNER_USERNAME = "shopoflie"
DATA_FILE = "channels.json"

# Conversation states for adding a channel
WAITING_FOR_CHANNEL_ID, WAITING_FOR_CHANNEL_LINK = range(2)

# ================= DATABASE HELPERS =================
def load_channels():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_channels(channels):
    with open(DATA_FILE, "w") as f:
        json.dump(channels, f, indent=4)

# ================= FORCE JOIN CHECKER =================
async def get_unjoined_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    channels = load_channels()
    unjoined = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status not in [
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            ]:
                unjoined.append(ch)
        except Exception as e:
            # If bot is not admin in the channel or ID is invalid, print error in console
            print(f"Error checking channel {ch['id']}: {e}")
            unjoined.append(ch)
    return unjoined

def build_force_join_markup(unjoined_channels):
    keyboard = []
    for idx, ch in enumerate(unjoined_channels, start=1):
        keyboard.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=ch["link"])])
    keyboard.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="check_join")])
    return InlineKeyboardMarkup(keyboard)

# ================= USER COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    unjoined = await get_unjoined_channels(user.id, context)

    if unjoined:
        await update.message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "Bot use karne ke liye pehle niche diye gaye sabhi channels join karein.\n"
            "Join karne ke baad **✅ Joined / Verify** par click karein:",
            reply_markup=build_force_join_markup(unjoined),
            parse_mode="Markdown",
        )
        return

    # Welcome message after joining all channels
    keyboard = []
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    await update.message.reply_text(
        f"👋 Welcome **{user.first_name}**!\n\nAapne sabhi required channels join kar liye hain. Bot ab ready hai!",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode="Markdown",
    )

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    unjoined = await get_unjoined_channels(user.id, context)

    if unjoined:
        await query.answer("❌ Aapne abhi tak saare channels join nahi kiye hain!", show_alert=True)
        try:
            await query.edit_message_reply_markup(reply_markup=build_force_join_markup(unjoined))
        except Exception:
            pass  # Ignore error if message markup is identical
        return

    await query.answer("✅ Verification Successful!", show_alert=False)
    keyboard = []
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    await query.edit_message_text(
        f"🎉 Thank you **{user.first_name}**!\n\nVerification complete ho gayi hai. Ab aap bot use kar sakte hain.",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode="Markdown",
    )

# ================= ADMIN PANEL =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Yeh command sirf bot owner ke liye hai.")
        return

    keyboard = [
        [InlineKeyboardButton("📢 Force Join Settings", callback_data="force_join_menu")]
    ]
    await update.message.reply_text(
        f"🛠 **Admin Panel**\nOwner: @{OWNER_USERNAME}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📢 Force Join Settings", callback_data="force_join_menu")]
    ]
    await query.edit_message_text(
        f"🛠 **Admin Panel**\nOwner: @{OWNER_USERNAME}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

async def force_join_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    await query.answer()
    channels = load_channels()
    text = "📢 **Force Join Management**\n\n"
    if not channels:
        text += "Abhi koi bhi channel add nahi hai."
    else:
        text += f"Total Active Channels: **{len(channels)}**\n"
        for idx, ch in enumerate(channels, start=1):
            text += f"{idx}. ID: `{ch['id']}` | [Link]({ch['link']})\n"

    keyboard = [
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_fj_channel")],
        [InlineKeyboardButton("🗑 Remove Channel", callback_data="remove_fj_list")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

# ================= ADD CHANNEL FLOW =================
async def start_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    await query.edit_message_text(
        "1️⃣ **Channel ka Chat ID bhejein:**\n"
        "*(Example: `-1001234567890`)*\n\n"
        "⚠️ Note: Bot us channel mein Admin hona zaroori hai.\n"
        "Cancel karne ke liye `/cancel` bhejein.",
        parse_mode="Markdown",
    )
    return WAITING_FOR_CHANNEL_ID

async def receive_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    chat_id_text = update.message.text.strip()
    try:
        chat_id = int(chat_id_text)
    except ValueError:
        await update.message.reply_text(
            "❌ Galat Chat ID! Kripya valid numeric ID bhejein (e.g., `-1001234567890`).",
            parse_mode="Markdown",
        )
        return WAITING_FOR_CHANNEL_ID

    context.user_data["new_channel_id"] = chat_id
    await update.message.reply_text(
        "2️⃣ **Ab us channel ka Invite Link bhejein:**\n"
        "*(Example: `https://t.me/yourchannel` ya private invite link)*",
        parse_mode="Markdown",
    )
    return WAITING_FOR_CHANNEL_LINK

async def receive_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    link = update.message.text.strip()
    if not (link.startswith("https://t.me/") or link.startswith("http://t.me/")):
        await update.message.reply_text(
            "❌ Invalid Link! Link `https://t.me/...` se start hona chahiye. Dobara bhejein:"
        )
        return WAITING_FOR_CHANNEL_LINK

    chat_id = context.user_data.get("new_channel_id")
    channels = load_channels()

    # Check if already exists
    if any(ch["id"] == chat_id for ch in channels):
        await update.message.reply_text("⚠️ Yeh channel pehle se Force Join list mein added hai!")
        return ConversationHandler.END

    channels.append({"id": chat_id, "link": link})
    save_channels(channels)

    keyboard = [[InlineKeyboardButton("📢 Back to Force Join", callback_data="force_join_menu")]]
    await update.message.reply_text(
        f"✅ **Channel Successfully Added!**\n\n"
        f"• **ID:** `{chat_id}`\n"
        f"• **Link:** {link}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Process cancel kar diya gaya hai.")
    return ConversationHandler.END

# ================= REMOVE CHANNEL FLOW =================
async def remove_channel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    await query.answer()
    channels = load_channels()
    if not channels:
        await query.answer("Remove karne ke liye koi channel nahi hai!", show_alert=True)
        return

    keyboard = []
    for idx, ch in enumerate(channels):
        keyboard.append(
            [InlineKeyboardButton(f"❌ Remove {ch['id']}", callback_data=f"del_ch_{idx}")]
        )
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="force_join_menu")])

    await query.edit_message_text(
        "🗑 **Jis channel ko remove karna hai us par click karein:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

async def delete_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    idx = int(query.data.split("_")[-1])
    channels = load_channels()

    if 0 <= idx < len(channels):
        removed = channels.pop(idx)
        save_channels(channels)
        await query.answer(f"✅ Removed {removed['id']}", show_alert=True)
    else:
        await query.answer("⚠️ Channel nahi mila!", show_alert=True)

    # Refresh the Force Join menu
    await force_join_menu(update, context)

# ================= MAIN RUNNER =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for adding a force join channel
    add_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_channel, pattern="^add_fj_channel$")],
        states={
            WAITING_FOR_CHANNEL_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_id)
            ],
            WAITING_FOR_CHANNEL_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_link)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(add_channel_conv)

    # Callback query handlers
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(force_join_menu, pattern="^force_join_menu$"))
    app.add_handler(CallbackQueryHandler(remove_channel_list, pattern="^remove_fj_list$"))
    app.add_handler(CallbackQueryHandler(delete_channel_callback, pattern="^del_ch_"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
