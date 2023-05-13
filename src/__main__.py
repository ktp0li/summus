import os
import asyncio
import logging

from aiogram import Dispatcher, Bot

from src.modules import routers


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()

    for router in routers:
        dispatcher.include_router(router)

    return dispatcher


async def main():
    bot = Bot(token=os.getenv('TOKEN'))
    dispatcher = create_dispatcher()
    logging.basicConfig(level=logging.INFO)

    await dispatcher.start_polling(
        bot
    )

if __name__ == '__main__':
    asyncio.run(main())
