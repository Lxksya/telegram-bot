from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from config import ADMIN_IDS
from services.movie_service import load_movies, save_movies, update_session
from utils.keyboard_builder import build_keyboard

# Состояния ConversationHandler
ADMIN_MENU, ADD_MOVIE, DELETE_MOVIE, EDIT_SESSION = range(4)


def register_admin_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_menu)],
        states={
            ADMIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_menu)
            ],
            ADD_MOVIE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_handler)
            ],
            DELETE_MOVIE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_movie_handler)
            ],
            EDIT_SESSION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_session_handler)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text('⚠️ У вас нет прав администратора')
        return ConversationHandler.END

    context.user_data.clear()
    return await show_admin_menu(update)


async def show_admin_menu(update: Update):
    await update.message.reply_text(
        '🛠️ <b>Админ-панель</b>\nВыберите действие:',
        parse_mode='HTML',
        reply_markup=build_keyboard([
            '🎬 Добавить фильм',
            '❌ Удалить фильм',
            '⏱️ Редактировать сеанс',
            '🚪 Выход'
        ])
    )
    return ADMIN_MENU


async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == '🎬 Добавить фильм':
        await update.message.reply_text(
            '📝 Введите данные фильма в формате:\n\n'
            '<code>Название; Дата1 Время1, Дата2 Время2,...</code>\n\n'
            'Пример:\n<code>Интерстеллар; 2023-12-15 19:00, 2023-12-16 21:00</code>',
            parse_mode='HTML'
        )
        return ADD_MOVIE

    elif choice == '❌ Удалить фильм':
        movies = load_movies()
        if not movies:
            await update.message.reply_text('ℹ️ Нет фильмов для удаления')
            return await show_admin_menu(update)

        await update.message.reply_text(
            'Выберите фильм для удаления:',
            reply_markup=build_keyboard([m['title'] for m in movies] + ['↩️ Назад'])
        )
        return DELETE_MOVIE

    elif choice == '⏱️ Редактировать сеанс':
        movies = load_movies()
        if not movies:
            await update.message.reply_text('ℹ️ Нет фильмов для редактирования')
            return await show_admin_menu(update)

        await update.message.reply_text(
            'Выберите фильм для редактирования:',
            reply_markup=build_keyboard([m['title'] for m in movies] + ['↩️ Назад'])
        )
        context.user_data['edit_step'] = 'select_movie'
        return EDIT_SESSION

    elif choice == '🚪 Выход':
        return await cancel_admin(update, context)

    await update.message.reply_text('❌ Неверный выбор, попробуйте еще раз')
    return ADMIN_MENU


async def add_movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        if text.lower() == 'отмена':
            return await show_admin_menu(update)

        title_part, sessions_part = text.split(';', 1)
        title = title_part.strip()
        sessions = []

        for session in sessions_part.split(','):
            date, time = session.strip().split()
            sessions.append({'date': date, 'time': time})

        movies = load_movies()
        if any(m['title'].lower() == title.lower() for m in movies):
            await update.message.reply_text('⚠️ Фильм с таким названием уже существует')
            return await show_admin_menu(update)

        movies.append({'title': title, 'sessions': sessions})
        save_movies(movies)

        await update.message.reply_text(
            f'✅ Фильм <b>{title}</b> успешно добавлен с {len(sessions)} сеансами',
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            '❌ Ошибка формата. Используйте:\n'
            '<code>Название; Дата Время, Дата Время,...</code>\n'
            'Или отправьте "отмена"',
            parse_mode='HTML'
        )
        return ADD_MOVIE

    return await show_admin_menu(update)


async def delete_movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == '↩️ Назад':
        return await show_admin_menu(update)

    movies = load_movies()
    if not any(m['title'] == text for m in movies):
        await update.message.reply_text('❌ Фильм не найден')
        return DELETE_MOVIE

    updated_movies = [m for m in movies if m['title'] != text]
    save_movies(updated_movies)

    await update.message.reply_text(f'✅ Фильм <b>{text}</b> удален', parse_mode='HTML')
    return await show_admin_menu(update)


async def edit_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == '↩️ Назад':
        context.user_data.clear()
        return await show_admin_menu(update)

    if context.user_data.get('edit_step') == 'select_movie':
        movie_title = text
        movies = load_movies()
        movie = next((m for m in movies if m['title'] == movie_title), None)

        if not movie:
            await update.message.reply_text('❌ Фильм не найден')
            return EDIT_SESSION

        if not movie['sessions']:
            await update.message.reply_text('ℹ️ У этого фильма нет сеансов')
            return await show_admin_menu(update)

        sessions_text = '\n'.join(
            f"{i}. {s['date']} {s['time']}"
            for i, s in enumerate(movie['sessions'])
        )

        await update.message.reply_text(
            f'Сеансы фильма <b>{movie_title}</b>:\n{sessions_text}\n\n'
            'Введите номер сеанса, новую дату и время в формате:\n'
            '<code>номер, дата, время</code>\n\n'
            'Пример: <code>0, 2023-12-20, 18:00</code>',
            parse_mode='HTML'
        )
        context.user_data['edit_movie'] = movie_title
        context.user_data['edit_step'] = 'edit_session'
        return EDIT_SESSION

    elif context.user_data.get('edit_step') == 'edit_session':
        try:
            index, new_date, new_time = [x.strip() for x in text.split(',')]
            movie_title = context.user_data['edit_movie']

            if update_session(movie_title, int(index), new_date, new_time):
                await update.message.reply_text('✅ Сеанс успешно обновлен')
            else:
                await update.message.reply_text('❌ Не удалось обновить сеанс')

        except Exception as e:
            await update.message.reply_text(
                '❌ Ошибка формата. Используйте:\n'
                '<code>номер, дата, время</code>\n'
                'Пример: <code>0, 2023-12-20, 18:00</code>',
                parse_mode='HTML'
            )
            return EDIT_SESSION

        finally:
            context.user_data.clear()

        return await show_admin_menu(update)


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        '🔙 Вы вышли из админ-панели\n'
        'Используйте /start для возврата в главное меню',
        reply_markup=build_keyboard(['/start'])
    )
    return ConversationHandler.END