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

    def create_ecs(self, name, flavor, image_id, subnet_id):
        return f'resource "sbercloud_compute_instance" "{name}" {{\n' +\
               f'\tname = "{name}"\n' +\
               f'\tflavor_id = "{flavor}"\n' +\
               f'\timage_id = "{image_id}"\n' +\
               '\tnetwork {\n' + \
               f'\t\tuuid = "{subnet_id}"\n' +\
               '\t}\n' +\
               '}'

    def create_image(self, name, instance_id):
        return f'resource "sbercloud_images_image" "{name}" {{\n' +\
               f'\tname = "{name}"\n' +\
               f'\towner = "{instance_id}"\n' +\
               '}'

    def create_nat_gateway(self, name, desc, spec, router_id, internal_network_id, proj_id):
        return f'resource "sbercloud_nat_gateway" "{name}" {{\n' +\
               f'\tname = "{name}"\n' +\
               f'\tdescription = "{desc}"\n' +\
               f'\tspec = "{spec}"\n' +\
               f'\trouter_id = "{router_id}"\n' +\
               f'\tinternal_network_id = "{internal_network_id}"\n' +\
               f'\tenterprise_project_id = "{proj_id}"\n' +\
               '}'
