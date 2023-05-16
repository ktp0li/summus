from aiogram.filters import CommandStart
from aiogram import F, Router
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.module import Module
from src.modules import modules
from src.globalstate import GlobalState

START = Module(
    name='Main module',
    router=Router(name='start')
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


class CreditsState(StatesGroup):
    AK = State()
    SK = State()
    PROJECT_ID = State()
    ACCOUNT_ID = State()


@START.router.message(GlobalState.DEFAULT, CommandStart())
async def main_authorized(message: Message):
    await message.answer(
        "白哥你好", reply_markup=__build_menu()
    )


@START.router.message(CommandStart())
async def main(message: Message, state: FSMContext):
    await message.answer('Привет! Для использования бота тебе нужно авторизироваться. Введи ak')
    await state.set_state(CreditsState.AK)


@START.router.message(CreditsState.AK)
async def auth_ak(message: Message, state: FSMContext):
    await state.update_data(ak=message.text)
    await state.set_state(CreditsState.SK)
    await message.answer('Введи sk')


@START.router.message(CreditsState.SK)
async def auth_sk(message: Message, state: FSMContext):
    await state.update_data(sk=message.text)
    await state.set_state(CreditsState.PROJECT_ID)
    await message.answer('Введи project id')


@START.router.message(CreditsState.PROJECT_ID)
async def auth_project_id(message: Message, state: FSMContext):
    await state.update_data(project_id=message.text)
    await state.set_state(CreditsState.ACCOUNT_ID)
    await message.answer('Введи account id')


@START.router.message(CreditsState.ACCOUNT_ID)
async def auth_account_id(message: Message, state: FSMContext):
    await state.update_data(account_id=message.text)
    await state.set_state(GlobalState.DEFAULT)

    await message.answer(
        "白哥你好", reply_markup=__build_menu()
    )


@START.router.callback_query(F.data == 'exit')
async def exit_(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=__build_menu())
    await call.answer()
