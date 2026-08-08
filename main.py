import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# التوكن ومعرف القناة
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8846666964:AAEGSetfRCcEMZJewe3hs6lez-OqqjpEAKQ")
CHANNEL_USERNAME = "@Riiin69"

# قاعدة بيانات مؤقتة لحفظ المقاطع
video_database = []

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def get_sub_keyboard():
    """لوحة أزرار الاشتراك التفاعلية"""
    keyboard = [
        [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

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
        "أرسل لي أي مقطع فيديو من عندك، وسأرد عليك فوراً بمقطع عشوائي أرسله مستخدم آخر! 🚀",
        parse_mode="Markdown"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استقبال الفيديوهات"""
    user_id = update.effective_user.id

    if not await is_subscribed(user_id, context):
        await update.message.reply_text(
            f"⚠️ **عذراً!** يجب عليك الاشتراك في القناة أولاً لتبادل المقاطع:\n{CHANNEL_USERNAME}",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    # حفظ معرف الفيديو المرسل
    video_file_id = update.message.video.file_id

    # إرسال مقطع عشوائي للمستخدم
    if video_database:
        random_video = random.choice(video_database)
        await update.message.reply_video(
            video=random_video,
            caption="🍿 **إليك مقطع عشوائي مقابل مقطعك!**\nأرسل مقطعاً آخر للحصول على جديد."
        )
    else:
        await update.message.reply_text(
            "✅ **تم استلام مقطعك بنجاح!**\nأنت أول مشارك في البوت، أرسل مقطعاً آخر أو انتظر مشاركات البقية! 🚀"
        )

    # إضافة الفيديو للقائمة إذا لم يكن مكرراً
    if video_file_id not in video_database:
        video_database.append(video_file_id)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الزر"""
    query = update.callback_query
    await query.answer()

    if query.data == "check_sub":
        user_id = query.from_user.id
        if await is_subscribed(user_id, context):
            await query.edit_message_text(
                "✅ **تم التحقق بنجاح!**\nأهلاً بك، أرسل لي الآن أي مقطع فيديو للتبادل 🎬"
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
