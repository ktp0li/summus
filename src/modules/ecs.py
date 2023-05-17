from enum import Enum

from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkecs.v2 import(EcsAsyncClient, ListServersDetailsRequest, ListFlavorsRequest)

ENDPOINT = 'https://ecs.ru-moscow-1.hc.sbercloud.ru'

ECS = Module(
    name='Elastic Cloud Server',
    router=Router(name='ecs')
)

class Action(str, Enum):
    CREATE_PREPAID = 'create prepaid'
    LIST = 'list'
    LIST_FLAVORS = 'list flavors'
    SHOW_FLAVOR = 'show flavors'

class EcsCallback(CallbackData, prefix='ecs'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=EcsCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()


@ECS.router.callback_query(F.data == ECS.name)
async def ecs_main(call: CallbackQuery, state: FSMContext):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()

    credentials = BasicCredentials(
        ak=data['ak'],
        sk=data['sk'],
        project_id=data['project_id'],
    )

    client = EcsAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(ENDPOINT) \
        .build()

    await state.update_data(client=client)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


class EcsCreateStates(StatesGroup):
    NAME = State()
    FLAVOR = State()
    IMAGE_ID = State()
    ROOT_VOL_TYPE = State()
    ecs_ID = State()
    SUBNET_ID = State()

@ECS.router.callback_query(EcsCallback.filter(F.action == Action.CREATE_PREPAID))
async def ecs_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для новой виртуальной машины')
    await state.set_state(EcsCreateStates.NAME)
    await call.answer()


def __ecs_to_str(ecs) -> str:
    text = f'<b>{ecs.name}</b>:\n' + \
        f'\t id: <code>{ecs.id}</code>\n' + \
        f'\t flavor: <code>{ecs.flavor}</code>\n' + \
        f'\t status: <b>{ecs.status}</b>\n'

    return text

@ECS.router.callback_query(EcsCallback.filter(F.action == Action.LIST))
async def ecs_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    try:
        request = ListServersDetailsRequest()
        response = client.list_servers_details_async(request)
        result = response.result()
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    entries = [__ecs_to_str(ecs) for ecs in result.servers]
    await call.message.answer('\n'.join(entries), parse_mode='html')
    await call.answer()


@ECS.router.callback_query(EcsCallback.filter(F.action == Action.LIST_FLAVORS))
async def ecs_list_flavors(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']

    try:
        request = ListFlavorsRequest()
        response = client.list_flavors_async(request)
        result = response.result()
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    entries = [flavor.name for flavor in result.flavors]
    await call.message.answer('\n'.join(entries), parse_mode='html')
    await call.answer()


class EcsShowFlavor(StatesGroup):
    SHOW = State()

def __flavor_to_str(flavor) -> str:
    text = f'<b>{flavor.name}</b>:\n' + \
        f'\t disk: <b>{flavor.disk}</b>\n' + \
        f'\t vcpus: <b>{flavor.vcpus}</b>\n' + \
        f'\t ram: <b>{flavor.ram}</b>\n'

    return text

@ECS.router.callback_query(EcsCallback.filter(F.action == Action.SHOW_FLAVOR))
async def ecs_show_flavor_name(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Информацию о каком флейворе хочешь посмотреть?')
    await state.set_state(EcsShowFlavor.SHOW)
    await call.answer()

@ECS.router.message(EcsShowFlavor.SHOW)
async def ecs_show_flavor(message: types.Message, state: FSMContext):
    name = message.text
    data = await state.get_data()
    client = data['client']

    try:
        request = ListFlavorsRequest()
        response = client.list_flavors_async(request)
        result = response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    entries = [__flavor_to_str(flavor) for flavor in result.flavors if flavor.name == name]
    await message.answer('\n'.join(entries), parse_mode='html')
    await state.set_state(GlobalState.DEFAULT)
