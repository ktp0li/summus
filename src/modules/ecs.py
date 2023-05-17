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
from huaweicloudsdkecs.v2 import (EcsAsyncClient, ListServersDetailsRequest, ListFlavorsRequest, CreateServersRequest,
                                  CreateServersRequestBody, PrePaidServer, PrePaidServerRootVolume, PrePaidServerNic,
                                  ShowServerRequest)

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

ENDPOINT = 'https://ecs.ru-moscow-1.hc.sbercloud.ru'

ECS = Module(
    name='Elastic Cloud Server',
    router=Router(name='ecs')
)


class Action(str, Enum):
    CREATE_PREPAID = 'create prepaid'
    CREATE_PREPAID_TERRAFORM = 'create prepaid terraform'
    LIST = 'list'
    SHOW = 'show'
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
    VPC_ID = State()
    SUBNET_ID = State()

@ECS.router.callback_query(EcsCallback.filter(F.action == Action.CREATE_PREPAID_TERRAFORM))
async def ecs_create_terraform(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для новой виртуальной машины')
    await state.update_data(use_terraform=True)
    await state.set_state(EcsCreateStates.NAME)
    await call.answer()


@ECS.router.callback_query(EcsCallback.filter(F.action == Action.CREATE_PREPAID))
async def ecs_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для новой виртуальной машины')
    await state.update_data(use_terraform=False)
    await state.set_state(EcsCreateStates.NAME)
    await call.answer()


@ECS.router.message(EcsCreateStates.NAME)
async def ecs_create_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer('Введи flavor новой виртуальной машины')
    await state.set_state(EcsCreateStates.FLAVOR)


@ECS.router.message(EcsCreateStates.FLAVOR)
async def ecs_create_flavor(message: types.Message, state: FSMContext):
    flavor = message.text
    await state.update_data(flavor=flavor)
    await message.answer('Введи айди образа для новой виртуальной машины')
    await state.set_state(EcsCreateStates.IMAGE_ID)


@ECS.router.message(EcsCreateStates.IMAGE_ID)
async def ecs_create_image_id(message: types.Message, state: FSMContext):
    image_id = message.text
    await state.update_data(image_id=image_id)
    await message.answer('Введи айди vpc для новой виртуальной машины')
    await state.set_state(EcsCreateStates.VPC_ID)


@ECS.router.message(EcsCreateStates.VPC_ID)
async def ecs_create_vpc_id(message: types.Message, state: FSMContext):
    vpc_id = message.text
    await state.update_data(vpc_id=vpc_id)
    await message.answer('Введи айди subnet для nic-интерфейса новой виртуальной машины')
    await state.set_state(EcsCreateStates.SUBNET_ID)


@ECS.router.message(EcsCreateStates.SUBNET_ID)
async def ecs_create_network_id(message: types.Message, state: FSMContext):
    data = await state.get_data()

    if data['use_terraform'] == True:
        await state.set_state(GlobalState.DEFAULT)
        return

    client = data['client']
    subnet_id = message.text
    try:
        request = CreateServersRequest()
        root_volume = PrePaidServerRootVolume(volumetype='SSD')
        nic = PrePaidServerNic(subnet_id=subnet_id)
        server = PrePaidServer(image_ref=data['image_id'], flavor_ref=data['flavor'],
                               name=data['name'], vpcid=data['vpc_id'],
                               root_volume=root_volume, nics=[nic])
        request.body = CreateServersRequestBody(server=server)
        response = client.create_servers_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Виртуальная машина создается')
    await state.set_state(GlobalState.DEFAULT)


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

    entries = [__flavor_to_str(flavor)
               for flavor in result.flavors if flavor.name == name]
    await message.answer('\n'.join(entries), parse_mode='html')
    await state.set_state(GlobalState.DEFAULT)


class EcsShow(StatesGroup):
    SERVER_ID = State()


def __server_to_str(server) -> str:
    text = f'<b>{server.name}</b>: {server.description} \n' + \
        f'\t flavor: <code>{server.flavor}</code>\n' + \
        f'\t os type: {server.metadata["os_type"]} \n' + \
        f'\t os bit: {server.metadata["os_bit"]} \n' + \
        f'\t charging mode: {server.metadata["charging_mode"]} \n' + \
        f'\t tags: {server.tags}\n' + \
        f'\t updated: {server.updated}\n' + \
        f'\t created: {server.created}\n' + \
        f'\t status: <b>{server.status}</b>\n'

    return text


@ECS.router.callback_query(EcsCallback.filter(F.action == Action.SHOW))
async def ecs_show_server_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Информацию о каком сервере хочешь посмотреть? (ID)')
    await state.set_state(EcsShow.SERVER_ID)
    await call.answer()


@ECS.router.message(EcsShow.SERVER_ID)
async def ecs_show(message: types.Message, state: FSMContext):
    server_id = message.text
    data = await state.get_data()
    client = data['client']  # type: EcsAsyncClient

    try:
        request = ShowServerRequest(server_id=server_id)
        response = client.show_server_async(request)
        result = response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer(__server_to_str(result.server), parse_mode='html')
    await state.set_state(GlobalState.DEFAULT)
