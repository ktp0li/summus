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
from huaweicloudsdkeps.v1 import(EpsAsyncClient, ListEnterpriseProjectRequest,
                                CreateEnterpriseProjectRequest, EnterpriseProject,
                                EnableEnterpriseProjectRequest, EnableAction, DisableAction,
                                DisableEnterpriseProjectRequest, UpdateEnterpriseProjectRequest)

from src.module import Module
from src.utils import add_exit_button

endpoint = 'https://eps.ru-moscow-1.hc.sbercloud.ru'

EPS = Module(
    name='Enterprise Project Management Service',
    router=Router(name='eps')
)

class Action(str, Enum):
    AUTH = 'authorize'
    CREATE = 'create'
    LIST = 'list'
    UPDATE = 'update'
    ENABLE = 'enable'
    DISABLE = 'disable'
    UNAUTH = 'unauthorize'


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

class eps_AuthStates(StatesGroup):
    ACCOUNT_ID = State()
    AK = State()
    SK = State()
    AUTHORIZED = State()

@EPS.router.callback_query(F.data == EPS.name)
async def eps_main(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()

@EPS.router.callback_query(EpsCallback.filter(F.action == Action.AUTH))
async def eps_auth(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи account ID')
    await state.set_state(eps_AuthStates.ACCOUNT_ID)
    await call.answer()


@EPS.router.message(eps_AuthStates.ACCOUNT_ID)
async def eps_auth_pjid(message: types.Message, state: FSMContext):
    account_id = message.text

    await state.update_data(account_id=account_id)
    await message.answer('Введи AK')
    await state.set_state(eps_AuthStates.AK)


@EPS.router.message(eps_AuthStates.AK)
async def eps_auth_ak(message: types.Message, state: FSMContext):
    ak = message.text
    await state.update_data(ak=ak)
    await message.answer('Введи SK')
    await state.set_state(eps_AuthStates.SK)

@EPS.router.message(eps_AuthStates.SK)
async def eps_auth_sk(message: types.Message, state: FSMContext):
    sk = message.text
    await state.update_data(sk=sk)
    await message.answer('Батя грит малаца. Ща проверим твои креды')

    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()
    ak = data['ak']
    account_id = data['account_id']

    credentials = GlobalCredentials(ak, sk, account_id)

    client = EpsAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    await state.update_data(client=client)

    try:
        client.list_enterprise_project_async(ListEnterpriseProjectRequest(limit=1)).result()
    except exceptions.ClientRequestException as e:  # pylint: disable=C0103
        print(e)
        await message.answer('Неверные креды, бро. Попробуй ещё раз', reply_markup=keyboard())
        await state.clear()
        return

    await message.answer('Всё нормально. Я проверил. Что делаем дальше?', reply_markup=keyboard())
    await state.set_state(eps_AuthStates.AUTHORIZED)


@EPS.router.callback_query(EpsCallback.filter(F.action == Action.UNAUTH))
async def esp_unauth(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text('Твои креды были почищены', reply_markup=keyboard())
    await state.clear()
    await call.answer()

class eps_CreateStates(StatesGroup):
    NAME = State()
    DESCRIPTION = State()


@EPS.router.callback_query(eps_AuthStates.AUTHORIZED, EpsCallback.filter(F.action == Action.CREATE))
async def eps_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введи имя для нового проекта')
    await state.set_state(eps_CreateStates.NAME)
    await call.answer()

@EPS.router.message(eps_CreateStates.NAME)
async def eps_create_name(message: types.Message, state: FSMContext):
    name = message.text

    await message.answer('Введи описание')
    await state.update_data(name=name)
    await state.set_state(eps_CreateStates.DESCRIPTION)

@EPS.router.message(eps_CreateStates.DESCRIPTION)
async def eps_create_desc(message: types.Message, state: FSMContext):
    description = message.text

    data = await state.get_data()
    client = data['client'] 

    try:
        request = CreateEnterpriseProjectRequest()
        request.body = EnterpriseProject(data['name'], description)
        response = client.create_enterprise_project_async(request)
        result = response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(eps_AuthStates.AUTHORIZED)
        return

    await message.answer('Создано!')
    await state.set_state(eps_AuthStates.AUTHORIZED)


@EPS.router.callback_query(eps_AuthStates.AUTHORIZED, EpsCallback.filter(F.action == Action.LIST))
async def eps_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']

    request = ListEnterpriseProjectRequest()
    response = client.list_enterprise_project_async(request)
    result = response.result()

    entry = []
    for i in result.enterprise_projects:
        entry += [f'<b>{i.name}</b>\n' + \
                    f'\t id: <code>{i.id}</code>\n' + \
                    f'\t description: {i.description}\n'
                    f'\t status: {"enabled" if i.status == 1 else "disabled"}\n']

    await call.message.answer('\n'.join(entry), parse_mode='html')
    await call.answer()


class eps_ProjectStates(StatesGroup):
    ENABLE = State()
    DISABLE = State()

@EPS.router.callback_query(eps_AuthStates.AUTHORIZED, EpsCallback.filter(F.action == Action.DISABLE))
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
        result = response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(eps_AuthStates.AUTHORIZED)
        return

    await message.answer('Выключено!')
    await state.set_state(eps_AuthStates.AUTHORIZED)


@EPS.router.callback_query(eps_AuthStates.AUTHORIZED, EpsCallback.filter(F.action == Action.ENABLE))
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
        result = response.result()
    except exceptions.ClientRequestException as e:
        await message.answer(e.error_msg)
        await state.set_state(eps_AuthStates.AUTHORIZED)
        return

    await message.answer('Включено!')
    await state.set_state(eps_AuthStates.AUTHORIZED)


@EPS.router.callback_query(EpsCallback.filter(F.action.in_(list(Action))))
async def eps_not_authorized(call: CallbackQuery):
    await call.message.edit_text('Бро, сначала тебе нужно авторизоваться. ' +
                                 'Забери свои хайповые токены в личном кабинете',
                                 reply_markup=keyboard())
    await call.answer()