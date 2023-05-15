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
from huaweicloudsdkvpc.v2 import CreateVpcRequest, CreateVpcOption, CreateVpcRequestBody
from huaweicloudsdkvpc.v2 import DeleteVpcRequest, DeleteVpcResponse

from src.module import Module
from src.utils import add_exit_button
from src.utils import get_endpoint

VPC = Module(
    name='Virtual Private Cloud',
    router=Router(name='vpc')
)

cred = BasicCredentials('0HISGMSMIOSIB3I3LAFI',
                        'Xi0iikywUYqfy2FnJFgDc4u12kKyWVEEkTAMf85f', 'b4df643b9d8e44a58b64605519482245')
dbg_client = VpcAsyncClient.new_builder() \
    .with_http_config(HttpConfig.get_default_config()) \
    .with_credentials(cred) \
    .with_endpoint(get_endpoint()) \
    .build()


class Action(str, Enum):
    AUTH = 'authorize'
    CREATE = 'create'
    CREATE_SUBNET = 'create subnet'
    LIST = 'list'
    LIST_SUBNET = 'list subnet'
    SHOW = 'show'
    SHOW_SUBNET = 'show subnet'
    EDIT = 'edit'
    EDIT_SUBNET = 'edit subnet'
    DELETE = 'delete'
    DELETE_SUBNET = 'delete subnet'
    UNAUTH = 'unauthorize'


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


class AuthStates(StatesGroup):
    PROJECT_ID = State()
    AK = State()
    SK = State()
    AUTHORIZED = State()


@VPC.router.callback_query(F.data == VPC.name)
async def main(call: CallbackQuery, state: FSMContext):
    # TODO: fds
    # await state.set_state(AuthStates.AUTHORIZED)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.AUTH))
async def vpc_auth(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введите project ID')
    await state.set_state(AuthStates.PROJECT_ID)
    await call.answer()


@VPC.router.message(AuthStates.PROJECT_ID)
async def vpc_auth_pjid(message: types.Message, state: FSMContext):
    project_id = message.text

    await state.update_data(project_id=project_id)
    await message.answer('Введите AK')
    await state.set_state(AuthStates.AK)


@VPC.router.message(AuthStates.AK)
async def vpc_auth_ak(message: types.Message, state: FSMContext):
    ak = message.text
    await state.update_data(ak=ak)
    await message.answer('Введите SK')
    await state.set_state(AuthStates.SK)


@VPC.router.message(AuthStates.SK)
async def vpc_auth_sk(message: types.Message, state: FSMContext):
    sk = message.text
    await state.update_data(sk=sk)
    await message.answer('батя грит малаца. Ща проверим твои креды')

    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()
    ak = data['ak']
    project_id = data['project_id']
    endpoint = get_endpoint()

    credentials = BasicCredentials(ak, sk, project_id)

    client = VpcAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    await state.update_data(client=client)

    try:
        client.list_vpcs_async(ListVpcsRequest(limit=1))
    except exceptions.ClientRequestException as e:  # pylint: disable=C0103
        print(e)
        await message.answer('Неверные креды, бро. Попробуй ещё раз', reply_markup=keyboard())
        await state.clear()
        return

    await message.answer('Всё нормально. Я проверил. Что делаем дальше?', reply_markup=keyboard())
    await state.set_state(AuthStates.AUTHORIZED)


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.UNAUTH))
async def vpc_unauth(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text('Твои креды были почищены', reply_markup=keyboard())
    await state.clear()
    await call.answer()


class CreateStates(StatesGroup):
    NAME = State()
    DESCRIPTION = State()
    CIDR = State()
    ENTERPRISE_PROJECT_ID = State()


@VPC.router.callback_query(AuthStates.AUTHORIZED, VpcCallback.filter(F.action == Action.CREATE))
async def vpc_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового vpc')
    await state.set_state(CreateStates.NAME)
    await call.answer()


@VPC.router.message(CreateStates.NAME)
async def vpc_create_name(message: types.Message, state: FSMContext):
    name = message.text

    await message.answer('Введи описание')
    await state.update_data(name=name)
    await state.set_state(CreateStates.DESCRIPTION)


@VPC.router.message(CreateStates.DESCRIPTION)
async def vpc_create_description(message: types.Message, state: FSMContext):
    description = message.text

    await state.update_data(description=description)
    await message.answer('введи CIDR')
    await state.set_state(CreateStates.CIDR)


@VPC.router.message(CreateStates.CIDR)
async def vpc_create_cidr(message: types.Message, state: FSMContext):
    cidr = message.text
    await state.update_data(cidr=cidr)

    await message.answer('введи Enterprise project id (или 0)')
    await state.set_state(CreateStates.ENTERPRISE_PROJECT_ID)


@VPC.router.message(CreateStates.ENTERPRISE_PROJECT_ID)
async def vpc_create_projid(message: types.Message, state: FSMContext):
    enterprise_project_id = message.text

    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vpc = CreateVpcOption(
        cidr=data['cidr'],
        name=data['name'],
        description=data['description'],
        enterprise_project_id=enterprise_project_id
    )

    body = CreateVpcRequestBody(vpc)
    request = CreateVpcRequest(body)
    response = client.create_vpc_async(request)

    print(response)

    await message.answer('Создано!')
    await state.set_state(AuthStates.AUTHORIZED)


@VPC.router.callback_query(AuthStates.AUTHORIZED, VpcCallback.filter(F.action == Action.LIST))
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


class DeleteStates(StatesGroup):
    ID = State()


@VPC.router.callback_query(AuthStates.AUTHORIZED, VpcCallback.filter(F.action == Action.DELETE))
async def vpc_delete_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id вэпэцэшки')
    await state.set_state(DeleteStates.ID)
    await call.answer()


@VPC.router.message(DeleteStates.ID)
async def vpc_delete(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vid = message.text
    request = ShowVpcRequest(vpc_id=vid)

    try:
        response = client.delete_vpc_async(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.clear()
        return

    await message.answer('это база')
    await state.set_state(AuthStates.AUTHORIZED)


class ShowStates(StatesGroup):
    ID = State()


@VPC.router.callback_query(AuthStates.AUTHORIZED, VpcCallback.filter(F.action == Action.SHOW))
async def vpc_show_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id вэпэцэшки')
    await state.set_state(ShowStates.ID)
    await call.answer()


@VPC.router.message(ShowStates.ID)
async def vpc_show(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    vid = message.text
    request = ShowVpcRequest(vpc_id=vid)

    try:
        response = client.show_vpc_async(request)
        result = response.result()  # type: ShowVpcResponse
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.clear()
        return

    await state.clear()


@VPC.router.callback_query(VpcCallback.filter(F.action.in_(list(Action))))
async def vpc_not_authorized(call: CallbackQuery):
    await call.message.edit_text('Бро сначала тебе нужно авторизоваться. ' +
                                 'Забери свои хайповые токены в личном кабинете',
                                 reply_markup=keyboard())
    await call.answer()
