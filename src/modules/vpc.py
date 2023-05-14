from enum import Enum
from aiogram import F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData

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


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.CREATE))
async def vpc_create(call: CallbackQuery):
    await call.message.answer('VPC CREATE')
    await call.answer()
