from telegram.ext import Application
from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    user_handlers.register_user_handlers(app)
    admin_handlers.register_admin_handlers(app)

    print("Бот запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()
