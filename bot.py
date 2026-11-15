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
BOT_TOKEN = "9076582647:AAFvcBQQSvFHxsFggkn8Chgji9qRiath_a4"
OWNER_ID = 8690715024
OWNER_USERNAME = "shopoflie"

CHANNELS_FILE = "channels.json"
ADMINS_FILE = "admins.json"
USERS_FILE = "users.json"

# Conversation states
(
    WAITING_FOR_CHANNEL_ID,
    WAITING_FOR_CHANNEL_LINK,
    WAITING_FOR_ADMIN_INPUT,
) = range(3)


# ================= DATABASE HELPERS =================
def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, "r") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def load_channels():
    return load_json(CHANNELS_FILE, [])


def save_channels(channels):
    save_json(CHANNELS_FILE, channels)


def load_admins():
    return load_json(ADMINS_FILE, [])


def save_admins(admins):
    save_json(ADMINS_FILE, admins)


def register_user(user):
    if not user:
        return
    users = load_json(USERS_FILE, {})
    users[str(user.id)] = {
        "id": user.id,
        "username": user.username.lower() if user.username else None,
        "name": user.first_name,
    }
    save_json(USERS_FILE, users)


def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    admins = load_admins()
    return any(a["id"] == user_id for a in admins)


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
            print(f"Error checking channel {ch['id']}: {e}")
            unjoined.append(ch)
    return unjoined


def build_force_join_markup(unjoined_channels):
    keyboard = []
    for idx, ch in enumerate(unjoined_channels, start=1):
        keyboard.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=ch["link"])])
    keyboard.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="check_join")])
    return InlineKeyboardMarkup(keyboard)


def build_admin_panel_markup(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📢 Force Join", callback_data="force_join_menu")],
    ]
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("👥 Admins", callback_data="admins_menu")])
    return InlineKeyboardMarkup(keyboard)


