import os
import re
import asyncio
import random
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

# --- 1. خادم الويب المخصص لـ Render و UptimeRobot ---
async def handle(request):
    return web.Response(text="Bot is online and running fine!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def post_init(application: Application):
    asyncio.create_task(start_web_server())

# --- 2. إعدادات البوت والبيانات الأساسية ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 7195085575
CHANNEL_USERNAME = "@Riiin69"
CHANNEL_LINK = "https://t.me/Riiin69"

BLACK_LIST = {994608867}

video_database = []
video_unique_ids = set()

# التحقق من اشتراك المستخدم في القناة
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
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

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in BLACK_LIST:
        await update.message.reply_text("🚫 **عذراً، تم حظرك من استخدام هذا البوت.**")
        return

    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            f"⚠️ **عذراً! يجب عليك الاشتراك في القناة لاستخدام البوت.**\n\nاشترك ثم اضغط على زر التحقق:",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "👋 **أهلاً بك في بوت تبادل المقاطع!**\n\n"
        "أرسل مقطع فيديو الآن ليتم تبادله تلقائياً مع مقطع آخر من مستخدم مختلف.\n"
        "⚠️ يمنع إرسال المقاطع المكررة.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# زر التحقق من الاشتراك
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id in BLACK_LIST:
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

# --- 3. معالجة الإدارة: الحذف والحظر ---

async def execute_delete(update: Update):
    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.video:
        await update.message.reply_text("⚠️ قم بالرد (Reply) على رسالة التقرير التي تحتوي على الفيديو.")
        return

    file_id = reply_msg.video.file_id
    file_unique_id = reply_msg.video.file_unique_id

    removed = False
    if file_id in video_database:
        video_database.remove(file_id)
        removed = True
    if file_unique_id in video_unique_ids:
        video_unique_ids.remove(file_unique_id)
        removed = True

    if removed:
        await update.message.reply_text("✅ **تم حذف المقطع بنجاح من قاعدة البيانات!**")
    else:
        await update.message.reply_text("ℹ️ المقطع تم حذفه سابقاً أو غير موجود في القاعدة.")

async def execute_ban(update: Update):
    reply_msg = update.message.reply_to_message
    if not reply_msg:
        await update.message.reply_text("⚠️ قم بالرد (Reply) على رسالة التقرير.")
        return

    text_to_search = reply_msg.caption or reply_msg.text or ""
    ids_found = re.findall(r'\b\d{7,12}\b', text_to_search)
    
    target_user_id = None
    for found_id in ids_found:
        if int(found_id) != ADMIN_ID:
            target_user_id = int(found_id)
            break

    if target_user_id:
        BLACK_LIST.add(target_user_id)
        
        # حذف الفيديو إن وجد
        if reply_msg.video:
            file_id = reply_msg.video.file_id
            file_unique_id = reply_msg.video.file_unique_id
            if file_id in video_database:
                video_database.remove(file_id)
            if file_unique_id in video_unique_ids:
                video_unique_ids.remove(file_unique_id)

        await update.message.reply_text(f"🚫 **تم حظر المستخدم `{target_user_id}` وحذف مقطعه بنجاح!**", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ لم يتم العثور على أيدي المستخدم في الرسالة التي قمت بالرد عليها.")

# معالجة رسائل الأدمن الأوامر والنصوص
async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    text = update.message.text.strip().lower() if update.message.text else ""

    if text in ["/del", "/delete", "حذف", "مسح"]:
        await execute_delete(update)
    elif text in ["/ban", "حظر", "احظره"]:
        await execute_ban(update)

# معالجة الفيديوهات
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in BLACK_LIST:
        await update.message.reply_text("🚫 **عذراً، تم حظرك من استخدام هذا البوت.**")
        return

    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            f"⚠️ **عذراً! يجب عليك الاشتراك في القناة أولاً لتبادل المقاطع.**",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    video = update.message.video
    file_id = video.file_id
    file_unique_id = video.file_unique_id

    # كشف ومنع المقاطع المكررة
    if file_unique_id in video_unique_ids:
        await update.message.reply_text(
            "⚠️ **هذا المقطع تم إرساله سابقاً وموجود بالفعل في البوت!**\nالرجاء إرسال مقطع جديد غير مكرر.",
            reply_markup=get_main_keyboard()
        )
        return

    # إرسال تقرير للآدمن
    admin_caption = (
        f"📥 **مقطع متبادل جديد:**\n\n"
        f"👤 **بيانات المشارك:**\n"
        f"الاسم: {user.full_name}\n"
        f"اليوزر: @{user.username if user.username else 'لا يوجد'}\n"
        f"الآيدي: `{user.id}`"
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

    # عملية التبادل
    if video_database:
        random_video = random.choice(video_database)
        sent_message = await update.message.reply_video(
            video=random_video,
            caption="⏳ **قم بتحويل المقطع أو حفظه فوراً، سينحذف بعد 30 ثانية!**",
            reply_markup=get_main_keyboard()
        )
        
        video_database.append(file_id)
        video_unique_ids.add(file_unique_id)

        await asyncio.sleep(30)
        try:
            await sent_message.delete()
        except Exception:
            pass
    else:
        video_database.append(file_id)
        video_unique_ids.add(file_unique_id)
        await update.message.reply_text(
            "تم استلام مقطعك بنجاح! أنت أول المشاركين، أرسل مقطعاً آخر أو انتظر مشاركة مستخدم جديد ليصلك مقطعه.",
            reply_markup=get_main_keyboard()
        )

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable is not set.")
        return

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    # استقبال أشكال أوامر الأدمن كرسائل متكاملة لتفادي أخطاء المترجم
    app.add_handler(MessageHandler(filters.TEXT, handle_admin_commands))

    print("Starting bot polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
