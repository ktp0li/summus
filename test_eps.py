from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig

from huaweicloudsdkeps.v1 import EpsAsyncClient, ListEnterpriseProjectRequest, CreateEnterpriseProjectRequest, EnterpriseProject, EnableEnterpriseProjectRequest, EnableAction, DisableAction, DisableEnterpriseProjectRequest
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

def create_enterprise_project(client):
    try:
        request = CreateEnterpriseProjectRequest()
        request.body = EnterpriseProject('puk11', 'kak')
        response = client.create_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)

def enable_enterprise_project(client):
    try:
        request = EnableEnterpriseProjectRequest(enterprise_project_id="6fe88c4f-be76-4c61-ae3d-a6ff15d4bf5a")
        request.body = EnableAction('enable')
        response = client.enable_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)

def disable_enterprise_project(client):
    try:
        request = DisableEnterpriseProjectRequest(enterprise_project_id="6fe88c4f-be76-4c61-ae3d-a6ff15d4bf5a")
        request.body = DisableAction('disable')
        response = client.disable_enterprise_project_async(request)
        result = response.result()
        print(result)
    except exceptions.ClientRequestException as exc:
        handle(exc)


if __name__ == "__main__":
    ak = "E7LTLBACONTPGAZ1QSCF"
    sk = "UJDZN8EMV82p9oEk98m6bdhOdpmE5iaN3W7mNK5P"
    #project_id = "b4df643b9d8e44a58b64605519482245"
    account_id = '1e8824275f4946b0a1d26591ab3f8f03'
    endpoint = "https://eps.ru-moscow-1.hc.sbercloud.ru"

    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False
    credentials = GlobalCredentials(ak, sk, account_id)

    eps_client = EpsAsyncClient.new_builder() \
    .with_http_config(config) \
    .with_credentials(credentials) \
    .with_endpoint(endpoint) \
    .build()

    list_enterprise_project(eps_client)
    enable_enterprise_project(eps_client)
