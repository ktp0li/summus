from src.modules import modules
import os

from aiogram import Dispatcher, Bot
from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkvpc.v2 import *
from huaweicloudsdkeps.v1 import (EpsAsyncClient)

def test_bot(): Bot(token=os.getenv('TOKEN'))

def test_modules(): assert(len(modules) >= 1)

def test_auth_vpc():
    bot_token = os.getenv('TOKEN')
    ak = os.getenv('AK')
    sk = os.getenv('SK')
    project_id = os.getenv('PROJECT_ID')
    account_id = os.getenv('ACCOUNT_ID')
    endpoint = 'https://vpc.ru-moscow-1.hc.sbercloud.ru'
    assert(bot_token and ak and sk and project_id and account_id)
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = True
    credentials = BasicCredentials(ak, sk, project_id)

    vpc_client = VpcClient.new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    request = ListVpcsRequest(limit=1)
    response = vpc_client.list_vpcs(request)

def test_auth_eps():
    bot_token = os.getenv('TOKEN')
    ak = os.getenv('AK')
    sk = os.getenv('SK')
    project_id = os.getenv('PROJECT_ID')
    account_id = os.getenv('ACCOUNT_ID')
    endpoint = 'https://eps.ru-moscow-1.hc.sbercloud.ru'
    assert(bot_token and ak and sk and project_id and account_id)
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = True
    credentials = GlobalCredentials(ak, sk, domain_id=account_id)

    eps_client = EpsAsyncClient.new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    request = ListVpcsRequest(limit=1)
    response = eps_client.list_enterprise_project_async(request)
