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
from huaweicloudsdkvpc.v2 import VpcAsyncClient
from huaweicloudsdkvpc.v2 import CreateSubnetOption, CreateSubnetRequest, CreateSubnetRequestBody, CreateSubnetResponse
from huaweicloudsdkvpc.v2 import ListSubnetsRequest, ListSubnetsResponse
from huaweicloudsdkvpc.v2 import DeleteSubnetRequest
from huaweicloudsdkvpc.v2 import ShowSubnetRequest, ShowSubnetResponse
from huaweicloudsdkvpc.v2 import UpdateSubnetOption, UpdateSubnetRequest, UpdateSubnetRequestBody, UpdateSubnetResponse

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

ENDPOINT = 'https://vpc.ru-moscow-1.hc.sbercloud.ru'

SUBNET = Module(
    name='Subnet',
    router=Router(name='subnet')
)


class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    SHOW_BY_ID = 'show by id'
    SHOW = 'show'
    UPDATE = 'update'
    UPDATE_BY_ID = 'update by id'
    DELETE = 'delete'
    DELETE_BY_ID = 'delete by id'


class SubnetCallback(CallbackData, prefix='subnet'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=SubnetCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()


@SUBNET.router.callback_query(F.data == SUBNET.name)
async def subnet_main(call: CallbackQuery, state: FSMContext):
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


class SubnetCreateStates(StatesGroup):
    NAME = State()
    DESCRIPTION = State()
    CIDR = State()
    VPC_ID = State()


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.CREATE))
async def subnet_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового сабнета')
    await state.set_state(SubnetCreateStates.NAME)
    await call.answer()


@SUBNET.router.message(SubnetCreateStates.NAME)
async def subnet_create_name(message: types.Message, state: FSMContext):
    name = message.text

    await message.answer('Введи описание')
    await state.update_data(name=name)
    await state.set_state(SubnetCreateStates.DESCRIPTION)


@SUBNET.router.message(SubnetCreateStates.DESCRIPTION)
async def subnet_create_description(message: types.Message, state: FSMContext):
    description = message.text

    await state.update_data(description=description)
    await message.answer('введи CIDR')
    await state.set_state(SubnetCreateStates.CIDR)


@SUBNET.router.message(SubnetCreateStates.CIDR)
async def subnet_create_cidr(message: types.Message, state: FSMContext):
    cidr = message.text
    await state.update_data(cidr=cidr)

    await message.answer('введи vpc id')
    await state.set_state(SubnetCreateStates.VPC_ID)


@SUBNET.router.message(SubnetCreateStates.VPC_ID)
async def subnet_create_vpc_id(message: types.Message, state: FSMContext):
    vpc_id = message.text

    # TODO: сделать это НЕ константой
    gateway_ip = '10.0.0.1'

    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        sub = CreateSubnetOption(
            name=data['name'],
            description=data['description'],
            cidr=data['cidr'],
            vpc_id=vpc_id,
            gateway_ip=gateway_ip
        )

        body = CreateSubnetRequestBody(sub)
        request = CreateSubnetRequest(body)
        response = client.create_subnet_async(request)
        result = response.result()  # type: CreateSubnetResponse

        if result.subnet is None:
            await message.answer('Ошибка!')
            await message.answer(str(result))
            await state.set_state(GlobalState.DEFAULT)
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Создано!')
    await state.set_state(GlobalState.DEFAULT)


def __subnet_to_str(subnet) -> str:
    text = f'<b>{subnet.name}</b>: {subnet.description}\n' + \
           f'\t id: <code>{subnet.id}</code>\n' + \
           f'\t cidr: <code>{subnet.cidr}</code>\n' + \
           f'\t vpc_id: <code>{subnet.vpc_id}</code>\n' + \
           f'\t gateway ip: {subnet.gateway_ip}\n' + \
           f'\t status: <b>{subnet.status}</b>\n'

    return text


