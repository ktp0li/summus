from enum import Enum

from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.module import Module
from src.utils import add_exit_button

VPC = Module(
    name='Virtual Private Cloud',
    router=Router(name='vpc')
)


class Action(str, Enum):
    AUTH = 'authorize'
    CREATE = 'create'
    LIST = 'list'
    EDIT = 'edit'
    REMOVE = 'remove'

class States(StatesGroup):
    PROJECT_ID = State()
    AK = State()
    SK = State()



class VpcCallback(CallbackData, prefix='vpc'):
    action: Action


@VPC.router.callback_query(F.data == VPC.name)
async def main(call: CallbackQuery):
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=VpcCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(1)

    await call.message.edit_reply_markup(reply_markup=builder.as_markup())
    await call.answer()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.AUTH))
async def vpc_auth(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введите project ID')
    await state.set_state(States.PROJECT_ID)
    await call.answer()

@VPC.router.message(States.PROJECT_ID)
async def vpc_auth_pjid(message: types.Message, state: FSMContext):
    project_id = message.text
    await message.answer('Введите AK')
    await state.set_state(States.AK)

@VPC.router.message(States.AK)
async def vpc_auth_ak(message: types.Message, state: FSMContext):
    ak = message.text
    await message.answer('Введите SK')
    await state.set_state(States.SK)

async def vpc_auth_sk(message: types.Message, state: FSMContext):
    sk = message.text
    await message.answer('батя грит малаца')
    await state.clear()



@VPC.router.callback_query(VpcCallback.filter(F.action == Action.CREATE))
async def vpc_create(call: CallbackQuery):
    await call.message.answer('VPC CREATE')
    await call.answer()
