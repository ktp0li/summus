from enum import Enum
from magic_filter import F
from aiogram import Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData

class Action(str, Enum):
    create = "create"
    edit = "edit"
    remove = "remove"
    next_act = "next_act"

class Resource(str, Enum):
    vpc = "vpc"
    dns = "dns"
    nat = "nat"
    acl = "acl"

class AdminAction(CallbackData, prefix="resource"):
    resource = Resource
    action = Action

start_router = Router(name="start")
vpc_router = Router(name="vpc")

@start_router.message(CommandStart())
async def start(message: types.Message):
    builder = InlineKeyboardBuilder()
    for i in Resource:
        print(i.value)
        builder.button(
            text=i.value,
            callback_data=AdminAction(resource=i.value, action="next_act"),
    )
    builder.adjust(1)

    # 启动命令处理程序
    return await message.answer(
        "白哥你好", reply_markup=builder.as_markup()
    )



@start_router.callback_query(AdminAction.filter(F.resource == 'vpc'))
async def my_callback_foo(call: CallbackQuery, callback_data: dict):
    print("bar =", callback_data.action)
