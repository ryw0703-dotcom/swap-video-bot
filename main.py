import os
import asyncio
import random
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. خادم الويب المخصص للمنافذ و UptimeRobot ---
async def handle(request):
    return web.Response(text="Bot is online and running fine!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # الحصول على المنفذ المحدد من Render تلقائياً
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

async def post_init(application: Application):
    # تشغيل خادم الويب كمهام خلفية ضمن حلقة الأحداث الأساسية
    asyncio.create_task(start_web_server())

# --- 2. إعدادات وتعاريف البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 7195085575  # الآيدي الخاص بك

video_database = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت تبادل المقاطع!\n\n"
        "أرسل مقطع فيديو الآن ليتم تبادله تلقائياً مع مقطع آخر من مستخدم مختلف."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video_file_id = update.message.video.file_id

    # إرسال تقرير للآدمن
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
        print(f"Admin Notification Error: {e}")

    # عملية التبادل
    if video_database:
        random_video = random.choice(video_database)
        sent_message = await update.message.reply_video(
            video=random_video,
            caption="⏳ **قم بتحويل المقطع أو حفظه فوراً، ينحذف بعد 30 ثانية!**"
        )
        
        video_database.append(video_file_id)

        # حذف المقطع بعد 30 ثانية
        await asyncio.sleep(30)
        try:
            await sent_message.delete()
        except Exception:
            pass
    else:
        video_database.append(video_file_id)
        await update.message.reply_text(
            "تم استلام مقطعك بنجاح! أنت أول المشاركين، أرسل مقطعاً آخر أو انتظر مشاركة مستخدم جديد ليصلك مقطعه."
        )

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable is not set.")
        return

    # بناء البوت مع ربط دالة post_init
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    print("Starting bot polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
