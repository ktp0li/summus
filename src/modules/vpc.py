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
from huaweicloudsdkvpc.v2 import VpcAsyncClient, ListVpcsRequest, ListVpcsResponse
from huaweicloudsdkvpc.v2 import ShowVpcRequest, ShowVpcResponse
from huaweicloudsdkvpc.v2 import CreateVpcRequest, CreateVpcOption, CreateVpcRequestBody, CreateVpcResponse
from huaweicloudsdkvpc.v2 import UpdateVpcOption, UpdateVpcRequestBody, UpdateVpcRequest, UpdateVpcResponse
from huaweicloudsdkvpc.v2 import DeleteVpcRequest

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

ENDPOINT = 'https://vpc.ru-moscow-1.hc.sbercloud.ru'

VPC = Module(
    name='Virtual Private Cloud',
    router=Router(name='vpc')
)


class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    SHOW = 'show'
    SHOW_BY_ID = 'show by id'
    UPDATE_BY_ID = 'update by id'
    UPDATE = 'update'
    DELETE_BY_ID = 'delete by id'
    DELETE = 'delete'


class VpcCallback(CallbackData, prefix='vpc'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=VpcCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()


@VPC.router.callback_query(F.data == VPC.name)
async def vpc_main(call: CallbackQuery, state: FSMContext):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()

    credentials = BasicCredentials(
        ak=data['ak'],
        sk=data['sk'],
        project_id=data['project_id'],
    )

    client = VpcAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(ENDPOINT) \
        .build()

    await state.update_data(client=client)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


class VpcCreateStates(StatesGroup):
    NAME = State()
    DESCRIPTION = State()
    CIDR = State()
    ENTERPRISE_PROJECT_ID = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.CREATE))
async def vpc_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового vpc')
    await state.set_state(VpcCreateStates.NAME)
    await call.answer()


@VPC.router.message(VpcCreateStates.NAME)
async def vpc_create_name(message: types.Message, state: FSMContext):
    name = message.text

    await message.answer('Введи описание')
    await state.update_data(name=name)
    await state.set_state(VpcCreateStates.DESCRIPTION)


@VPC.router.message(VpcCreateStates.DESCRIPTION)
async def vpc_create_description(message: types.Message, state: FSMContext):
    description = message.text

    await state.update_data(description=description)
    await message.answer('введи CIDR')
    await state.set_state(VpcCreateStates.CIDR)


@VPC.router.message(VpcCreateStates.CIDR)
async def vpc_create_cidr(message: types.Message, state: FSMContext):
    cidr = message.text
    await state.update_data(cidr=cidr)

    await message.answer('введи Enterprise project id (или 0)')
    await state.set_state(VpcCreateStates.ENTERPRISE_PROJECT_ID)


@VPC.router.message(VpcCreateStates.ENTERPRISE_PROJECT_ID)
async def vpc_create_projid(message: types.Message, state: FSMContext):
    enterprise_project_id = message.text

    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        vpc = CreateVpcOption(
            cidr=data['cidr'],
            name=data['name'],
            description=data['description'],
            enterprise_project_id=enterprise_project_id
        )

        body = CreateVpcRequestBody(vpc)
        request = CreateVpcRequest(body)
        response = client.create_vpc_async(request)
        result = response.result()  # type: CreateVpcResponse

        if result.vpc is None:
            await message.answer('Ошибка!')
            await message.answer(str(result))
            await state.set_state(GlobalState.DEFAULT)
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Создано!')
    await state.set_state(GlobalState.DEFAULT)


def __vpc_to_str(vpc) -> str:
    text = f'<b>{vpc.name}</b>: {vpc.description}\n' + \
        f'\t id: <code>{vpc.id}</code>\n' + \
        f'\t cidr: <code>{vpc.cidr}</code>\n' + \
        f'\t status: <b>{vpc.status}</b>\n'

    return text


def __create_vpcs_keyboard(client, callbacktype):
    request = ListVpcsRequest()
    response = client.list_vpcs_async(request)
    result = response.result()

    builder = InlineKeyboardBuilder()

    for vpc in result.vpcs:
        builder.button(
            text=vpc.name,
            callback_data=callbacktype(action='do', id=vpc.id),
        )
    builder.button(text='Назад', callback_data=callbacktype(
        action='back', id='____'))

    return builder.as_markup()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.LIST))
async def vpc_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    request = ListVpcsRequest()
    response = client.list_vpcs_async(request)
    result = response.result()  # type: ListVpcsResponse

    entries = [__vpc_to_str(vpc) for vpc in result.vpcs]
    await call.message.answer('\n'.join(entries), parse_mode='html')
    await call.answer()


