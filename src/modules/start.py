from aiogram import Router, types
from aiogram.filters import CommandStart

start_router = Router(name="start")

@start_router.message(CommandStart())
async def start(message: types.Message):
    """Start command handler"""
    return await message.answer(
        "白哥你好"
    )
