from enum import Enum

from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkims.v2 import *

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

ENDPOINT = 'https://ims.ru-moscow-1.hc.sbercloud.ru'

IMS = Module(
    name='Image Management Service',
    router=Router(name='ims')
)

class Action(str, Enum):
    CREATE = 'create'
    CREATE_WHOLE = 'create whole image'
    CREATE_DATA = 'create data image'
    LIST = 'list'
    SHOW_FLAVOR = 'show flavors'

class ImsCallback(CallbackData, prefix='ims'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=ImsCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(1)

    return builder.as_markup()


@IMS.router.callback_query(F.data == IMS.name)
async def ims_main(call: CallbackQuery, state: FSMContext):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()

    credentials = BasicCredentials(
        ak=data['ak'],
        sk=data['sk'],
    )

    client = ImsAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(ENDPOINT) \
        .build()

    await state.update_data(client=client)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


class ImsCreateStates(StatesGroup):
    NAME = State()
    INSTANCE_ID = State()
    DESCRIPTION = State()

@IMS.router.callback_query(ImsCallback.filter(F.action == Action.CREATE))
async def ims_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового образа диска')
    await state.set_state(ImsCreateStates.NAME)
    await call.answer()

@IMS.router.message(ImsCreateStates.NAME)
async def ims_create_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer('Введи instance_id машины, с которой хуярить образ')
    await state.set_state(ImsCreateStates.INSTANCE_ID)

@IMS.router.message(ImsCreateStates.INSTANCE_ID)
async def ims_create_instance_id(message: types.Message, state: FSMContext):
    instance_id = message.text
    await state.update_data(instance_id=instance_id)
    await message.answer('Введи описание образа диска')
    await state.set_state(ImsCreateStates.DESCRIPTION)

@IMS.router.message(ImsCreateStates.DESCRIPTION)
async def ims_create_network_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    description = message.text
    try:
        request = CreateImageRequest()
        request.body = CreateImageRequestBody(name=data['name'], instance_id=data['instance_id'], description=description)
        response = client.create_image_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer('Не вышло :(')
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return
    
    await message.answer('Образ создается')
    await state.set_state(GlobalState.DEFAULT)

def __ims_to_str(ims) -> str:
    text = f'<b>{ims.name}</b>:\n' + \
        f'\t id: <code>{ims.id}</code>\n' + \
        f'\t flavor: <code>{ims.flavor}</code>\n' + \
        f'\t status: <b>{ims.status}</b>\n'

    return text

@IMS.router.callback_query(ImsCallback.filter(F.action == Action.LIST))
async def ims_list(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового образа диска')
    

    await call.answer()
