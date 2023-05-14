from dataclasses import dataclass
from aiogram import Router


@dataclass
class Module():
    name: str
    router: Router