def __create_subnets_keyboard(client, callbacktype):
    request = ListSubnetsRequest()
    response = client.list_subnets_async(request)
    result = response.result()  # type: ListSubnetsResponse

    builder = InlineKeyboardBuilder()

    for subnet in result.subnets:
        builder.button(
            text=subnet.name,
            callback_data=callbacktype(action='do', id=subnet.id),
        )
    builder.button(text='Назад', callback_data=callbacktype(
        action='back', id='____'))

    return builder.as_markup()


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.LIST))
async def subnet_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        request = ListSubnetsRequest()
        response = client.list_subnets_async(request)
        result = response.result()  # type: ListSubnetsResponse
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await call.answer()
        await state.set_state(GlobalState.DEFAULT)
        return

    entries = [__subnet_to_str(sub) for sub in result.subnets]
    await call.message.answer('\n'.join(entries), parse_mode='html')
    await call.answer()



class SubnetShowCallback(CallbackData, prefix='subnet_show'):
    action: str  # show or go back
    id: str


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.SHOW))
async def subnet_show_buttons(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient
    await call.message.edit_text('Выбери subnet', reply_markup=__create_subnets_keyboard(client, SubnetShowCallback))
    await call.answer()


@SUBNET.router.callback_query(SubnetShowCallback.filter(F.action == 'back'))
async def subnet_show_buttons_back(call: CallbackQuery):
    await call.message.edit_text('Subnetworks', reply_markup=keyboard())
    await call.answer()


@SUBNET.router.callback_query(SubnetShowCallback.filter(F.action == 'show'))
async def subnet_show_buttons_entry(call: CallbackQuery, state: FSMContext, callback_data: SubnetShowCallback):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        request = ShowSubnetRequest(subnet_id=callback_data.id)
        response = client.show_subnet_async(request)
        result = response.result()  # type: ShowSubnetResponse
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await call.answer()
        await state.set_state(GlobalState.DEFAULT)
        return

    await call.message.reply(__subnet_to_str(result.subnet), parse_mode='html')
    await call.answer()


class SubnetShowStates(StatesGroup):
    ID = State()


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.SHOW_BY_ID))
async def subnet_show_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id сабнета')
    await state.set_state(SubnetShowStates.ID)
    await call.answer()


@SUBNET.router.message(SubnetShowStates.ID)
async def subnet_show(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    subnet_id = message.text
    try:
        request = ShowSubnetRequest(subnet_id=subnet_id)
        response = client.show_subnet_async(request)
        result = response.result()  # type: ShowSubnetResponse

        await message.reply(__subnet_to_str(result.subnet), parse_mode='html')
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await state.set_state(GlobalState.DEFAULT)


class SubnetDeleteCallback(CallbackData, prefix='subnet_delete'):
    action: str
    id: str


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.DELETE))
async def vpc_delete(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient
    await call.message.edit_text('Выбери VPC для удаления', reply_markup=__create_subnets_keyboard(client, SubnetDeleteCallback))
    await call.answer()


@SUBNET.router.callback_query(SubnetDeleteCallback.filter(F.action == 'do'))
async def vpc_delete_entry(call: CallbackQuery, state: FSMContext, callback_data: SubnetDeleteCallback):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        request = ShowSubnetRequest(subnet_id=callback_data.id)
        response = client.show_subnet_async(request)
        result = response.result()  # type: ShowSubnetResponse

        request = DeleteSubnetRequest(
            vpc_id=result.subnet.vpc_id, subnet_id=callback_data.id)
        response = client.delete_subnet_async(request)
        response.result()
    except exceptions.ClientRequestException as exc:
        await call.message.answer(exc.error_msg)
        await call.answer()
        return

    await call.message.answer('Удалено')
    await call.answer()


@SUBNET.router.callback_query(SubnetDeleteCallback.filter(F.action == 'back'))
async def vpc_delete_back(call: CallbackQuery):
    await call.message.edit_text('Subnet', reply_markup=keyboard())
    await call.answer()


class SubnetDeleteStates(StatesGroup):
    SUBNET_ID = State()
    VPC_ID = State()


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.DELETE_BY_ID))
async def subnet_delete_subnet_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id сабнета')
    await state.set_state(SubnetDeleteStates.SUBNET_ID)
    await call.answer()


