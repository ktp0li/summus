from aiogram.utils.keyboard import InlineKeyboardBuilder

def add_exit_button(builder: InlineKeyboardBuilder):
    builder.button(text='В главное меню', callback_data='exit')
