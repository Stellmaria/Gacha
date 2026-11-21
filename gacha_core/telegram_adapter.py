"""User-facing ordinary Telegram chat adapter for the Gacha PostgreSQL core.

No network calls until the operator explicitly invokes the runtime. Tests
inject fake TelegramClient. The wheel stays the exact owner-approved MP4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from uuid import UUID

from gacha_core import GameCore, GameError, MissingActiveCards, InsufficientAttempts
from gacha_core.card_store import approved_cards, image_for_card, CardAssetError
from gacha_core.telegram_intents import SpinIntentService, InvalidCallback
from gacha_core.telegram_api import api
from scripts.telegram_royal_mp4_smoke import send_media, load_approved_media
from scripts.telegram_wheel6_smoke import (edit_to_animation, send_animation_fallback,
                                          MediaReplacementRejected, video_bytes)

SPIN_PREFIX = 'g1:spin:'
CAPTION_SPINNING = '✦ Колесо вращается…\nРезультат будет показан после остановки.'
REVEAL_DELAY = 12.0
MAIN_MENU = {'keyboard': [[{'text':'🎡 Крутить колесо'}, {'text':'🃏 Моя коллекция'}],
                          [{'text':'👤 Мой профиль'}, {'text':'📜 История'}]],
             'resize_keyboard':True,'is_persistent':True}


@dataclass(frozen=True)
class TelegramOutcome:
    handled: bool
    category: str


class TelegramClient:
    def __init__(self, token: str):
        self.token = token

    def send_text(self, chat_id: int, message: str, *, menu: bool = False) -> dict:
        data = {'chat_id':chat_id,'text':message}
        if menu:data['reply_markup']=MAIN_MENU
        return api(self.token,'sendMessage',data)

    def send_cover(self, chat_id: int, caption: str, callback_data: str) -> dict:
        cover,_=load_approved_media()
        return send_media(self.token,chat_id,'sendPhoto',cover,caption,
                          reply_markup={'inline_keyboard':[[{'text':'✦ Крутить колесо',
                                                              'callback_data':callback_data}]]})

    def acknowledge(self, callback_id: str, message: str) -> None:
        api(self.token,'answerCallbackQuery',{'callback_query_id':callback_id,'text':message,
                                              'show_alert':False})

    def disable_button(self, chat_id: int, message_id: int) -> None:
        api(self.token,'editMessageReplyMarkup',{'chat_id':chat_id,
                                                 'message_id':message_id,
                                                 'reply_markup':{'inline_keyboard':[]}})

    def show_wheel(self, chat_id: int, cover_message_id: int, rarity: str) -> int:
        raw=video_bytes(rarity)
        try:
            result=edit_to_animation(self.token,chat_id,cover_message_id,rarity,raw,
                                     caption=CAPTION_SPINNING)
        except MediaReplacementRejected:
            result=send_animation_fallback(self.token,chat_id,rarity,raw,
                                           caption=CAPTION_SPINNING)
        return result['message_id']

    def reveal_rarity(self, chat_id: int, message_id: int, rarity: str) -> None:
        result=api(self.token,'editMessageCaption',{
            'chat_id':chat_id, 'message_id':message_id,
            'caption':f'✦ {rarity.upper()} ✦\nКолесо остановилось. Карта сохранена в коллекции.'})
        if not isinstance(result,dict) or result.get('message_id') != message_id:
            raise GameError('Telegram did not acknowledge the rarity caption')

    def send_card(self, chat_id: int, card_id: str, private_root: str | Path) -> int:
        record=next((c for c in approved_cards() if c['card_id']==card_id),None)
        if record is None:raise CardAssetError('Unknown result card')
        png=image_for_card(private_root,card_id)
        label=f"✦ Получена карта №{record['number']:02d} · {record['rarity']} ✦\n{record['title']}"
        result=send_media(self.token,chat_id,'sendPhoto',png,label)
        return result['message_id']


class TelegramGameAdapter:
    def __init__(self, db, telegram: TelegramClient, private_root: str | Path,
                 *, sleeper=time.sleep, game: GameCore | None = None):
        self.db=db
        self.telegram=telegram
        self.private_root=private_root
        self.sleeper=sleeper
        self.game=game or GameCore(db)
        self.intents=SpinIntentService(db,game=self.game)

    def _profile_text(self, user_id: int, now: datetime) -> str:
        p=self.game.profile(user_id,now=now)
        return (f'✦ Velvet Gacha ✦\nЕжедневные попытки: {p.daily_remaining}/10\n'
                f'Бонусные попытки: {p.bonus_remaining}\n'
                f'Вельветы: {p.wallet_balance}\nОбновление: 00:00 МСК')

    def _collection_text(self, user_id: int) -> str:
        rows=self.game.collection(user_id)
        if not rows:return '✦ Моя коллекция ✦\nПока пусто. Крутите колесо, чтобы получить первую карту.'
        catalog={c['card_id']:c for c in approved_cards()}
        lines=['✦ Моя коллекция ✦']
        for card_id,kind,rarity,count in rows[:50]:
            record=catalog.get(card_id)
            label=(f"№{record['number']:02d} · {record['title']}" if record else card_id)
            grade=rarity if kind=='standard' else 'Velvet · ивент'
            lines.append(f'{grade} · {label} ×{count}')
        return '\n'.join(lines)

    def _history_text(self,user_id: int) -> str:
        spins=self.intents.recent_spins(user_id)
        if not spins:return '✦ История ✦\nПока нет вращений.'
        return '✦ История ✦\n'+'\n'.join(
            f'{rarity} · {title}' for rarity,title,_,_ in spins)

    def handle_update(self, update: dict, *, now: datetime | None = None) -> TelegramOutcome:
        timestamp=now or datetime.now(timezone.utc)
        if not isinstance(update,dict):return TelegramOutcome(False,'invalid')
        msg=update.get('message')
        if isinstance(msg,dict):
            sender,chat=msg.get('from'),msg.get('chat')
            if (not isinstance(sender,dict) or not isinstance(chat,dict) or
                    sender.get('is_bot') is not False or chat.get('type')!='private' or
                    type(sender.get('id')) is not int or sender['id']!=chat.get('id')):
                return TelegramOutcome(False,'not_private')
            uid=sender['id'];text=msg.get('text')
            if not isinstance(text,str):return TelegramOutcome(False,'not_text')
            if text in ('/start','👤 Мой профиль','/profile'):
                self.telegram.send_text(uid,self._profile_text(uid,timestamp),menu=True)
                return TelegramOutcome(True,'profile')
            if text in ('/cards','🃏 Моя коллекция'):
                self.telegram.send_text(uid,self._collection_text(uid))
                return TelegramOutcome(True,'collection')
            if text in ('/history','📜 История'):
                self.telegram.send_text(uid,self._history_text(uid))
                return TelegramOutcome(True,'history')
            if text in ('/spin','🎡 Крутить колесо'):
                # Ensure all approved cards are present BEFORE creating spendable button.
                # This is a heavy first-MVP safety check, but never spends an attempt.
                from gacha_core.card_store import verify_private_cards
                verify_private_cards(self.private_root)
                prepared=self.intents.prepare(uid,uid,now=timestamp)
                data=SPIN_PREFIX+prepared.intent_id.hex
                status=self.game.profile(uid,now=timestamp)
                cover=self.telegram.send_cover(uid,
                     f'✦ Колесо судьбы ✦\nЕжедневные: {status.daily_remaining}/10 · '
                     f'Бонусные: {status.bonus_remaining}',data)
                if not isinstance(cover,dict) or type(cover.get('message_id')) is not int:
                    raise GameError('Telegram did not confirm spin cover')
                self.intents.bind_message(prepared.intent_id,uid,uid,cover['message_id'],now=timestamp)
                return TelegramOutcome(True,'ready')
            return TelegramOutcome(False,'unknown_message')
        query=update.get('callback_query')
        if not isinstance(query,dict):return TelegramOutcome(False,'unknown_update')
        data=query.get('data')
        if not isinstance(data,str) or not re.fullmatch(r'g1:spin:[0-9a-f]{32}',data):
            return TelegramOutcome(False,'unknown_callback')
        sender,message=query.get('from'),query.get('message')
        if not isinstance(sender,dict) or not isinstance(message,dict):
            return TelegramOutcome(False,'invalid_callback')
        chat=message.get('chat')
        callback_id=query.get('id')
        if (not isinstance(chat,dict) or chat.get('type')!='private' or
                type(sender.get('id')) is not int or sender['id']!=chat.get('id') or
                type(message.get('message_id')) is not int or
                not isinstance(callback_id,str) or not callback_id):
            return TelegramOutcome(False,'unauthorized_callback')
        uid=sender['id'];mid=message['message_id']
        try:
            result=self.intents.commit_callback(UUID(hex=data[len(SPIN_PREFIX):]),uid,uid,mid,now=timestamp)
        except InvalidCallback:
            self.telegram.acknowledge(callback_id,'Кнопка недействительна или уже устарела')
            return TelegramOutcome(True,'rejected')
        except (InsufficientAttempts,MissingActiveCards):
            self.telegram.acknowledge(callback_id,'Крутка пока недоступна')
            return TelegramOutcome(True,'unavailable')
        # DB has committed the reward before ANY media operation.
        try:
            self.telegram.acknowledge(callback_id, 'Уже учтено' if result.replay else 'Запускаю колесо…')
        except Exception:
            # ACK failure is not a reason to lose a committed, saved reward.
            pass
        if result.replay:
            return TelegramOutcome(True,'replayed')
        try:
            self.telegram.disable_button(uid,mid)
        except Exception:
            # Do not re-roll a committed spin because Telegram markup edit failed.
            pass
        return self.deliver_committed(uid,mid,result)

    def deliver_committed(self, chat_id: int, cover_message_id: int, result) -> TelegramOutcome:
        # Validate all source bytes before taking the outbox from pending.
        video_bytes(result.rarity)
        image_for_card(self.private_root,result.card_id)
        if not self.intents.start_delivery(result.spin_id):
            return TelegramOutcome(True,'already_delivering')
        # State is now 'uncertain' until ACKED card delivery. Exceptions must
        # NEVER cause automatic media retries or another attempt charge.
        wheel_mid=self.telegram.show_wheel(chat_id,cover_message_id,result.rarity)
        self.sleeper(REVEAL_DELAY)
        self.telegram.reveal_rarity(chat_id,wheel_mid,result.rarity)
        card_mid=self.telegram.send_card(chat_id,result.card_id,self.private_root)
        self.intents.finish_delivery(result.spin_id,wheel_mid,card_mid)
        return TelegramOutcome(True,'delivered')
