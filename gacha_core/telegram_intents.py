"""PostgreSQL-bound Telegram spin buttons, opaque IDs and durable outbox.

Only Telegram's authenticated message/callback update is used for user identity.
No callback payload can specify a rarity, card ID or destination chat.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from gacha_core.domain import GameCore, GameError, SpinResult, _telegram_id


class InvalidCallback(GameError):
    pass


@dataclass(frozen=True)
class SpinIntent:
    intent_id: UUID
    telegram_user_id: int
    chat_id: int
    message_id: int | None
    state: str


class SpinIntentService:
    def __init__(self, db, *, game: GameCore | None = None):
        self.db = db
        self.game = game or GameCore(db)

    def prepare(self, telegram_user_id: int, chat_id: int, *, now: datetime | None = None) -> SpinIntent:
        uid = _telegram_id(telegram_user_id)
        if _telegram_id(chat_id) != uid:
            raise InvalidCallback('Only user-owned private chats are supported')
        timestamp = now or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError('Expected an aware datetime')
        status = self.game.profile(uid,now=timestamp)
        intent_id = uuid4()
        expires = timestamp + timedelta(minutes=15)
        with self.db.transaction():
            self.db.execute('INSERT INTO gacha.telegram_spin_intents '
                            '(intent_id,player_id,telegram_user_id,chat_id,created_at,expires_at) '
                            'VALUES (%s,%s,%s,%s,%s,%s)',
                            (intent_id,status.player_id,uid,chat_id,timestamp,expires))
        return SpinIntent(intent_id,uid,chat_id,None,'prepared')

    def bind_message(self, intent_id: UUID, telegram_user_id: int, chat_id: int,
                     message_id: int, *, now: datetime | None = None) -> None:
        uid = _telegram_id(telegram_user_id)
        if _telegram_id(chat_id) != uid or type(message_id) is not int or message_id <= 0:
            raise InvalidCallback('Invalid original chat or message')
        timestamp = now or datetime.now(timezone.utc)
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute('UPDATE gacha.telegram_spin_intents SET message_id=%s,state=%s '
                            'WHERE intent_id=%s AND telegram_user_id=%s AND chat_id=%s '
                            'AND state=%s AND expires_at>%s',
                            (message_id,'ready',intent_id,uid,chat_id,'prepared',timestamp))
                if cur.rowcount != 1:
                    raise InvalidCallback('Spin button was already bound or expired')

    def commit_callback(self, intent_id: UUID, telegram_user_id: int,
                        chat_id: int, message_id: int, *, now: datetime | None = None) -> SpinResult:
        uid = _telegram_id(telegram_user_id)
        if _telegram_id(chat_id) != uid or type(message_id) is not int or message_id <= 0:
            raise InvalidCallback('Callback did not originate from owner private chat')
        timestamp = now or datetime.now(timezone.utc)
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute('SELECT telegram_user_id,chat_id,message_id,state,expires_at '
                            'FROM gacha.telegram_spin_intents WHERE intent_id=%s FOR UPDATE',
                            (intent_id,))
                entry = cur.fetchone()
                if entry is None or tuple(entry[:3]) != (uid,chat_id,message_id):
                    raise InvalidCallback('Callback is not bound to this user and message')
                _,_,_,state,expires = entry
                if state not in ('ready','committed') or (state=='ready' and timestamp >= expires):
                    raise InvalidCallback('Button is no longer available')
                result = self.game.spin(uid,intent_id,now=timestamp)
                if state=='ready':
                    cur.execute('UPDATE gacha.telegram_spin_intents SET state=%s,spin_id=%s '
                                'WHERE intent_id=%s AND state=%s',
                                ('committed',result.spin_id,intent_id,'ready'))
                    if cur.rowcount != 1:
                        raise InvalidCallback('Concurrent callback already committed')
                elif not result.replay:
                    raise InvalidCallback('Committed intent lost matching spin')
                return result

    def start_delivery(self, spin_id: UUID) -> bool:
        """Persist uncertainty BEFORE any network send; never auto-retry uncertain."""
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute('SELECT state FROM gacha.delivery_outbox '
                            'WHERE spin_id=%s FOR UPDATE', (spin_id,))
                item = cur.fetchone()
                if item is None:
                    raise GameError('Committed spin does not have a delivery outbox entry')
                if item[0] != 'pending':
                    return False
                cur.execute('UPDATE gacha.delivery_outbox SET state=%s,updated_at=now() '
                            'WHERE spin_id=%s', ('uncertain',spin_id))
                return True

    def finish_delivery(self, spin_id: UUID, wheel_message_id: int,
                        card_message_id: int) -> None:
        if (type(wheel_message_id) is not int or wheel_message_id <= 0 or
                type(card_message_id) is not int or card_message_id <= 0):
            raise GameError('Cannot acknowledge unknown Telegram media messages')
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute('UPDATE gacha.delivery_outbox SET state=%s, '
                            'wheel_message_id=%s,card_message_id=%s,telegram_message_id=%s, '
                            'updated_at=now() WHERE spin_id=%s AND state=%s',
                            ('sent',wheel_message_id,card_message_id,card_message_id,spin_id,'uncertain'))
                if cur.rowcount != 1:
                    raise GameError('Delivery was not claimed by this process')

    def recent_spins(self, telegram_user_id: int, *, limit: int = 8):
        uid = _telegram_id(telegram_user_id)
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError('Invalid history length')
        with self.db.cursor() as cur:
            cur.execute('SELECT s.rarity,c.title,s.created_at,s.card_id '
                        'FROM gacha.spins s '
                        'JOIN gacha.players p ON p.id=s.player_id '
                        'JOIN gacha.cards c ON c.card_id=s.card_id '
                        'WHERE p.telegram_user_id=%s ORDER BY s.created_at DESC,s.spin_id DESC LIMIT %s',
                        (uid,limit))
            return cur.fetchall()
