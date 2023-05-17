import os
import asyncio
import logging

from aiogram import Dispatcher, Bot, types
from aiogram.fsm.storage.memory import MemoryStorage

from src.modules import modules
from src.start import START


def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)
    dispatcher.include_router(START.router)

    for module in modules:
        dispatcher.include_router(module.router)

    return dispatcher


async def main():
    bot = Bot(token=os.getenv('TOKEN'))
    await bot.set_my_commands(
        commands=[types.BotCommand(
            command='start', description='Главное меню бота')]
    )

    dispatcher = create_dispatcher()
    logging.basicConfig(level=logging.INFO)

    await dispatcher.start_polling(
        bot
    )

if __name__ == '__main__':
    asyncio.run(main())
