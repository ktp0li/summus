from aiogram.filters import CommandStart
from aiogram import F, Router
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from src.module import Module
from src.modules import modules

MENU = Module(
    name='Menu',
    router=Router(name='menu')
)

def __build_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for module in modules:
        builder.button(
            text=module.name,
            callback_data=module.name,
    )
    builder.adjust(2)

    return builder.as_markup()

@MENU.router.message(CommandStart())
async def main(message: Message):
    return await message.answer(
        "白哥你好", reply_markup=__build_menu()
    )

@MENU.router.callback_query(F.data == 'exit')
async def exit_(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=__build_menu())
    await call.answer()