# ================= USER COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    if not is_admin(user.id):
        unjoined = await get_unjoined_channels(user.id, context)
        if unjoined:
            await update.message.reply_text(
                "⚠️ **Access Denied!**\n\n"
                "Bot use karne ke liye pehle niche diye gaye sabhi channels join karein.\n"
                "Join karne ke baad **✅ Joined / Verify** par click karein:",
                reply_markup=build_force_join_markup(unjoined),
                parse_mode="Markdown",
            )
            return ConversationHandler.END

    keyboard = []
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    await update.message.reply_text(
        f"👋 Welcome **{user.first_name}**!\n\nAapne sabhi required channels join kar liye hain. Bot ab ready hai!",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    register_user(user)

    unjoined = await get_unjoined_channels(user.id, context)
    if unjoined:
        await query.answer("❌ Aapne abhi tak saare channels join nahi kiye hain!", show_alert=True)
        try:
            await query.edit_message_reply_markup(reply_markup=build_force_join_markup(unjoined))
        except Exception:
            pass
        return

    await query.answer("✅ Verification Successful!", show_alert=False)
    keyboard = []
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    await query.edit_message_text(
        f"🎉 Thank you **{user.first_name}**!\n\nVerification complete ho gayi hai. Ab aap bot use kar sakte hain.",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode="Markdown",
    )


# ================= ADMIN PANEL =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    if not is_admin(user.id):
        await update.message.reply_text("⛔ Yeh command sirf Admins ke liye hai.")
        return ConversationHandler.END

    role = "Owner" if user.id == OWNER_ID else "Admin"
    await update.message.reply_text(
        f"🛠 **Admin Panel**\nRole: **{role}** | Owner: @{OWNER_USERNAME}",
        reply_markup=build_admin_panel_markup(user.id),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    if not is_admin(user.id):
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    await query.answer()
    role = "Owner" if user.id == OWNER_ID else "Admin"
    await query.edit_message_text(
        f"🛠 **Admin Panel**\nRole: **{role}** | Owner: @{OWNER_USERNAME}",
        reply_markup=build_admin_panel_markup(user.id),
        parse_mode="Markdown",
    )


# ================= ADMINS MANAGEMENT (OWNER ONLY) =================
async def admins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Sirf Owner hi admins manage kar sakta hai!", show_alert=True)
        return

    await query.answer()
    admins = load_admins()
    text = f"👥 **Bot Admins Management**\n\n👑 **Owner:** `{OWNER_ID}` (@{OWNER_USERNAME})\n\n"

    if not admins:
        text += "Abhi koi extra admin add nahi hai."
    else:
        text += f"**Added Admins ({len(admins)}):**\n"
        for idx, adm in enumerate(admins, start=1):
            uname = f"(@{adm['username']})" if adm.get("username") else ""
            text += f"{idx}. `{adm['id']}` {uname}\n"

    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin_btn")],
        [InlineKeyboardButton("🗑 Remove Admin", callback_data="remove_admin_list")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    await query.edit_message_text(
        "👤 **Naye Admin ka Chat ID ya `@username` bhejein:**\n\n"
        "• Example ID: `123456789`\n"
        "• Example Username: `@username`\n\n"
        "⚠️ *Note: Username se add karne ke liye zaroori hai ki us user ne bot ko pehle `/start` kiya ho.*\n"
        "Cancel karne ke liye `/cancel` bhejein.",
        parse_mode="Markdown",
    )
    return WAITING_FOR_ADMIN_INPUT


async def receive_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    raw_input = update.message.text.strip()
    target_id = None
    target_username = None

    if raw_input.lstrip("-").isdigit():
        target_id = int(raw_input)
        try:
            chat = await context.bot.get_chat(target_id)
            target_username = chat.username
        except Exception:
            pass
    else:
        clean_uname = raw_input.lstrip("@").lower()
        users = load_json(USERS_FILE, {})
        for uid_str, udata in users.items():
            if udata.get("username") == clean_uname:
                target_id = udata["id"]
                target_username = clean_uname
                break

        if not target_id:
            await update.message.reply_text(
                f"❌ `@{clean_uname}` nahi mila!\n\n"
                "Us user ne abhi tak bot ko `/start` nahi kiya hai. "
                "Unhe pehle bot start karne ko bolein, ya unka **numeric Chat ID** bhejein (ya `/cancel` karein):",
                parse_mode="Markdown",
            )
            return WAITING_FOR_ADMIN_INPUT

    if target_id == OWNER_ID:
        await update.message.reply_text("⚠️ Aap pehle se hi Bot Owner hain!")
        return ConversationHandler.END

    admins = load_admins()
    if any(a["id"] == target_id for a in admins):
        await update.message.reply_text("⚠️ Yeh user pehle se Admin hai!")
        return ConversationHandler.END

    admins.append({"id": target_id, "username": target_username})
    save_admins(admins)

    uname_display = f" (@{target_username})" if target_username else ""
    keyboard = [[InlineKeyboardButton("👥 Back to Admins", callback_data="admins_menu")]]
    await update.message.reply_text(
        f"✅ **New Admin Added!**\n\n"
        f"• **User:** `{target_id}`{uname_display}\n"
        f"Ab yeh user `/admin` command se bot manage kar sakta hai.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def remove_admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    admins = load_admins()
    if not admins:
        await query.answer("Remove karne ke liye koi admin nahi hai!", show_alert=True)
        return

    await query.answer()
    keyboard = []
    for idx, adm in enumerate(admins):
        label = f"@{adm['username']}" if adm.get("username") else str(adm["id"])
        keyboard.append(
            [InlineKeyboardButton(f"❌ Remove {label}", callback_data=f"del_adm_{idx}")]
        )
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admins_menu")])

    await query.edit_message_text(
        "🗑 **Jis Admin ko remove karna hai us par click karein:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def delete_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    idx = int(query.data.split("_")[-1])
    admins = load_admins()

    if 0 <= idx < len(admins):
        removed = admins.pop(idx)
        save_admins(admins)
        await query.answer(f"✅ Removed Admin {removed['id']}", show_alert=True)
    else:
        await query.answer("⚠️ Admin nahi mila!", show_alert=True)

    await admins_menu(update, context)


# ================= FORCE JOIN MANAGEMENT =================
async def force_join_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
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


async def start_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
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
    if not is_admin(update.effective_user.id):
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
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    link = update.message.text.strip()
    if not (link.startswith("https://t.me/") or link.startswith("http://t.me/")):
        await update.message.reply_text(
            "❌ Invalid Link! Link `https://t.me/...` se start hona chahiye. Dobara bhejein:"
        )
        return WAITING_FOR_CHANNEL_LINK

    chat_id = context.user_data.get("new_channel_id")
    channels = load_channels()

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


async def remove_channel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    channels = load_channels()
    if not channels:
        await query.answer("Remove karne ke liye koi channel nahi hai!", show_alert=True)
        return

    await query.answer()
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
    if not is_admin(query.from_user.id):
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

    await force_join_menu(update, context)


# ================= MAIN RUNNER =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

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
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start),
            CommandHandler("admin", admin_command),
        ],
    )

    add_admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_admin, pattern="^add_admin_btn$")],
        states={
            WAITING_FOR_ADMIN_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_input)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start),
            CommandHandler("admin", admin_command),
        ],
    )

    app.add_handler(add_channel_conv)
    app.add_handler(add_admin_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))

    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))

    app.add_handler(CallbackQueryHandler(force_join_menu, pattern="^force_join_menu$"))
    app.add_handler(CallbackQueryHandler(remove_channel_list, pattern="^remove_fj_list$"))
    app.add_handler(CallbackQueryHandler(delete_channel_callback, pattern="^del_ch_"))

    app.add_handler(CallbackQueryHandler(admins_menu, pattern="^admins_menu$"))
    app.add_handler(CallbackQueryHandler(remove_admin_list, pattern="^remove_admin_list$"))
    app.add_handler(CallbackQueryHandler(delete_admin_callback, pattern="^del_adm_"))

    print("Bot is running perfectly...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
    
