from enum import Enum
from aiogram import Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

class AdminAction(CallbackData, prefix="resource"):
    resource = Resource
    action = Action

start_router = Router(name="start")

@start_router.message(CommandStart())
async def start(message: types.Message):
    builder = InlineKeyboardBuilder()
    for i in Resource:
        builder.button(
            text=i.value.title(),
            callback_data=AdminAction(resource=i.value.title(), action="next_act"),
    )
    
    # 启动命令处理程序
    return await message.answer(
        "白哥你好", reply_markup=builder.as_markup()
    )
