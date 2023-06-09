from enum import Enum
import json

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
from ..terraform import TerraformCreate

ENDPOINT = 'https://ims.ru-moscow-1.hc.sbercloud.ru'

IMS = Module(
    name='Image Management Service',
    router=Router(name='ims')
)


class Action(str, Enum):
    CREATE = 'create'
    CREATE_TERRAFORM = 'create terraform'
    LIST = 'list'
    IMPORT = 'import'


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


@IMS.router.callback_query(ImsCallback.filter(F.action == Action.CREATE_TERRAFORM))
async def ims_create_terraform(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового образа диска')
    await state.update_data(use_terraform=True)
    await state.set_state(ImsCreateStates.NAME)
    await call.answer()


@IMS.router.callback_query(ImsCallback.filter(F.action == Action.CREATE))
async def ims_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового образа диска')
    await state.update_data(use_terraform=False)
    await state.set_state(ImsCreateStates.NAME)
    await call.answer()


@IMS.router.message(ImsCreateStates.NAME)
async def ims_create_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer('Введи instance_id машины, с которой будем делать образ')
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

    if data['use_terraform'] == True:
        config = TerraformCreate().create_image(
            name=data['name'],
            instance_id=data['instance_id']
        )
        await message.answer(f'<code>{config}</code>', parse_mode='html')
        await state.set_state(GlobalState.DEFAULT)
        return

    client = data['client']
    description = message.text
    try:
        request = CreateImageRequest()
        request.body = CreateImageRequestBody(
            name=data['name'], instance_id=data['instance_id'], description=description)
        response = client.create_image_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer('Не вышло :(')
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Образ создается')
    await state.set_state(GlobalState.DEFAULT)


@IMS.router.callback_query(ImsCallback.filter(F.action == Action.LIST))
async def ims_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    try:
        request = ListImagesRequest()
        response = client.list_images_async(request)
        response = json.loads(str(response.result()))
        messag = '**Доступные образы:**\n'
        for image in response['images']:
            messag += ('**Name:**\t`' +
                       image['name'] + '`') if image['name'] else ''
            messag += '\n'
            messag += ('**ID:**\t`' + image['id'] + '`') if image['id'] else ''
            messag += '\n'
            messag += '\n'
        await call.message.answer(messag, parse_mode='markdown')
    except exceptions.ClientRequestException as e:
        await call.message.answer('Не вышло :(')
        await call.message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await call.answer()


class ImsImportState(StatesGroup):
    NAME = State()
    OS_VERSION = State()
    IMAGE_URL = State()
    MIN_DISK = State()


@IMS.router.callback_query(ImsCallback.filter(F.action == Action.IMPORT))
async def ims_import(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для импортируемого образа диска')
    await state.set_state(ImsImportState.NAME)
    await call.answer()


@IMS.router.message(ImsImportState.NAME)
async def ims_import_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer('Введи версию ОС образа')
    await state.set_state(ImsImportState.OS_VERSION)


@IMS.router.message(ImsImportState.OS_VERSION)
async def ims_import_os_version(message: types.Message, state: FSMContext):
    os_version = message.text
    await state.update_data(os_version=os_version)
    await message.answer('Введи минимальный размер диска образа (в гигах)')
    await state.set_state(ImsImportState.MIN_DISK)


@IMS.router.message(ImsImportState.MIN_DISK)
async def ims_import_min_disk(message: types.Message, state: FSMContext):
    min_disk = message.text
    await state.update_data(min_disk=min_disk)
    await message.answer('Введи URL образа диска')
    await state.set_state(ImsImportState.IMAGE_URL)


@IMS.router.message(ImsImportState.IMAGE_URL)
async def ims_import_image_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    image_url = await state.get_data()
    client = data['client']
    image_url = message.text
    try:
        request = ImportImageQuickRequest()
        request.body = QuickImportImageByFileRequestBody(
            image_url=image_url, min_disk=data['min_disk'], name=data['name'], os_version=data['os_version'])
        response = client.import_image_quick_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer('Не вышло :(')
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Образ импортируется')
    await state.set_state(GlobalState.DEFAULT)
