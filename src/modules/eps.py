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
                                  DisableEnterpriseProjectRequest, UpdateEnterpriseProjectRequest,
                                  ShowEnterpriseProjectRequest)

from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

ENDPOINT = 'https://eps.ru-moscow-1.hc.sbercloud.ru'

EPS = Module(
    name='Enterprise Project Management Service',
    router=Router(name='eps')
)


class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    SHOW = 'show'
    UPDATE = 'update'
    ENABLE = 'enable'
    DISABLE = 'disable'
    UPDATE_BY_ID = 'update by id'
    ENABLE_BY_ID = 'enable by id'
    DISABLE_BY_ID = 'disable by id'


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
        .with_endpoint(ENDPOINT) \
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


def __eps_to_str(eps) -> str:
    text = f'<b>{eps.name}</b>: {eps.description}\n' + \
        f'\t id: <code>{eps.id}</code>\n' + \
        f'\t status: <b>{"enabled" if eps.status == 1 else "disabled"}</b>\n'

    return text


def __create_epss_keyboard(client, callbacktype):
    request = ListEnterpriseProjectRequest()
    response = client.list_enterprise_project_async(request)
    result = response.result()

    builder = InlineKeyboardBuilder()

    for eps in result.enterprise_projects:
        builder.button(
            text=eps.name,
            callback_data=callbacktype(action='do', id=eps.id),
        )
    builder.button(text='Назад', callback_data=callbacktype(
        action='back', id='____'))

    return builder.as_markup()


class EpsShowCallback(CallbackData, prefix='eps_show'):
    action: str
    id: str


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.SHOW))
async def eps_show_buttons(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: EpsAsyncClient
    await call.message.edit_text('Выбери EPS', reply_markup=__create_epss_keyboard(client, EpsShowCallback))
    await call.answer()


@EPS.router.callback_query(EpsShowCallback.filter(F.action == 'back'))
async def eps_show_buttons_back(call: CallbackQuery):
    await call.message.edit_text('Enterprise Project Management', reply_markup=keyboard())
    await call.answer()


@EPS.router.callback_query(EpsShowCallback.filter(F.action == 'do'))
async def eps_show_buttons_entry(call: CallbackQuery, state: FSMContext, callback_data: EpsShowCallback):
    data = await state.get_data()
    client = data['client']  # type: EpsAsyncClient

    request = ShowEnterpriseProjectRequest(
        enterprise_project_id=callback_data.id)
    response = client.show_enterprise_project_async(request)
    result = response.result()

    await call.message.reply(__eps_to_str(result.enterpise_project), parse_mode='html')
    await call.answer()


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

    entry = [__eps_to_str(eps) for eps in result.enterprise_projects]
    await call.message.answer('\n'.join(entry), parse_mode='html')
    await call.answer()


class EpsDisableCallback(CallbackData, prefix='eps_disable'):
    action: str
    id: str


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.DISABLE))
async def eps_disable(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: EpsAsyncClient
    await call.message.edit_text('Выбери EPS для отключения', reply_markup=__create_epss_keyboard(client, EpsDisableCallback))
    await call.answer()


@EPS.router.callback_query(EpsDisableCallback.filter(F.action == 'do'))
async def eps_disable_entry(call: CallbackQuery, state: FSMContext, callback_data: EpsDisableCallback):
    data = await state.get_data()
    client = data['client']  # type: EpsAsyncClient

    try:
        request = DisableEnterpriseProjectRequest(
            enterprise_project_id=callback_data.id)
        request.body = DisableAction('disable')
        response = client.disable_enterprise_project_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await call.answer()
        return

    await call.message.answer('Выключено!')
    await call.answer()


@EPS.router.callback_query(EpsDisableCallback.filter(F.action == 'back'))
async def eps_disable_back(call: CallbackQuery):
    await call.message.edit_text('Enterprise Project Management', reply_markup=keyboard())
    await call.answer()


class EpsEnableCallback(CallbackData, prefix='eps_enable'):
    action: str
    id: str


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.DISABLE))
async def eps_enable(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: EpsAsyncClient
    await call.message.edit_text('Выбери EPS для отключения', reply_markup=__create_epss_keyboard(client, EpsEnableCallback))
    await call.answer()


@EPS.router.callback_query(EpsEnableCallback.filter(F.action == 'do'))
async def eps_enable_entry(call: CallbackQuery, state: FSMContext, callback_data: EpsDisableCallback):
    data = await state.get_data()
    client = data['client']

    try:
        request = EnableEnterpriseProjectRequest(
            enterprise_project_id=callback_data.id)
        request.body = DisableAction('enable')
        response = client.enable_enterprise_project_async(request)
        response.result()
    except exceptions.ClientRequestException as e:
        await call.message.answer(e.error_msg)
        await call.answer()
        return

    await call.message.answer('Включено!')
    await call.answer()


@EPS.router.callback_query(EpsEnableCallback.filter(F.action == 'back'))
async def eps_enable_back(call: CallbackQuery):
    await call.message.edit_text('Enterprise Project Management', reply_markup=keyboard())
    await call.answer()


class EpsProjectStates(StatesGroup):
    ENABLE = State()
    DISABLE = State()


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.DISABLE_BY_ID))
async def eps_disable_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи айди выключаемого проекта')
    await state.set_state(EpsProjectStates.DISABLE)
    await call.answer()


