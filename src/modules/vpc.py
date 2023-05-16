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

endpoint = 'https://vpc.ru-moscow-1.hc.sbercloud.ru'

VPC = Module(
    name='Virtual Private Cloud',
    router=Router(name='vpc')
)


class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    SHOW = 'show'
    UPDATE = 'update'
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
        .with_endpoint(endpoint) \
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


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.LIST))
async def vpc_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    request = ListVpcsRequest()
    response = client.list_vpcs_async(request)
    result = response.result()  # type: ListVpcsResponse

    entries = []
    for vpc in result.vpcs:
        entry = f'<b>{vpc.name}</b>\n' + \
                f'\t id: <code>{vpc.id}</code>\n' + \
                f'\t cidr: {vpc.cidr}\n' + \
                f'\t description: {vpc.description}\n'

        entries.append(entry)

    await call.message.answer('\n'.join(entries), parse_mode='html')
    await call.answer()


class vpc_DeleteStates(StatesGroup):
    ID = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.DELETE))
async def vpc_delete_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id вэпэцэшки')
    await state.set_state(vpc_DeleteStates.ID)
    await call.answer()


@VPC.router.message(vpc_DeleteStates.ID)
async def vpc_delete(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vid = message.text

    try:
        request = DeleteVpcRequest(vpc_id=vid)
        response = client.delete_vpc_async(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('это база')
    await state.set_state(GlobalState.DEFAULT)


class vpc_ShowStates(StatesGroup):
    ID = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.SHOW))
async def vpc_show_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id вэпэцэшки')
    await state.set_state(vpc_ShowStates.ID)
    await call.answer()


@VPC.router.message(vpc_ShowStates.ID)
async def vpc_show(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vid = message.text
    try:
        request = ShowVpcRequest(vpc_id=vid)
        response = client.show_vpc_async(request)
        result = response.result()  # type: ShowVpcResponse

        await message.reply(str(result))
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.set_state(GlobalState.DEFAULT)
        return

    await state.set_state(GlobalState.DEFAULT)


class vpc_UpdateStates(StatesGroup):
    VPC_ID = State()
    NAME = State()
    DESCRIPTION = State()
    CIDR = State()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.UPDATE))
async def vpc_update_vpc_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи vpc id')
    await state.set_state(vpc_UpdateStates.VPC_ID)
    await call.answer()


@VPC.router.message(vpc_UpdateStates.VPC_ID)
async def vpc_update_name(message: types.Message, state: FSMContext):
    vpc_id = message.text
    await state.update_data(vpc_id=vpc_id)

    await message.answer('Введи новое имя')
    await state.set_state(vpc_UpdateStates.NAME)


@VPC.router.message(vpc_UpdateStates.NAME)
async def vpc_update_desc(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)

    await message.answer('Введи новое описание')
    await state.set_state(vpc_UpdateStates.DESCRIPTION)


@VPC.router.message(vpc_UpdateStates.DESCRIPTION)
async def vpc_update_cidr(message: types.Message, state: FSMContext):
    desc = message.text
    await state.update_data(desc=desc)

    await message.answer('Введи CIDR')
    await state.set_state(vpc_UpdateStates.CIDR)


@VPC.router.message(vpc_UpdateStates.CIDR)
async def vpc_update(message: types.Message, state: FSMContext):
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
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Данные обновлены')
    await state.set_state(GlobalState.DEFAULT)
