class TerraformCreate:
    def create_vpc(self, name, cidr, desc, ent_proj_id):
        return f'resource "sbercloud_vpc" "{name}" {{\n' +\
               f'\tname = "{name}"\n' +\
               f'\tcidr = "{cidr}"\n' +\
               f'\tdescription = "{desc}"\n' +\
               f'\tenterprise_project_id = "{ent_proj_id}"\n' +\
               '}'

    def create_subnet(self, name, cidr, gateway, vpc_id):
        return f'resource "sbercloud_vpc_subnet" "{name}" {{\n' +\
               f'\tname = "{name}"\n' +\
               f'\tcidr = "{cidr}"\n' +\
               f'\tgateway_ip = "{gateway}"\n' +\
               f'\tvpc_id = "{vpc_id}"\n' +\
               '}'

    def create_enterprise_project(self, name, desc):
        return f'resource "sbercloud_enterprise_project" "{name}" {{\n' +\
               f'\tname = "{name}"\n' +\
               f'\tdescription = "{desc}"\n' +\
               '}'