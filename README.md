# summus

> summus - от лат. высочайний, верховный

## Что это?

Телеграм бот для работы с [~~Sber~~Cloud](https://cloud.ru). Позволяет управлять виртуальными машинами, хранилищами, сетями, образами и прочими сущностями, предоставляемыми [~~Sber~~Cloud](https://cloud.ru).

## Установка и запуск
<details>
	<summary>Переменные окружения</summary>

- `TOKEN` - токен Telegram бота

</details>

### Docker
```bash
docker-compose up
```
### Standalone
```bash
pip3 install -r requirements.txt
```
```bash
python3 -m src
```

## Поддерживаемые сервисы

- Elastic Cloud Server
- Enterprise Management
- NAT Gateway
- Virtual Private Cloud
- Subnet
- Image Management Service

## Roadmap

- [x] Создать минимального бота с базовыми возможностями управления ресурсами:
- - [x] ESC
- - [x] EPS
- - [x] NAT
- - [x] VPC
- - [x] IMS
- - [x] Subnet
- [x] Написать несколько тестов, которые покроют базовые аспекты работы бота
------
- [ ] Покрыть ботом больше сервисов ~~Sber~~Cloud
- [ ] Сделать более удобную систему авторизации
- [ ] Сделать более user-friendly интерфейс (предоставлять опцию выбора ресурса из имеющихся, когда есть возможность)

## Требования

### Функциональные

- [x] Можно создавать, редактировать, удалять как минимум пять типов ресурсов.
- [x] Можно получать информацию о доступных конфигурациях ресуров.
- [ ] Выгрузка отчёта по всем потребляемым ресурсам.
- [ ] Возможность получить сгенерированный терраформ-код для ресурса вместо создания.
- [X] Есть мониторинг ресурса.

### Нефункциональные

- [x] Использован SDK.
- [x] Авторизация с возможностью контроля прав доступа и грамотная обработка отсутствия у бота прав.
- [x] Несложно добавить поддержку нового сервиса.
- [x] Код покрыт тестами.

## Документация

### Как добавлять новые модули?

Модуль работает с запросами к SDK через библиотеку [`aiogram`](https://aiogram.dev). Чтобы написать новый модуль необходимо выбрать сервис (неожиданно), который имеет [Endpoint](https://support.hc.sbercloud.ru/en-us/endpoint/index.html) и соответственно [SDK HuaweiCloud](https://console-intl.huaweicloud.com/apiexplorer/#/openapi/) (SDK HuaweiCloud совместим с ~~Sber~~Cloud). Используя примеры кода, которые предлагается в SDK,  [репозитории SDK](https://github.com/huaweicloud/huaweicloud-sdk-python-v3#huawei-cloud-python-software-development-kit-python-sdk) и в уже [реализованных модулях](/src/modules/), несложно написать новый модуль.

#### Пример модуля (этот модуль не взаимодействует с HuaweiCloud)

Файл: `src/modules/<MODULE_SHORT_NAME_LOWERCASE>.py`

```Python
from enum import Enum

from aiogram import F, Router, types
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.module import Module
from src.utils import add_exit_button


# Объявление модуля
<MODULE_SHORT_NAME> = Module(
    name='<MODULE_PRETTY_NAME>',
    router=Router(name='<MODULE_SHORT_NAME>')
)

# Список действий модуля
class Action(str, Enum):
    CREATE = 'create'
    LIST = 'list'
    SHOW = 'show'
    <CUSTOM_ACTION> = '<CUSTOM_PRETTY_ACTION>'

class <MODULE_SHORT_NAME>Callback(CallbackData, prefix='<MODULE_SHORT_NAME>'):
    action: Action

def keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for action in Action:
        builder.button(
            text=action.value.title(),
            callback_data=<MODULE_SHORT_NAME>Callback(action=action.value),
        )

    add_exit_button(builder)
    builder.adjust(2)

    return builder.as_markup()

# Действие модуля
@<MODULE_SHORT_NAME>.router.callback_query(<MODULE_SHORT_NAME>Callback.filter(F.action == Action.<CUSTOM_ACTION>))
async def CUSTOM_ACTION(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Hello, world!')
    await call.answer()
```

Файл: `src/modules/__init__.py`

```Python
from .vpc import VPC
from .eps import EPS
from .subnet import SUBNET
from .nat import NAT
from .ecs import ECS
from .<MODULE_SHORT_NAME_LOWERCASE> import <MODULE_SHORT_NAME>

modules = (EPS, VPC, SUBNET, NAT, ECS, <MODULE_SHORT_NAME>)
```

Итог:

![Screenshot of example module](/img/module_example.jpeg)

Пример взаимодействия с SDK см. в [src/modules](/src/modules)

## Тестирование

Для тестирования проекта используются библиотеки `pytest`

<details>
	<summary>Переменные окружения для тестирования</summary>

- `TOKEN` - токен Telegram бота
- `AK` - Access Key Id
- `SK` - Secret Access Key
- `PROJECT_ID`
- `ACCOUNT_ID`

</details>

```bash
pytest src/test.py
```

--------

## К проекту приложили руки

- [beshenkaD](https://github.com/beshenkaD)
- [ktp0li](https://github.com/ktp0li)
- [ivabus](https://github.com/ivabus)

## Лицензия

Проект лицензируется под [GNU GPLv3](/LICENSE).