@EPS.router.message(EpsProjectStates.DISABLE)
async def eps_disable_by_id(message: types.Message, state: FSMContext):
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


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.ENABLE_BY_ID))
async def eps_enable_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи айди включаемого проекта')
    await state.set_state(EpsProjectStates.ENABLE)
    await call.answer()


@EPS.router.message(EpsProjectStates.ENABLE)
async def eps_enable_by_id(message: types.Message, state: FSMContext):
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


class EpsUpdateStates(StatesGroup):
    PROJECT_ID = State()
    NAME = State()
    DESCRIPTION = State()


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.UPDATE_BY_ID))
async def eps_update_id(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи айди изменяемого проекта')
    await state.set_state(EpsUpdateStates.PROJECT_ID)
    await call.answer()


@EPS.router.message(EpsUpdateStates.PROJECT_ID)
async def eps_update_name(message: types.Message, state: FSMContext):
    project_id = message.text
    await state.update_data(project_id=project_id)

    await message.answer('Введи новое имя проекта')
    await state.set_state(EpsUpdateStates.NAME)


@EPS.router.message(EpsUpdateStates.NAME)
async def eps_update_desc(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)

    await message.answer('Введи новое описание проекта')
    await state.set_state(EpsUpdateStates.DESCRIPTION)


@EPS.router.message(EpsUpdateStates.DESCRIPTION)
async def eps_update_by_id(message: types.Message, state: FSMContext):
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


class EpsUpdateCallback(CallbackData, prefix='eps_update'):
    action: str
    id: str


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.UPDATE))
async def eps_update(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: EpsAsyncClient
    await call.message.edit_text('Выбери EPS для изменения', reply_markup=__create_epss_keyboard(client, EpsUpdateCallback))
    await call.answer()


@EPS.router.callback_query(EpsUpdateCallback.filter(F.action == 'do'))
async def eps_update_entry(call: CallbackQuery, state: FSMContext, callback_data: EpsUpdateCallback):
    await state.update_data(project_id=callback_data.id)
    await call.message.answer('Введите новое имя')
    await call.answer()
    await state.set_state(EpsUpdateStates.NAME)


@EPS.router.callback_query(EpsUpdateCallback.filter(F.action == 'back'))
async def eps_update_back(call: CallbackQuery):
    await call.message.edit_text('Enterprise Project Management', reply_markup=keyboard())
    await call.answer()
