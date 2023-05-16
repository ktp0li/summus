from enum import Enum

from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkeps.v1 import (EpsAsyncClient, ListEnterpriseProjectRequest,
                                  CreateEnterpriseProjectRequest, EnterpriseProject,
                                  EnableEnterpriseProjectRequest, DisableAction,
                                  DisableEnterpriseProjectRequest, UpdateEnterpriseProjectRequest)

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

endpoint = 'https://eps.ru-moscow-1.hc.sbercloud.ru'

EPS = Module(
    name='Enterprise Project Management Service',
    router=Router(name='eps')
)


class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    UPDATE = 'update'
    ENABLE = 'enable'
    DISABLE = 'disable'


class EpsCallback(CallbackData, prefix='eps'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=EpsCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()


@EPS.router.callback_query(F.data == EPS.name)
async def eps_main(call: CallbackQuery, state: FSMContext):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()

    credentials = GlobalCredentials(
        ak=data['ak'],
        sk=data['sk'],
        domain_id=data['account_id'],
    )

    client = EpsAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    await state.update_data(client=client)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


class EpsCreateStates(StatesGroup):
    NAME = State()
    DESCRIPTION = State()


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.CREATE))
async def eps_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового проекта')
    await state.set_state(EpsCreateStates.NAME)
    await call.answer()


@EPS.router.message(EpsCreateStates.NAME)
async def eps_create_name(message: types.Message, state: FSMContext):
    name = message.text

    await message.answer('Введи описание')
    await state.update_data(name=name)
    await state.set_state(EpsCreateStates.DESCRIPTION)


@EPS.router.message(EpsCreateStates.DESCRIPTION)
async def eps_create_desc(message: types.Message, state: FSMContext):
    description = message.text

    data = await state.get_data()
    client = data['client']

    try:
        request = CreateEnterpriseProjectRequest()
        request.body = EnterpriseProject(data['name'], description)
        response = client.create_enterprise_project_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Создано!')
    await state.set_state(GlobalState.DEFAULT)


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.LIST))
async def eps_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']

    try:
        request = ListEnterpriseProjectRequest()
        response = client.list_enterprise_project_async(request)
        result = response.result()
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    entry = []
    for i in result.enterprise_projects:
        entry += [f'<b>{i.name}</b>\n' +
                  f'\t id: <code>{i.id}</code>\n' +
                  f'\t description: {i.description}\n'
                  f'\t status: {"enabled" if i.status == 1 else "disabled"}\n']

    await call.message.answer('\n'.join(entry), parse_mode='html')
    await call.answer()


class eps_ProjectStates(StatesGroup):
    ENABLE = State()
    DISABLE = State()


@EPS.router.callback_query(GlobalState.DEFAULT, EpsCallback.filter(F.action == Action.DISABLE))
async def eps_disable_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи айди выключаемого проекта')
    await state.set_state(eps_ProjectStates.DISABLE)
    await call.answer()


@EPS.router.message(eps_ProjectStates.DISABLE)
async def eps_disable(message: types.Message, state: FSMContext):
    proj_id = message.text

    data = await state.get_data()
    client = data['client']

    try:
        request = DisableEnterpriseProjectRequest(proj_id)
        request.body = DisableAction('disable')
        response = client.disable_enterprise_project_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Выключено!')
    await state.set_state(GlobalState.DEFAULT)


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.ENABLE))
async def eps_enable_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи айди включаемого проекта')
    await state.set_state(eps_ProjectStates.ENABLE)
    await call.answer()


@EPS.router.message(eps_ProjectStates.ENABLE)
async def eps_enable(message: types.Message, state: FSMContext):
    proj_id = message.text

    data = await state.get_data()
    client = data['client']

    try:
        request = EnableEnterpriseProjectRequest(proj_id)
        request.body = DisableAction('enable')
        response = client.enable_enterprise_project_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Включено!')
    await state.set_state(GlobalState.DEFAULT)


class eps_UpdateStates(StatesGroup):
    PROJECT_ID = State()
    NAME = State()
    DESCRIPTION = State()


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.UPDATE))
async def eps_update_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи айди изменяемого проекта')
    await state.set_state(eps_UpdateStates.PROJECT_ID)
    await call.answer()


@EPS.router.message(eps_UpdateStates.PROJECT_ID)
async def eps_update_name(message: types.Message, state: FSMContext):
    project_id = message.text
    await state.update_data(project_id=project_id)

    await message.answer('Введи новое имя проекта')
    await state.set_state(eps_UpdateStates.NAME)


@EPS.router.message(eps_UpdateStates.NAME)
async def eps_update_desc(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)

    await message.answer('Введи новое описание проекта')
    await state.set_state(eps_UpdateStates.DESCRIPTION)


@EPS.router.message(eps_UpdateStates.DESCRIPTION)
async def eps_update(message: types.Message, state: FSMContext):
    description = message.text
    data = await state.get_data()
    client = data['client']

    try:
        request = UpdateEnterpriseProjectRequest(data['project_id'])
        request.body = EnterpriseProject(data['name'], description)
        response = client.update_enterprise_project_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(GlobalState.DEFAULT)
        return

    await message.answer('Данные о проекте обновлены!')
    await state.set_state(GlobalState.DEFAULT)

