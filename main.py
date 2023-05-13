import os
import logging
from aiogram import Bot, Dispatcher, executor, types

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

resources = {'Virtual Private Cloud': 'vpc'}

# 资源选择
@dp.message_handler(commands=['start', 'help'])
async def cmd_start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    for j, k in resources.items():
        keyboard.add(types.InlineKeyboardButton(text=j, callback_data=k))
    await message.answer("Выберите ресурс для взаимодействия:", reply_markup=keyboard)

# 为vpc选择操作
@dp.callback_query_handler(text="vpc")
async def resource_vpc(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    actions = {'Create': 'vpc_create', 'Edit': 'vpc_edit', 'Delete': 'vpc_delete'}
    for j, k in actions.items():
        keyboard.add(types.InlineKeyboardButton(text=j, callback_data=k))
    await call.message.edit_text(text="", reply_markup=keyboard)
    await call.answer()

@dp.callback_query_handler(text="vpc_create")
async def vpc_create(call: types.CallbackQuery):
    pass

@dp.callback_query_handler(text="vpc_edit")
async def vpc_edit(call: types.CallbackQuery):
    pass

@dp.callback_query_handler(text="vpc_delete")
async def vpc_delete(call: types.CallbackQuery):
    pass

if  __name__ == '__main__':
    executor.start_polling(dp)
