from enum import Enum
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkces.v1 import CesAsyncClient, ListMetricsRequest, BatchListMetricDataRequest
from huaweicloudsdkces.v1 import BatchListMetricDataRequestBody, MetricInfoList, MetricsDimension
from huaweicloudsdkecs.v2 import EcsAsyncClient, ListServersDetailsRequest


from src.module import Module
from src.utils import add_exit_button
from src.globalstate import GlobalState

ENDPOINT = 'https://ces.ru-moscow-1.hc.sbercloud.ru'

CES = Module(
    name='Cloud Eye Monitoring',
    router=Router(name='ces')
)


class Action(str, Enum):
    NAT = 'show NAT metrics'
    ECS = 'show ECS metrics'
    EVS = 'show EVS disk id'


class CesCallback(CallbackData, prefix='ces'):
    action: Action


def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=CesCallback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()


@CES.router.callback_query(F.data == CES.name)
async def ces_main(call: CallbackQuery, state: FSMContext):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False

    data = await state.get_data()

    credentials = BasicCredentials(
        ak=data['ak'],
        sk=data['sk'],
        project_id=data['project_id'],
    )

    client = CesAsyncClient().new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(ENDPOINT) \
        .build()

    await state.update_data(client=client)

    await call.message.edit_reply_markup(reply_markup=keyboard())
    await call.answer()


class CesShowStates(StatesGroup):
    ECS = State()
    NAT = State()
    EVS = State()


def __metric_to_str(metric) -> str:
    text = f'<b>{metric.metric_name} ({metric.unit})</b>: {metric.datapoints}'

    return text


@CES.router.callback_query(CesCallback.filter(F.action == Action.ECS))
async def ces_show_ecs(call: CallbackQuery, state: FSMContext):
    await call.message.answer(text='Введи ECS id')
    await state.set_state(CesShowStates.ECS)
    await call.answer()


@CES.router.callback_query(CesCallback.filter(F.action == Action.NAT))
async def ces_show_nat(call: CallbackQuery, state: FSMContext):
    await call.message.answer(text='Введи NAT id')
    await state.set_state(CesShowStates.NAT)
    await call.answer()


@CES.router.callback_query(CesCallback.filter(F.action == Action.EVS))
async def ces_show_evs(call: CallbackQuery, state: FSMContext):
    await call.message.answer(text='Введи EVS disk id')
    await state.set_state(CesShowStates.EVS)
    await call.answer()


@CES.router.message(CesShowStates.ECS)
async def ces_show_ecs_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: CesAsyncClient

    ecs_id = message.text

    from_ = int((datetime.utcnow() - timedelta(minutes=5)).timestamp() * 1000)
    to = int(datetime.utcnow().timestamp() * 1000)

    metric_names = ['cpu_util', 'network_vm_connections',
                    'network_vm_newconnections']

    dimensions = [MetricsDimension(name='instance_id', value=ecs_id)]

    metrics = []
    for name in metric_names:
        metric = MetricInfoList(
            dimensions=dimensions, metric_name=name, namespace='SYS.ECS')
        metrics.append(metric)

    body = BatchListMetricDataRequestBody(
        metrics=metrics, period='300', filter='average', _from=from_, to=to)

    request = BatchListMetricDataRequest(body)
    request = client.batch_list_metric_data_async(request)
    result = request.result()

    entries = []
    for metric in result.metrics:
        entries.append(__metric_to_str(metric))

    await message.answer(text='\n'.join(entries), parse_mode='html')
    await state.set_state(GlobalState.DEFAULT)


@CES.router.message(CesShowStates.NAT)
async def ces_show_nat_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: CesAsyncClient

    nat_id = message.text

    from_ = int((datetime.utcnow() - timedelta(minutes=1)).timestamp() * 1000)
    to = int(datetime.utcnow().timestamp() * 1000)

    metric_names = ['snat_connection', 'inbound_bandwidth', 'outbound_bandwidth',
                    'inbound_traffic', 'outbound_traffic',
                    'inbound_bandwidth_ratio']

    dimensions = [MetricsDimension(name='nat_gateway_id', value=nat_id)]

    metrics = []
    for name in metric_names:
        metric = MetricInfoList(
            dimensions=dimensions, metric_name=name, namespace='SYS.NAT')
        metrics.append(metric)

    body = BatchListMetricDataRequestBody(
        metrics=metrics, period='1', filter='average', _from=from_, to=to)

    request = BatchListMetricDataRequest(body)
    request = client.batch_list_metric_data_async(request)
    result = request.result()

    entries = []
    for metric in result.metrics:
        entries.append(__metric_to_str(metric))

    await message.answer(text='\n'.join(entries), parse_mode='html')
    await state.set_state(GlobalState.DEFAULT)


@CES.router.message(CesShowStates.EVS)
async def ces_show_evs_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']  # type: CesAsyncClient

    evs_id = message.text

    from_ = int((datetime.utcnow() - timedelta(minutes=5)).timestamp() * 1000)
    to = int(datetime.utcnow().timestamp() * 1000)

    metric_names = ['disk_device_read_bytes_rate', 'disk_device_write_bytes_rate',
                    'disk_device_read_requests_rate', 'disk_device_queue_length',
                    'disk_device_write_await', 'disk_device_read_await',
                    'disk_device_io_iops_qos_num']

    dimensions = [MetricsDimension(name='disk_name', value=evs_id)]

    metrics = []
    for name in metric_names:
        metric = MetricInfoList(
            dimensions=dimensions, metric_name=name, namespace='SYS.EVS')
        metrics.append(metric)

    body = BatchListMetricDataRequestBody(
        metrics=metrics, period='300', filter='average', _from=from_, to=to)

    request = BatchListMetricDataRequest(body)
    request = client.batch_list_metric_data_async(request)
    result = request.result()

    entries = []
    for metric in result.metrics:
        entries.append(__metric_to_str(metric))

    await message.answer(text='\n'.join(entries), parse_mode='html')
    await state.set_state(GlobalState.DEFAULT)
