import os
from dotenv import load_dotenv
from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable

load_dotenv()
class CheckAdminMiddleware(BaseMiddleware): #outer type
    def __init__(self, dp: Dispatcher):
        self.dp = dp
        self.register_middleware()

    async def __call__(self,
                       handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, #callback or message or something
                       data: Dict[str, Any]) -> Any: #fsm or something
        if event.from_user.id == int(os.getenv('ADMIN_ID')):
            return await handler(event, data)
        return None

    def register_middleware(self):
        for event_type in [self.dp.message, self.dp.callback_query, self.dp.inline_query]:
            event_type.outer_middleware(self)