@SUBNET.router.message(SubnetDeleteStates.SUBNET_ID)
async def subnet_delete_vpc_id(message: types.Message, state: FSMContext):
    subnet_id = message.text
    await state.update_data(subnet_id=subnet_id)
    await message.answer('Введи id vpc')
    await state.set_state(SubnetDeleteStates.VPC_ID)


@SUBNET.router.message(SubnetDeleteStates.VPC_ID)
async def subnet_delete(message: types.Message, state: FSMContext):
    vpc_id = message.text

    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        request = DeleteSubnetRequest(
            vpc_id=vpc_id, subnet_id=data['subnet_id'])
        response = client.delete_subnet_async(request)
        response.result()
    except exceptions.ClientRequestException as exc:
        await message.answer(exc.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Удалено')
    await state.set_state(GlobalState.DEFAULT)


class SubnetUpdateStates(StatesGroup):
    SUBNET_ID = State()
    VPC_ID = State()
    NAME = State()
    DESCRIPTION = State()


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.UPDATE_BY_ID))
async def subnet_update_subnet_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи id сабнета')
    await state.set_state(SubnetUpdateStates.SUBNET_ID)
    await call.answer()


@SUBNET.router.message(SubnetUpdateStates.SUBNET_ID)
async def subnet_update_vpc_id(message: types.Message, state: FSMContext):
    subnet_id = message.text
    await state.update_data(subnet_id=subnet_id)

    await message.answer('Введи id vpc')
    await state.set_state(SubnetUpdateStates.VPC_ID)


@SUBNET.router.message(SubnetUpdateStates.VPC_ID)
async def subnet_update_name(message: types.Message, state: FSMContext):
    vpc_id = message.text
    await state.update_data(vpc_id=vpc_id)

    await message.answer('Введи новое имя')
    await state.set_state(SubnetUpdateStates.NAME)


@SUBNET.router.message(SubnetUpdateStates.NAME)
async def subnet_update_desc(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)

    await message.answer('Введи новое описание')
    await state.set_state(SubnetUpdateStates.DESCRIPTION)


@SUBNET.router.message(SubnetUpdateStates.DESCRIPTION)
async def subnet_update_by_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    description = message.text
    try:
        subnet = UpdateSubnetOption(
            name=data['name'],
            description=description
        )
        body = UpdateSubnetRequestBody(subnet)
        request = UpdateSubnetRequest(
            body=body, subnet_id=data['subnet_id'], vpc_id=data['vpc_id'])

        response = client.update_subnet_async(request)
        result = response.result()  # type: UpdateSubnetResponse

        if result.subnet is None:
            await message.answer('Ошибка!')
            await message.answer(str(result))
            await state.set_state(GlobalState.DEFAULT)
            return
    except exceptions.ClientRequestException as exc:
        await message.answer('Ошибка!')
        await message.answer(exc.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Данные обновлены')
    await state.set_state(GlobalState.DEFAULT)


class SubnetUpdateCallback(CallbackData, prefix='subnet_update'):
    action: str
    id: str


@SUBNET.router.callback_query(SubnetCallback.filter(F.action == Action.UPDATE))
async def subnet_update(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient
    await call.message.edit_text('Выбери Subnet для изменения', reply_markup=__create_subnets_keyboard(client, SubnetUpdateCallback))
    await call.answer()


@SUBNET.router.callback_query(SubnetUpdateCallback.filter(F.action == 'back'))
async def subnet_update_back(call: CallbackQuery):
    await call.message.edit_text('Subnet', reply_markup=keyboard())
    await call.answer()


@SUBNET.router.callback_query(SubnetUpdateCallback.filter(F.action == 'do'))
async def subnet_update_entry(call: CallbackQuery, state: FSMContext, callback_data: SubnetUpdateCallback):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    try:
        request = ShowSubnetRequest(subnet_id=callback_data.id)
        response = client.show_subnet_async(request)
        result = response.result()  # type: ShowSubnetResponse
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await call.answer()
        await state.set_state(GlobalState.DEFAULT)
        return

    await state.update_data(subnet_id=result.subnet.id)
    await state.update_data(vpc_id=result.subnet.vpc_id)

    await call.message.answer('Введите новое имя (ЭТО SUBNET)')
    await call.answer()
    await state.set_state(SubnetUpdateStates.NAME)
