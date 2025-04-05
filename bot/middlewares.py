import os
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject

ADMIN_ID = int(os.getenv("ADMIN_ID"))


class CheckAdminMiddleware(BaseMiddleware):
    def __init__(self, dp: Dispatcher) -> None:
        self.dp = dp
        self._register_middleware()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,  # callback or message or something
        data: Dict[str, Any],  # fsm or something
    ) -> Any:
        if event.from_user.id == ADMIN_ID:
            return await handler(event, data)
        return None

    def _register_middleware(self) -> None:
        for event_type in [
            self.dp.message,
            self.dp.callback_query,
            self.dp.inline_query,
        ]:
            event_type.outer_middleware(self)
