from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig

from huaweicloudsdkeps.v1 import EpsAsyncClient, ListEnterpriseProjectRequest, CreateEnterpriseProjectRequest, EnterpriseProject,\
    EnableEnterpriseProjectRequest, EnableAction, DisableAction, DisableEnterpriseProjectRequest, UpdateEnterpriseProjectRequest
def handle(e):
    print(e.status_code)
    print(e.request_id)
    print(e.error_code)
    print(e.error_msg)

def list_enterprise_project(client):
    try:
        request = ListEnterpriseProjectRequest()
        response = client.list_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)

def create_enterprise_project(client, name, desc, proj_type):
    try:
        request = CreateEnterpriseProjectRequest()
        request.body = EnterpriseProject(name, desc, proj_type)
        response = client.create_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)

def enable_enterprise_project(client, project_id):
    try:
        request = EnableEnterpriseProjectRequest(enterprise_project_id=project_id)
        request.body = EnableAction('enable')
        response = client.enable_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)

def disable_enterprise_project(client, project_id):
    try:
        request = DisableEnterpriseProjectRequest(enterprise_project_id=project_id)
        request.body = DisableAction('disable')
        response = client.disable_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)

def update_enterprise_project(client, project_id, name, desc, proj_type):
    try:
        request = UpdateEnterpriseProjectRequest(enterprise_project_id=project_id)
        request.body = EnterpriseProject(name, desc, proj_type)
        response = client.update_enterprise_project_async(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        handle(exc)

if __name__ == "__main__":
    ak = ''
    sk = ''
    account_id = ''
    endpoint = 'https://eps.ru-moscow-1.hc.sbercloud.ru'
    enterprise_project_id = ''

    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False
    credentials = GlobalCredentials(ak, sk, account_id)

    eps_client = EpsAsyncClient.new_builder() \
    .with_http_config(config) \
    .with_credentials(credentials) \
    .with_endpoint(endpoint) \
    .build()

    list_enterprise_project(eps_client)
