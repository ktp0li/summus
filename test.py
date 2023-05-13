from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
# import specified service library huaweicloudsdk{service}, take vpc for example
from huaweicloudsdkvpc.v2 import *


def handle(e):
    print(e.status_code)
    print(e.request_id)
    print(e.error_code)
    print(e.error_msg)


def show_vpc(client: VpcClient, vpc_id):
    try:
        request = ShowVpcRequest(vpc_id=vpc_id)
        response = client.show_vpc(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        handle(exc)


def delete_vpc(client: VpcClient, vpc_id):
    try:
        request = DeleteVpcRequest(vpc_id=vpc_id)
        response = client.delete_vpc(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        handle(exc)


def list_vpc(client: VpcClient):
    try:
        request = ListVpcsRequest(limit=1)
        response = client.list_vpcs(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        handle(exc)


def create_vpc(client: VpcClient, cidr, name, description, enterprise_project_id):
    try:
        vpc = CreateVpcOption(
            cidr=cidr,
            name=name,
            description=description,
            enterprise_project_id=enterprise_project_id
        )

        body = CreateVpcRequestBody(vpc)
        request = CreateVpcRequest(body)
        response = client.create_vpc(request)
        print(response)
    except exceptions.ClientRequestException as exc:
        handle(exc)


if __name__ == "__main__":
    ak = ""
    sk = ""
    endpoint = "https://vpc.ru-moscow-1.hc.sbercloud.ru"
    project_id = ""

    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = False
    credentials = BasicCredentials(ak, sk, project_id)

    vpc_client = VpcClient.new_builder() \
        .with_http_config(config) \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

    list_vpc(vpc_client)
