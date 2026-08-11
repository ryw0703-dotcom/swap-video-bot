import os
import re
import json
import time
import asyncio
import random
from collections import defaultdict
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.error import TelegramError

# ==================== إعدادات ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 7195085575
CHANNEL_USERNAME = "@Riiin69"
CHANNEL_LINK = "https://t.me/Riiin69"

DB_FILE = "bot_data.json"
DELETE_AFTER = 30
RATE_LIMIT_SECONDS = 20

# ==================== بيانات التشغيل ====================
videos = {}                         # {file_id: signature}
blacklist = {994608867}
user_history = defaultdict(set)
last_action = {}
admin_upload_mode = False
admin_added_count = 0
data_lock = asyncio.Lock()

# ==================== خادم الويب ====================
async def handle(request):
    return web.Response(text="Bot is online and running fine!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def post_init(application: Application):
    asyncio.create_task(start_web_server())

# ==================== حفظ وتحميل البيانات ====================
async def load_data():
    global videos, blacklist
    if not os.path.exists(DB_FILE):
        return
    try:
        async with data_lock:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                videos = data.get("videos", {})
                blacklist = set(data.get("blacklist", [994608867]))
    except Exception as e:
        print(f"Error loading data: {e}")

async def save_data():
    try:
        async with data_lock:
            data = {
                "videos": videos,
                "blacklist": list(blacklist)
            }
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

# ==================== أدوات مساعدة ====================
async def delete_message_after_delay(message, delay: int = DELETE_AFTER):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        return False

def get_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🛠️ الدعم الفني", url=f"tg://user?id={ADMIN_ID}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def make_signature(video) -> str:
    return f"{video.duration}_{video.file_size}"

# ==================== الأوامر الأساسية ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in blacklist:
        await update.message.reply_text("🚫 **عذراً، تم حظرك من استخدام هذا البوت.**", parse_mode="Markdown")
        return

    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            "⚠️ **عذراً! يجب عليك الاشتراك في القناة لاستخدام البوت.**\n\n"
            "اشترك ثم اضغط على زر التحقق:",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "👋 **أهلاً بك في بوت تبادل المقاطع!**\n\n"
        "أرسل مقطع فيديو الآن ليتم تبادله تلقائياً مع مقطع آخر.\n"
        "⚠️ يمنع إرسال المقاطع المكررة أو إعادة إرسال المقاطع المستلمة من البوت.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id in blacklist:
        return

    if query.data == "check_sub":
        if await check_subscription(query.from_user.id, context):
            await query.edit_message_text(
                "✅ **تم التحقق بنجاح!** يمكنك الآن إرسال المقاطع وتبادلها.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await query.answer("❌ ما زلت غير مشترك في القناة!", show_alert=True)

# ==================== أوامر الأدمن ====================
async def execute_delete(update: Update):
    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.video:
        await update.message.reply_text("⚠️ قم بالرد (Reply) على رسالة التقرير التي تحتوي على الفيديو.")
        return

    file_id = reply_msg.video.file_id
    sig = make_signature(reply_msg.video)

    removed = False
    if file_id in videos:
        del videos[file_id]
        removed = True

    to_remove = [fid for fid, s in videos.items() if s == sig]
    for fid in to_remove:
        del videos[fid]
        removed = True

    if removed:
        await save_data()
        await update.message.reply_text("✅ **تم حذف المقطع نهائياً ولن يظهر مجدداً لأحد!**", parse_mode="Markdown")
    else:
        await update.message.reply_text("ℹ️ المقطع غير موجود أو تم حذفه سابقاً.")

async def execute_ban(update: Update):
    reply_msg = update.message.reply_to_message
    if not reply_msg:
        await update.message.reply_text("⚠️ قم بالرد (Reply) على رسالة التقرير.")
        return

    text_to_search = reply_msg.caption or reply_msg.text or ""
    ids_found = re.findall(r"\b\d{7,12}\b", text_to_search)

    target_user_id = None
    for found_id in ids_found:
        if int(found_id) != ADMIN_ID:
            target_user_id = int(found_id)
            break

    if not target_user_id:
        await update.message.reply_text("❌ لم يتم العثور على آيدي المستخدم في الرسالة.")
        return

    blacklist.add(target_user_id)

    if reply_msg.video:
        file_id = reply_msg.video.file_id
        sig = make_signature(reply_msg.video)
        if file_id in videos:
            del videos[file_id]
        to_remove = [fid for fid, s in videos.items() if s == sig]
        for fid in to_remove:
            del videos[fid]

    await save_data()
    await update.message.reply_text(
        f"🚫 **تم حظر المستخدم `{target_user_id}` وحذف مقطعه نهائياً!**",
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📊 **إحصائيات البوت:**\n\n"
        f"• عدد المقاطع: `{len(videos)}`\n"
        f"• عدد المحظورين: `{len(blacklist)}`",
        parse_mode="Markdown"
    )

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_upload_mode, admin_added_count

    if update.effective_user.id != ADMIN_ID:
        return

    text = (update.message.text or "").strip().lower()

    if text in ["/add", "إضافة", "اضافة", "تعبئة"]:
        admin_upload_mode = True
        admin_added_count = 0
        await update.message.reply_text(
            "📥 **تم تفعيل وضع تعبئة المقاطع!**\n\n"
            "أرسل المقاطع الآن (فردية أو ألبوم).\n"
            "عند الانتهاء أرسل `/done` أو كلمة **تم**.",
            parse_mode="Markdown"
        )

    elif text in ["/done", "تم", "إنهاء", "انهاء"] and admin_upload_mode:
        admin_upload_mode = False
        await save_data()
        await update.message.reply_text(
            f"✅ **تم حفظ المقاطع وإغلاق وضع التعبئة!**\n"
            f"📊 المضافة: `{admin_added_count}` | الإجمالي: `{len(videos)}`",
            parse_mode="Markdown"
        )

    elif text in ["/del", "/delete", "حذف", "مسح"]:
        await execute_delete(update)

    elif text in ["/ban", "حظر", "احظره"]:
        await execute_ban(update)

    elif text in ["/stats", "إحصائيات", "احصائيات"]:
        await stats_command(update, context)

# ==================== معالجة الفيديوهات ====================
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_added_count

    user = update.effective_user
    video = update.message.video
    file_id = video.file_id
    sig = make_signature(video)

    # وضع تعبئة الأدمن
    if user.id == ADMIN_ID and admin_upload_mode:
        if file_id not in videos:
            videos[file_id] = sig
            admin_added_count += 1
            await save_data()
        return

    # فحوصات المستخدم
    if user.id in blacklist:
        await update.message.reply_text(
            "🚫 **عذراً، تم حظرك من استخدام هذا البوت.**",
            parse_mode="Markdown"
        )
        return

    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            "⚠️ **عذراً! يجب عليك الاشتراك في القناة أولاً.**",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    # Rate Limit
    now = time.time()
    if user.id in last_action and (now - last_action[user.id]) < RATE_LIMIT_SECONDS:
        remaining = int(RATE_LIMIT_SECONDS - (now - last_action[user.id]))
        await update.message.reply_text(f"⏳ انتظر **{remaining}** ثانية قبل إرسال مقطع آخر.")
        return
    last_action[user.id] = now

    # منع تكرار المقاطع
    if file_id in videos or sig in videos.values():
        await update.message.reply_text(
            "⚠️ **هذا المقطع مستخدم سابقاً أو تم استلامه من البوت!**\n"
            "الرجاء إرسال مقطع جديد من إعدادك الخاص.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    # إشعار الأدمن
    admin_caption = (
        f"📥 **مقطع متبادل جديد:**\n\n"
        f"👤 **الاسم:** {user.full_name}\n"
        f"🔗 **اليوزر:** @{user.username if user.username else 'لا يوجد'}\n"
        f"🆔 **الآيدي:** `{user.id}`"
    )
    try:
        await context.bot.send_video(
            chat_id=ADMIN_ID,
            video=file_id,
            caption=admin_caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin Notification Error: {e}")

    # اختيار مقطع مختلف تماماً
    seen = user_history[user.id]

    available = [
        fid for fid, s in videos.items()
        if fid != file_id and s != sig and fid not in seen
    ]

    if not available:
        available = [
            fid for fid, s in videos.items()
            if fid != file_id and s != sig
        ]

    if available:
        random_video = random.choice(available)

        sent_message = await update.message.reply_video(
            video=random_video,
            caption=f"⏳ **قم بحفظ المقطع فوراً، سينحذف بعد {DELETE_AFTER} ثانية!**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        user_history[user.id].add(random_video)
        if len(user_history[user.id]) > 80:
            user_history[user.id] = set(list(user_history[user.id])[-50:])

        # إضافة مقطع المستخدم
        videos[file_id] = sig

        # تسجيل المقطع المرسل لمنع إعادة رفعه
        if sent_message.video:
            out_sig = make_signature(sent_message.video)
            if sent_message.video.file_id not in videos:
                videos[sent_message.video.file_id] = out_sig

        await save_data()
        asyncio.create_task(delete_message_after_delay(sent_message, DELETE_AFTER))

    else:
        videos[file_id] = sig
        await save_data()
        await update.message.reply_text(
            "تم استلام مقطعك بنجاح!\n"
            "حالياً ما في مقاطع مختلفة متاحة، أرسل مقطعاً آخر أو انتظر مشاركة جديدة.",
            reply_markup=get_main_keyboard()
        )

# ==================== التشغيل ====================
def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable is not set.")
        return

    # تحميل البيانات قبل تشغيل البوت
    asyncio.run(load_data())

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["add", "done", "del", "delete", "ban", "stats"], handle_admin_commands))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_commands))

    print("Starting bot...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
