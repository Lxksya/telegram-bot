from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from services.movie_service import load_movies
from services.booking_service import (
    get_user_bookings,
    cancel_booking,
    load_bookings,
    save_bookings
)
from utils.keyboard_builder import build_keyboard

# Состояния ConversationHandler
MAIN_MENU, MOVIE_CHOICE, SESSION_CHOICE, SEAT_CHOICE, BOOKING_CANCELLATION = range(5)


def register_user_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
            ],
            MOVIE_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_choice)
            ],
            SESSION_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_session_choice)
            ],
            SEAT_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_seat_choice)
            ],
            BOOKING_CANCELLATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_cancellation)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_operation)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_main_menu(update)


async def show_main_menu(update: Update):
    user_id = str(update.effective_user.id)
    bookings = get_user_bookings(user_id)

    if bookings:
        buttons = ["🎬 Забронировать билет", "📋 Мои бронирования", "❌ Отменить бронь"]
    else:
        buttons = ["🎬 Забронировать билет"]

    await update.message.reply_text(
        "🎭 Добро пожаловать в кинотеатр! Выберите действие:",
        reply_markup=build_keyboard(buttons)
    )

    return MAIN_MENU


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == "🎬 Забронировать билет":
        return await start_booking(update)
    elif choice == "📋 Мои бронирования":
        return await show_user_bookings(update)
    elif choice == "❌ Отменить бронь":
        return await start_booking_cancellation(update, context)
    else:
        await update.message.reply_text("❌ Неизвестная команда")
        return await show_main_menu(update)


async def start_booking(update: Update):
    movies = load_movies()

    if not movies:
        await update.message.reply_text("🎥 Сейчас нет доступных фильмов.")
        return await show_main_menu(update)

    await show_movies(update)
    return MOVIE_CHOICE


async def show_movies(update: Update):
    movies = load_movies()
    await update.message.reply_text(
        "🎬 Выберите фильм:",
        reply_markup=build_keyboard([m['title'] for m in movies] + ['🚪 Назад'])
    )


async def show_user_bookings(update: Update):
    user_id = str(update.effective_user.id)
    bookings = get_user_bookings(user_id)

    if not bookings:
        await update.message.reply_text("📭 У вас нет активных бронирований.")
        return await show_main_menu(update)

    message = ["📋 Ваши бронирования:"]
    for booking in bookings:
        message.append(
            f"\n🎬 {booking['movie']}\n"
            f"⏰ {booking.get('session', 'Время не указано')}\n"
            f"💺 Место: {booking['seat']}"
        )

    await update.message.reply_text("\n".join(message))
    return await show_main_menu(update)


async def handle_movie_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == '🚪 Назад':
        return await show_main_menu(update)

    movies = load_movies()
    selected_movie = next((m for m in movies if m['title'] == choice), None)

    if not selected_movie:
        await update.message.reply_text("❌ Фильм не найден")
        return await show_movies(update)

    if not selected_movie.get('sessions'):
        await update.message.reply_text("⏰ Нет доступных сеансов для этого фильма")
        return await show_movies(update)

    context.user_data['selected_movie'] = selected_movie
    await show_sessions(update, selected_movie)
    return SESSION_CHOICE


async def show_sessions(update: Update, movie: dict):
    sessions = [f"{s['date']} {s['time']}" for s in movie['sessions']]
    await update.message.reply_text(
        f"⏰ Сеансы для {movie['title']}:",
        reply_markup=build_keyboard(sessions + ['↩️ Назад'])
    )


async def handle_session_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == '↩️ Назад':
        await show_movies(update)
        return MOVIE_CHOICE

    movie = context.user_data['selected_movie']
    session = next((s for s in movie['sessions'] if f"{s['date']} {s['time']}" == choice), None)

    if not session:
        await update.message.reply_text("❌ Сеанс не найден")
        return await show_sessions(update, movie)

    context.user_data['selected_session'] = session
    await show_seats(update)
    return SEAT_CHOICE


async def show_seats(update: Update):
    await update.message.reply_text(
        "💺 Выберите место (1-20):",
        reply_markup=build_keyboard([str(i) for i in range(1, 21)] + ['↩️ Назад'])
    )


async def handle_seat_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == '↩️ Назад':
        await show_sessions(update, context.user_data['selected_movie'])
        return SESSION_CHOICE

    if not choice.isdigit() or not 1 <= int(choice) <= 20:
        await update.message.reply_text("❌ Введите число от 1 до 20")
        return await show_seats(update)

    booking = {
        'user_id': str(update.effective_user.id),
        'movie': context.user_data['selected_movie']['title'],
        'session': f"{context.user_data['selected_session']['date']} {context.user_data['selected_session']['time']}",
        'seat': choice
    }

    bookings = load_bookings()
    bookings.append(booking)
    save_bookings(bookings)

    await update.message.reply_text(
        f"✅ Бронь успешно создана!\n\n"
        f"🎬 Фильм: {booking['movie']}\n"
        f"⏰ Время: {booking['session']}\n"
        f"💺 Место: {booking['seat']}"
    )

    return await show_main_menu(update)


async def start_booking_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bookings = get_user_bookings(user_id)

    if not bookings:
        await update.message.reply_text("ℹ️ Нет бронирований для отмены.")
        return await show_main_menu(update)

    choices = []
    for i, booking in enumerate(bookings, 1):
        choices.append(f"{i}. {booking['movie']} (место {booking['seat']})")

    await update.message.reply_text(
        "Выберите бронь для отмены:",
        reply_markup=build_keyboard(choices + ["Отмена"])
    )

    context.user_data['user_bookings'] = bookings
    return BOOKING_CANCELLATION


async def handle_booking_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == "Отмена":
        await update.message.reply_text("✅ Операция отменена.")
        return await show_main_menu(update)

    bookings = context.user_data.get('user_bookings', [])

    try:
        num = int(choice.split('.')[0]) - 1
        if num < 0 or num >= len(bookings):
            raise ValueError
    except:
        await update.message.reply_text("❌ Неверный выбор. Попробуйте еще раз.")
        return BOOKING_CANCELLATION

    booking_to_cancel = bookings[num]
    bookings = [b for b in load_bookings() if not (
            b.get('user_id') == str(update.effective_user.id) and
            b['movie'] == booking_to_cancel['movie'] and
            b['session'] == booking_to_cancel['session'] and
            b['seat'] == booking_to_cancel['seat']
    )]

    if save_bookings(bookings):
        await update.message.reply_text(f"✅ Бронь на {booking_to_cancel['movie']} отменена!")
    else:
        await update.message.reply_text("❌ Не удалось отменить бронь.")

    return await show_main_menu(update)


async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔙 Возврат в главное меню")
    return await show_main_menu(update)