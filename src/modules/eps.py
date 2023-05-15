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

class AuthStates(StatesGroup):
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
    await call.message.answer('Введите account ID')
    await state.set_state(AuthStates.ACCOUNT_ID)
    await call.answer()


@EPS.router.message(AuthStates.ACCOUNT_ID)
async def eps_auth_pjid(message: types.Message, state: FSMContext):
    account_id = message.text

    await state.update_data(account_id=account_id)
    await message.answer('Введите AK')
    await state.set_state(AuthStates.AK)


@EPS.router.message(AuthStates.AK)
async def eps_auth_ak(message: types.Message, state: FSMContext):
    ak = message.text
    await state.update_data(ak=ak)
    await message.answer('Введите SK')
    await state.set_state(AuthStates.SK)

@EPS.router.message(AuthStates.SK)
async def eps_auth_sk(message: types.Message, state: FSMContext):
    sk = message.text
    await state.update_data(sk=sk)
    await message.answer('батя грит малаца. Ща проверим твои креды')

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
