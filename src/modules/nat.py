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
from huaweicloudsdknat.v2 import NatAsyncClient, ListNatGatewaysRequest, ListNatGatewaysResponse
from huaweicloudsdknat.v2 import CreateNatGatewayOption, CreateNatGatewayRequest, CreateNatGatewayRequestBody, CreateNatGatewayResponse
from huaweicloudsdknat.v2 import DeleteNatGatewayRequest
from huaweicloudsdknat.v2 import ShowNatGatewayRequest, ShowNatGatewayResponse
from huaweicloudsdknat.v2 import UpdateNatGatewayOption, UpdateNatGatewayRequest, UpdateNatGatewayRequestBody

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

endpoint = 'https://nat.ru-moscow-1.hc.sbercloud.ru'

NAT = Module(
    name='Public NAT Gateway',
    router=Router(name='nat')
)


class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    SHOW = 'show'
    UPDATE = 'update'
    DELETE = 'delete'


class NatCallback(CallbackData, prefix='nat'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=NatCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()


@NAT.router.callback_query(F.data == NAT.name)
async def nat_main(call: CallbackQuery, state: FSMContext):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()

    credentials = BasicCredentials(
        ak=data['ak'],
        sk=data['sk'],
        project_id=data['project_id'],
    )

    client = NatAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    await state.update_data(client=client)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


class NatCreateStates(StatesGroup):
    NAME = State()
    DESCRIPTION = State()
    ROUTER_ID = State()
    SUBNET_ID = State()
    SPEC = State()
    ENTERPRISE_PROJECT_ID = State()


@NAT.router.callback_query(NatCallback.filter(F.action == Action.CREATE))
async def nat_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового NAT')
    await state.set_state(NatCreateStates.NAME)
    await call.answer()


@NAT.router.message(NatCreateStates.NAME)
async def nat_create_name(message: types.Message, state: FSMContext):
    name = message.text

    await message.answer('Введи описание')
    await state.update_data(name=name)
    await state.set_state(NatCreateStates.DESCRIPTION)


@NAT.router.message(NatCreateStates.DESCRIPTION)
async def nat_create_description(message: types.Message, state: FSMContext):
    description = message.text

    await state.update_data(description=description)
    await message.answer('введи id роутера (VPC)')
    await state.set_state(NatCreateStates.ROUTER_ID)


@NAT.router.message(NatCreateStates.ROUTER_ID)
async def nat_create_router_id(message: types.Message, state: FSMContext):
    router_id = message.text

    await state.update_data(router_id=router_id)
    await message.answer('введи spec (1, 2, 3, 4)')
    await state.set_state(NatCreateStates.SPEC)


@NAT.router.message(NatCreateStates.SPEC)
async def nat_create_spec(message: types.Message, state: FSMContext):
    spec = message.text

    await state.update_data(spec=spec)
    await message.answer('введи id сабнетворка')
    await state.set_state(NatCreateStates.SUBNET_ID)


@NAT.router.message(NatCreateStates.SUBNET_ID)
async def nat_create_subnet_id(message: types.Message, state: FSMContext):
    subnet_id = message.text
    await state.update_data(subnet_id=subnet_id)

    await message.answer('введи Enterprise project id (или 0)')
    await state.set_state(NatCreateStates.ENTERPRISE_PROJECT_ID)


@NAT.router.message(NatCreateStates.ENTERPRISE_PROJECT_ID)
async def nat_create_projid(message: types.Message, state: FSMContext):
    enterprise_project_id = message.text

    data = await state.get_data()
    client = data['client']  # type: NatAsyncClient

    try:
        nat = CreateNatGatewayOption(
            name=data['name'],
            description=data['description'],
            router_id=data['router_id'],
            internal_network_id=data['subnet_id'],
            spec=data['spec'],
            enterprise_project_id=enterprise_project_id
        )

        body = CreateNatGatewayRequestBody(nat)
        request = CreateNatGatewayRequest(body)
        response = client.create_nat_gateway_async(request)
        result = response.result()  # type: CreateNatGatewayResponse

        if result.nat_gateway is None:
            await message.answer('Ошибка!')
            await message.answer(str(result))
            await state.set_state(GlobalState.DEFAULT)
            return
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Создано!')
    await state.set_state(GlobalState.DEFAULT)


@NAT.router.callback_query(GlobalState.DEFAULT, NatCallback.filter(F.action == Action.LIST))
async def nat_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: NatAsyncClient

    request = ListNatGatewaysRequest()
    response = client.list_nat_gateways_async(request)
    result = response.result()  # type: ListNatGatewaysResponse

    entries = []
    for nat in result.nat_gateways:
        entry = f'<b>{nat.name}</b>\n' + \
                f'\t id: <code>{nat.id}</code>\n' + \
                f'\t spec: {nat.spec}\n' + \
                f'\t status: {nat.status}\n' + \
                f'\t description: {nat.description}\n'

        entries.append(entry)

    await call.message.answer('\n'.join(entries), parse_mode='html')
    await call.answer()


class nat_DeleteStates(StatesGroup):
    ID = State()


@NAT.router.callback_query(GlobalState.DEFAULT, NatCallback.filter(F.action == Action.DELETE))
async def nat_delete_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id ната')
    await state.set_state(nat_DeleteStates.ID)
    await call.answer()


@NAT.router.message(nat_DeleteStates.ID)
async def nat_delete(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: NatAsyncClient

    nat_id = message.text

    try:
        request = DeleteNatGatewayRequest(nat_gateway_id=nat_id)
        response = client.delete_nat_gateway_async(request)
        response.result()
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('это база')
    await state.set_state(GlobalState.DEFAULT)


class nat_ShowStates(StatesGroup):
    ID = State()


@NAT.router.callback_query(GlobalState.DEFAULT, NatCallback.filter(F.action == Action.SHOW))
async def nat_show_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи nat id')
    await state.set_state(nat_ShowStates.ID)
    await call.answer()


@NAT.router.message(nat_ShowStates.ID)
async def nat_show(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: NatAsyncClient

    nat_id = message.text
    try:
        request = ShowNatGatewayRequest(nat_gateway_id=nat_id)
        response = client.show_nat_gateway_async(request)
        result = response.result()  # type: ShowNatGatewayResponse

        if result.nat_gateway is None:
            await message.answer('Ошибка!')
            await message.answer(str(result))
            await state.set_state(GlobalState.DEFAULT)
            return
        
        await message.answer(str(result))

    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)

        # TODO: ещё попытку
        await state.set_state(GlobalState.DEFAULT)
        return

    await state.set_state(GlobalState.DEFAULT)


class nat_UpdateStates(StatesGroup):
    NAT_ID = State()
    NAME = State()
    DESCRIPTION = State()
    SPEC = State()


@NAT.router.callback_query(GlobalState.DEFAULT, NatCallback.filter(F.action == Action.UPDATE))
async def nat_update_vpc_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи nat id')
    await state.set_state(nat_UpdateStates.NAT_ID)
    await call.answer()


@NAT.router.message(nat_UpdateStates.NAT_ID)
async def nat_update_name(message: types.Message, state: FSMContext):
    nat_id = message.text
    await state.update_data(nat_id=nat_id)

    await message.answer('Введи новое имя')
    await state.set_state(nat_UpdateStates.NAME)


@NAT.router.message(nat_UpdateStates.NAME)
async def nat_update_desc(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)

    await message.answer('Введи новое описание')
    await state.set_state(nat_UpdateStates.DESCRIPTION)


@NAT.router.message(nat_UpdateStates.DESCRIPTION)
async def nat_update_spec(message: types.Message, state: FSMContext):
    desc = message.text
    await state.update_data(desc=desc)

    await message.answer('Введи spec (1, 2, 3, 4)')
    await state.set_state(nat_UpdateStates.SPEC)


@NAT.router.message(nat_UpdateStates.SPEC)
async def nat_update(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: NatAsyncClient

    spec = message.text
    try:
        vpc = UpdateNatGatewayOption(
            name=data['name'],
            description=data['desc'],
            spec=spec
        )
        body = UpdateNatGatewayRequestBody(vpc)
        request = UpdateNatGatewayRequest(body=body, nat_gateway_id=data['nat_id'])

        response = client.update_nat_gateway_async(request)
        result = response.result()

        if result.nat_gateway is None:
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