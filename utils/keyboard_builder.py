from telegram import ReplyKeyboardMarkup

def build_keyboard(options):
    return ReplyKeyboardMarkup([[opt] for opt in options], one_time_keyboard=True, resize_keyboard=True)
