"""PostgreSQL-backed authoritative daily attempts / collectible-card game core.

Usage: give GameCore a psycopg3 connection in autocommit mode. Every operation
starts an explicit transaction; all mutation and replay detection occurs while
holding a row lock on the player. No Telegram, worker or event scheduler here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import secrets
from typing import Callable
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

DAILY_LIMIT = 10
MSK = ZoneInfo('Europe/Moscow')
ODDS = (('Classic', 25), ('Elite', 22), ('Royal', 19),
        ('Epic', 16), ('Mythic', 11), ('Eternal', 7))
assert sum(weight for _, weight in ODDS) == 100

class GameError(Exception):
    """An expected, safe game-level rejection; no network or secret details."""

class InsufficientAttempts(GameError):
    pass

class MissingActiveCards(GameError):
    pass

class BlockedPlayer(GameError):
    pass

@dataclass(frozen=True)
class PlayerStatus:
    player_id: int
    game_day: date
    daily_remaining: int
    bonus_remaining: int
    wallet_balance: int

@dataclass(frozen=True)
class SpinResult:
    spin_id: UUID
    player_id: int
    request_id: UUID
    game_day: date
    attempt_kind: str
    rarity: str
    card_id: str
    replay: bool


def game_day_moscow(now: datetime) -> date:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Expected timezone-aware datetime')
    return now.astimezone(MSK).date()


def choose_rarity(roll: int) -> str:
    if type(roll) is not int or not 0 <= roll < 100:
        raise ValueError('Expected integer roll from 0 to 99')
    for name, weight in ODDS:
        roll -= weight
        if roll < 0:
            return name
    raise RuntimeError('Odds total invalid')


def _uuid(value: UUID | str) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Request ID must be UUID') from None


def _telegram_id(telegram_user_id: int) -> int:
    if type(telegram_user_id) is not int or not 0 < telegram_user_id <= 9223372036854775807:
        raise ValueError('Telegram user ID must be positive int64')
    return telegram_user_id


def _at(now: datetime | None) -> datetime:
    timestamp = now if now is not None else datetime.now(timezone.utc)
    game_day_moscow(timestamp)
    return timestamp


class GameCore:
    def __init__(self, connection, *, rng: Callable[[int], int] = secrets.randbelow):
        self.db = connection
        self.rng = rng

    @staticmethod
    def _lock_player(cursor, telegram_user_id: int) -> int:
        cursor.execute('INSERT INTO gacha.players (telegram_user_id) VALUES (%s) '
                       'ON CONFLICT (telegram_user_id) DO NOTHING', (telegram_user_id,))
        cursor.execute('SELECT id, is_blocked FROM gacha.players '
                       'WHERE telegram_user_id = %s FOR UPDATE', (telegram_user_id,))
        player_id, blocked = cursor.fetchone()
        if blocked:
            raise BlockedPlayer('Account is blocked')
        cursor.execute('INSERT INTO gacha.bonus_attempts (player_id) VALUES (%s) '
                       'ON CONFLICT DO NOTHING', (player_id,))
        cursor.execute('INSERT INTO gacha.wallets (player_id) VALUES (%s) '
                       'ON CONFLICT DO NOTHING', (player_id,))
        return player_id

    @staticmethod
    def _sync_daily(cursor, player_id: int, day: date) -> None:
        # The player row lock serializes even different worker processes.
        cursor.execute('INSERT INTO gacha.daily_attempts (player_id, game_day, remaining) '
                       'VALUES (%s,%s,%s) '
                       'ON CONFLICT (player_id) DO UPDATE '
                       'SET game_day = EXCLUDED.game_day, '
                       'remaining = EXCLUDED.remaining, updated_at = now() '
                       'WHERE gacha.daily_attempts.game_day < EXCLUDED.game_day',
                       (player_id, day, DAILY_LIMIT))
        if cursor.rowcount == 1:
            cursor.execute('INSERT INTO gacha.daily_grant_audit '
                           '(player_id, game_day, amount) VALUES (%s,%s,%s) '
                           'ON CONFLICT DO NOTHING', (player_id, day, DAILY_LIMIT))

    @staticmethod
    def _status(cursor, player_id: int) -> PlayerStatus:
        cursor.execute('SELECT d.game_day, d.remaining, b.remaining, w.balance '
                       'FROM gacha.daily_attempts d '
                       'JOIN gacha.bonus_attempts b USING (player_id) '
                       'JOIN gacha.wallets w USING (player_id) '
                       'WHERE d.player_id = %s', (player_id,))
        day, daily, bonus, wallet = cursor.fetchone()
        return PlayerStatus(player_id, day, daily, bonus, wallet)

    def profile(self, telegram_user_id: int, *, now: datetime | None = None) -> PlayerStatus:
        _telegram_id(telegram_user_id)
        today = game_day_moscow(_at(now))
        with self.db.transaction():
            with self.db.cursor() as cur:
                player_id = self._lock_player(cur, telegram_user_id)
                self._sync_daily(cur, player_id, today)
                return self._status(cur, player_id)

    def spin(self, telegram_user_id: int, request_id: UUID | str,
             *, now: datetime | None = None) -> SpinResult:
        _telegram_id(telegram_user_id)
        rid = _uuid(request_id)
        today = game_day_moscow(_at(now))
        with self.db.transaction():
            with self.db.cursor() as cur:
                player_id = self._lock_player(cur, telegram_user_id)
                cur.execute('SELECT spin_id, game_day, attempt_kind, rarity, card_id '
                            'FROM gacha.spins WHERE player_id = %s AND client_request_id = %s',
                            (player_id, rid))
                previous = cur.fetchone()
                if previous is not None:
                    sid, day, source, rarity, card_id = previous
                    return SpinResult(sid, player_id, rid, day, source, rarity, card_id, True)
                self._sync_daily(cur, player_id, today)
                status = self._status(cur, player_id)
                if status.game_day != today:
                    raise GameError('Out-of-order game clock; current day is newer')
                if status.daily_remaining > 0:
                    spent_from = 'daily'
                elif status.bonus_remaining > 0:
                    spent_from = 'bonus'
                else:
                    raise InsufficientAttempts('No daily or bonus attempts available')
                rarity = choose_rarity(self.rng(100))
                cur.execute("SELECT card_id FROM gacha.cards WHERE kind = 'standard' "
                            'AND is_active AND drop_key = %s AND rarity = %s ORDER BY card_id',
                            ('main', rarity))
                card_ids = [row[0] for row in cur.fetchall()]
                if not card_ids:
                    raise MissingActiveCards('No approved active cards for selected rarity')
                index = self.rng(len(card_ids))
                if type(index) is not int or not 0 <= index < len(card_ids):
                    raise ValueError('Invalid RNG result')
                card_id = card_ids[index]
                if spent_from == 'daily':
                    cur.execute('UPDATE gacha.daily_attempts SET remaining = remaining - 1, '
                                'updated_at = now() WHERE player_id = %s AND remaining > 0', (player_id,))
                else:
                    cur.execute('UPDATE gacha.bonus_attempts SET remaining = remaining - 1, '
                                'updated_at = now() WHERE player_id = %s AND remaining > 0', (player_id,))
                if cur.rowcount != 1:
                    raise InsufficientAttempts('Attempt no longer available')
                sid = uuid4()
                cur.execute('INSERT INTO gacha.spins '
                            '(spin_id, player_id, client_request_id, game_day, attempt_kind, rarity, card_id) '
                            'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                            (sid, player_id, rid, today, spent_from, rarity, card_id))
                cur.execute('INSERT INTO gacha.player_cards (player_id, card_id, quantity) '
                            'VALUES (%s,%s,1) ON CONFLICT (player_id, card_id) DO UPDATE '
                            'SET quantity = gacha.player_cards.quantity + 1, last_obtained_at = now()',
                            (player_id, card_id))
                cur.execute('INSERT INTO gacha.delivery_outbox (spin_id) VALUES (%s)', (sid,))
                return SpinResult(sid, player_id, rid, today, spent_from, rarity, card_id, False)

    def grant_bonus(self, telegram_user_id: int, request_id: UUID | str, amount: int,
                    reason: str) -> int:
        """Internal trusted-service operation. Never bind directly to Telegram callbacks.

        Authentication/roles belong in the future admin transport layer.
        """
        _telegram_id(telegram_user_id)
        rid = _uuid(request_id)
        if type(amount) is not int or not 1 <= amount <= 1_000_000:
            raise ValueError('Bonus amount out of range')
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 300:
            raise ValueError('Reason required')
        with self.db.transaction():
            with self.db.cursor() as cur:
                pid = self._lock_player(cur, telegram_user_id)
                cur.execute('SELECT player_id, amount, reason FROM gacha.bonus_grants '
                            'WHERE request_id = %s', (rid,))
                prior = cur.fetchone()
                if prior:
                    if prior != (pid, amount, reason):
                        raise GameError('Duplicate grant key with different parameters')
                else:
                    cur.execute('INSERT INTO gacha.bonus_grants '
                                '(request_id, player_id, amount, reason) VALUES (%s,%s,%s,%s)',
                                (rid, pid, amount, reason))
                    cur.execute('UPDATE gacha.bonus_attempts SET remaining = remaining + %s, '
                                'updated_at = now() WHERE player_id = %s', (amount, pid))
                cur.execute('SELECT remaining FROM gacha.bonus_attempts WHERE player_id = %s', (pid,))
                return cur.fetchone()[0]

    def collection(self, telegram_user_id: int) -> list[tuple[str, str, str | None, int]]:
        """Read inventory; a non-player gets an empty list and is NOT registered."""
        _telegram_id(telegram_user_id)
        with self.db.cursor() as cur:
            cur.execute('SELECT c.card_id, c.kind, c.rarity, pc.quantity '
                        'FROM gacha.players p JOIN gacha.player_cards pc ON p.id=pc.player_id '
                        'JOIN gacha.cards c ON c.card_id=pc.card_id '
                        'WHERE p.telegram_user_id=%s ORDER BY c.kind,c.rarity,c.card_id',
                        (telegram_user_id,))
            return cur.fetchall()
