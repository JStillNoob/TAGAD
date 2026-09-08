from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .session_access import sessions_for_user


class EngagementConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        session_id = self.scope['url_route']['kwargs']['session_id']
        if not user.is_authenticated or not await self._can_access(user, session_id):
            await self.close(code=4403)
            return
        self.group_name = f'engagement_session_{session_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def engagement_update(self, event):
        await self.send_json({'type': 'engagement.summary', 'data': event['payload']})

    @database_sync_to_async
    def _can_access(self, user, session_id):
        return sessions_for_user(user).filter(pk=session_id).exists()
