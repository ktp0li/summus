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

from src.module import Module
from src.utils import add_exit_button
from src.utils import get_endpoint

VPC = Module(
    name='Virtual Private Cloud',
    router=Router(name='vpc')
)


class Action(str, Enum):
    AUTH = 'authorize'
    CREATE = 'create'
    LIST = 'list'
    EDIT = 'edit'
    REMOVE = 'remove'
    UNAUTH = 'unauthorize'


class States(StatesGroup):
    PROJECT_ID = State()
    AK = State()
    SK = State()
    AUTHORIZED = State()


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
async def main(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.AUTH))
async def vpc_auth(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введите project ID')
    await state.set_state(States.PROJECT_ID)
    await call.answer()


@VPC.router.message(States.PROJECT_ID)
async def vpc_auth_pjid(message: types.Message, state: FSMContext):
    project_id = message.text

    await state.update_data(project_id=project_id)
    await message.answer('Введите AK')
    await state.set_state(States.AK)


@VPC.router.message(States.AK)
async def vpc_auth_ak(message: types.Message, state: FSMContext):
    ak = message.text
    await state.update_data(ak=ak)
    await message.answer('Введите SK')
    await state.set_state(States.SK)


@VPC.router.message(States.SK)
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
    await state.set_state(States.AUTHORIZED)


@VPC.router.callback_query(States.AUTHORIZED, VpcCallback.filter(F.action == Action.CREATE))
async def vpc_create(call: CallbackQuery, state: FSMContext):
    await call.message.answer('VPC CREATE')
    print(await state.get_data())
    await call.answer()


@VPC.router.callback_query(States.AUTHORIZED, VpcCallback.filter(F.action == Action.LIST))
async def vpc_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: VpcAsyncClient

    request = ListVpcsRequest()
    response = client.list_vpcs_async(request)
    result = response.result() # type: ListVpcsResponse

    await call.message.answer(str(result))
    await call.answer()


@VPC.router.callback_query(VpcCallback.filter(F.action.in_(list(Action))))
async def vpc_not_authorized(call: CallbackQuery):
    await call.message.edit_text('Бро сначала тебе нужно авторизоваться. ' +
                                 'Забери свои хайповые токены в личном кабинете',
                                 reply_markup=keyboard())
    await call.answer()


@VPC.router.callback_query(VpcCallback.filter(F.action == Action.UNAUTH))
async def vpc_unauth(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text('Твои креды были почищены', reply_markup=keyboard())
    await state.clear()
    await call.answer()