class VpcShowCallback(CallbackData, prefix='vpc_show'):
    action: str  # do or back
    id: str


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.SHOW))
async def vpc_show_buttons(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient
    await call.message.edit_text('Выбери VPC', reply_markup=__create_vpcs_keyboard(client, VpcShowCallback))
    await call.answer()


@VPC.router.callback_query(VpcShowCallback.filter(F.action == 'back'))
async def vpc_show_buttons_back(call: CallbackQuery):
    await call.message.edit_text('Virtal Private Cloud', reply_markup=keyboard())
    await call.answer()


@VPC.router.callback_query(VpcShowCallback.filter(F.action == 'do'))
async def vpc_show_buttons_entry(call: CallbackQuery, state: FSMContext, callback_data: VpcShowCallback):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    request = ShowVpcRequest(vpc_id=callback_data.id)
    response = client.show_vpc_async(request)
    result = response.result()

    await call.message.reply(__vpc_to_str(result.vpc), parse_mode='html')
    await call.answer()


class VpcDeleteCallback(CallbackData, prefix='vpc_delete'):
    action: str  # delete or back
    id: str


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.DELETE))
async def vpc_delete(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient
    await call.message.edit_text('Выбери VPC для удаления', reply_markup=__create_vpcs_keyboard(client, VpcDeleteCallback))
    await call.answer()


@VPC.router.callback_query(VpcDeleteCallback.filter(F.action == 'do'))
async def vpc_delete_entry(call: CallbackQuery, state: FSMContext, callback_data: VpcDeleteCallback):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        request = DeleteVpcRequest(vpc_id=callback_data.id)
        response = client.delete_vpc_async(request)
        response.result()
    except exceptions.ClientRequestException as exc:
        await call.message.answer(exc.error_msg)
        await call.answer()
        return

    await call.message.answer('это база')
    await state.set_state(GlobalState.DEFAULT)
    await call.answer()


@VPC.router.callback_query(VpcDeleteCallback.filter(F.action == 'back'))
async def vpc_delete_back(call: CallbackQuery):
    await call.message.edit_text('Virtal Private Cloud', reply_markup=keyboard())
    await call.answer()


class VpcDeleteStates(StatesGroup):
    ID = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.DELETE_BY_ID))
async def vpc_delete_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id вэпэцэшки')
    await state.set_state(VpcDeleteStates.ID)
    await call.answer()


@VPC.router.message(VpcDeleteStates.ID)
async def vpc_delete_by_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vpc_id = message.text

    try:
        request = DeleteVpcRequest(vpc_id=vpc_id)
        response = client.delete_vpc_async(request)
        response.result()
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('это база')
    await state.set_state(GlobalState.DEFAULT)


class VpcShowStates(StatesGroup):
    ID = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.SHOW_BY_ID))
async def vpc_show_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id вэпэцэшки')
    await state.set_state(VpcShowStates.ID)
    await call.answer()


@VPC.router.message(VpcShowStates.ID)
async def vpc_show(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vpc_id = message.text
    try:
        request = ShowVpcRequest(vpc_id=vpc_id)
        response = client.show_vpc_async(request)
        result = response.result()  # type: ShowVpcResponse

        await message.answer(text=__vpc_to_str(result.vpc))
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await state.set_state(GlobalState.DEFAULT)


class VpcUpdateStates(StatesGroup):
    VPC_ID = State()
    NAME = State()
    DESCRIPTION = State()
    CIDR = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.UPDATE_BY_ID))
async def vpc_update_vpc_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи vpc id')
    await state.set_state(VpcUpdateStates.VPC_ID)
    await call.answer()


@VPC.router.message(VpcUpdateStates.VPC_ID)
async def vpc_update_name(message: types.Message, state: FSMContext):
    vpc_id = message.text
    await state.update_data(vpc_id=vpc_id)

    await message.answer('Введи новое имя')
    await state.set_state(VpcUpdateStates.NAME)


@VPC.router.message(VpcUpdateStates.NAME)
async def vpc_update_desc(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)

    await message.answer('Введи новое описание')
    await state.set_state(VpcUpdateStates.DESCRIPTION)


@VPC.router.message(VpcUpdateStates.DESCRIPTION)
async def vpc_update_cidr(message: types.Message, state: FSMContext):
    desc = message.text
    await state.update_data(desc=desc)

    await message.answer('Введи CIDR')
    await state.set_state(VpcUpdateStates.CIDR)


@VPC.router.message(VpcUpdateStates.CIDR)
async def vpc_update_by_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    cidr = message.text
    try:
        vpc = UpdateVpcOption(
            name=data['name'],
            description=data['desc'],
            cidr=cidr
        )
        body = UpdateVpcRequestBody(vpc)
        request = UpdateVpcRequest(body=body, vpc_id=data['vpc_id'])
        response = client.update_vpc_async(request)
        result = response.result()  # type: UpdateVpcResponse

        if result.vpc is None:
            await message.answer('Ошибка!')
            await message.answer(str(result))
            await state.set_state(GlobalState.DEFAULT)
            return
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Данные обновлены')
    await state.set_state(GlobalState.DEFAULT)


class VpcUpdateCallback(CallbackData, prefix='vpc_update'):
    action: str
    id: str


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.UPDATE))
async def vpc_update(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient
    await call.message.edit_text('Выбери VPC для изменения', reply_markup=__create_vpcs_keyboard(client, VpcUpdateCallback))
    await call.answer()


@VPC.router.callback_query(VpcUpdateCallback.filter(F.action == 'do'))
async def vpc_update_entry(call: CallbackQuery, state: FSMContext, callback_data: VpcDeleteCallback):
    await state.update_data(vpc_id=callback_data.id)
    await call.message.answer('Введите новое имя')
    await call.answer()
    await state.set_state(VpcUpdateStates.NAME)


@VPC.router.callback_query(VpcDeleteCallback.filter(F.action == 'back'))
async def vpc_update_back(call: CallbackQuery):
    await call.message.edit_text('Virtual Private Cloud', reply_markup=keyboard())
    await call.answer()
