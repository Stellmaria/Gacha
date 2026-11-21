"""Offline Telegram Bot API adapter tests; no bot token or actual API calls."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from uuid import UUID,uuid4

from gacha_core import telegram_adapter as t
from gacha_core.telegram_intents import SpinIntent, InvalidCallback
from gacha_core.telegram_runtime import verify_operator_environment

NOW=datetime(2026,11,22,21,0,tzinfo=timezone.utc)


def user_message(command, uid=101, *, chat=None, typ='private'):
    return {'message':{'text':command, 'from':{'id':uid,'is_bot':False},
                       'chat':{'id':uid if chat is None else chat,'type':typ}}}


def callback(intent_id,uid=101,mid=55, *, chat=None):
    return {'callback_query':{'id':'ack-1','data':t.SPIN_PREFIX+intent_id.hex,
         'from':{'id':uid},'message':{'message_id':mid,'chat':{'id':uid if chat is None else chat,'type':'private'}}}}


class DummyClient:
    def __init__(self):self.events=[]
    def send_text(self,uid,text,*,menu=False):self.events.append(('text',uid,text,menu));return {'message_id':19}
    def send_cover(self,uid,caption,data):self.events.append(('cover',uid,caption,data));return {'message_id':55}
    def acknowledge(self,qid,message):self.events.append(('ack',qid,message))
    def disable_button(self,uid,mid):self.events.append(('disable',uid,mid))
    def show_wheel(self,uid,mid,rarity):self.events.append(('wheel',uid,mid,rarity));return mid
    def reveal_rarity(self,uid,mid,rarity):self.events.append(('reveal',uid,mid,rarity))
    def send_card(self,uid,cid,root):self.events.append(('card',uid,cid));return 77


class TelegramAdapterContractTests(unittest.TestCase):
    def setUp(self):
        self.client=DummyClient()
        self.game=Mock()
        self.game.profile.return_value=SimpleNamespace(player_id=7,daily_remaining=10,bonus_remaining=1,wallet_balance=0)
        self.game.collection.return_value=[]
        self.handler=t.TelegramGameAdapter(Mock(),self.client,'/no-real-files',game=self.game,sleeper=lambda s:self.client.events.append(('sleep',s)))
        self.handler.intents=Mock()

    def test_private_chat_required_for_all_commands(self):
        for update in (user_message('/start',chat=999),user_message('/spin',typ='group'),
                       {'message':{'text':'/spin','from':{'id':1,'is_bot':True},'chat':{'id':1,'type':'private'}}}):
            result=self.handler.handle_update(update,now=NOW)
            self.assertFalse(result.handled)
        self.assertEqual(self.client.events,[])

    def test_profile_writes_correct_daily_balance_without_spending(self):
        outcome=self.handler.handle_update(user_message('/start'),now=NOW)
        self.assertEqual(outcome.category,'profile')
        kind,uid,text,menu=self.client.events[0]
        self.assertTrue(menu);self.assertIn('10/10',text);self.assertIn('00:00 МСК',text)
        self.game.spin.assert_not_called()

    def test_collection_duplicates_and_event_label(self):
        self.game.collection.return_value=[('classic_06_eshmar','standard','Classic',3),
                                           ('velvet_22_aydan','event',None,1)]
        outcome=self.handler.handle_update(user_message('/cards'),now=NOW)
        self.assertEqual(outcome.category,'collection')
        text=self.client.events[0][2]
        self.assertIn('Эшмар',text);self.assertIn('×3',text);self.assertIn('Эйдан',text)
        self.assertIn('Velvet · ивент',text)

    def test_spin_button_binds_to_exact_user_and_cover_message(self):
        iid=uuid4();self.handler.intents.prepare.return_value=SpinIntent(iid,101,101,None,'prepared')
        with patch('gacha_core.card_store.verify_private_cards',return_value=()):
            result=self.handler.handle_update(user_message('/spin'),now=NOW)
        self.assertEqual(result.category,'ready')
        self.handler.intents.prepare.assert_called_once_with(101,101,now=NOW)
        self.handler.intents.bind_message.assert_called_once_with(iid,101,101,55,now=NOW)
        self.assertEqual(self.client.events[0][0],'cover')
        self.assertEqual(self.client.events[0][3],t.SPIN_PREFIX+iid.hex)

    def test_callback_wrong_id_or_chat_is_not_sent(self):
        iid=uuid4()
        wrong=callback(iid,uid=101,chat=999)
        self.assertEqual(self.handler.handle_update(wrong,now=NOW).category,'unauthorized_callback')
        self.assertEqual(self.client.events,[])
        self.handler.intents.commit_callback.side_effect=InvalidCallback('bad')
        self.assertEqual(self.handler.handle_update(callback(iid),now=NOW).category,'rejected')
        self.assertEqual(self.client.events[0][0],'ack')

    def test_replayed_callback_never_reuploads_media(self):
        iid=uuid4();result=SimpleNamespace(spin_id=uuid4(),rarity='Royal',card_id='royal_15_odin',replay=True)
        self.handler.intents.commit_callback.return_value=result
        out=self.handler.handle_update(callback(iid),now=NOW)
        self.assertEqual(out.category,'replayed')
        self.assertEqual([e[0] for e in self.client.events],['ack'])
        self.handler.intents.start_delivery.assert_not_called()

    def test_delivery_committed_before_network_and_card_after_reveal(self):
        result=SimpleNamespace(spin_id=uuid4(),rarity='Elite',card_id='elite_09_tiss',replay=False)
        self.handler.intents.start_delivery.return_value=True
        with patch.object(t,'video_bytes',return_value=b'mp4'),patch.object(t,'image_for_card',return_value=b'png'):
            out=self.handler.deliver_committed(101,55,result)
        self.assertEqual(out.category,'delivered')
        self.assertEqual([e[0] for e in self.client.events],['wheel','sleep','reveal','card'])
        self.handler.intents.start_delivery.assert_called_once_with(result.spin_id)
        self.handler.intents.finish_delivery.assert_called_once_with(result.spin_id,55,77)
        self.assertEqual(self.client.events[1][1],12)

    def test_media_failure_never_sends_card_or_marks_success(self):
        result=SimpleNamespace(spin_id=uuid4(),rarity='Royal',card_id='royal_15_odin',replay=False)
        self.handler.intents.start_delivery.return_value=True
        self.client.show_wheel=Mock(side_effect=TimeoutError('ambiguous'))
        self.client.send_card=Mock()
        with patch.object(t,'video_bytes',return_value=b'mp4'),patch.object(t,'image_for_card',return_value=b'png'):
            with self.assertRaises(TimeoutError):self.handler.deliver_committed(101,55,result)
        self.client.send_card.assert_not_called()
        self.handler.intents.finish_delivery.assert_not_called()

    def test_missing_private_card_refuses_delivery_before_claim(self):
        result=SimpleNamespace(spin_id=uuid4(),rarity='Royal',card_id='royal_15_odin',replay=False)
        with patch.object(t,'video_bytes',return_value=b'mp4'),patch.object(t,'image_for_card',side_effect=t.CardAssetError('missing')):
            with self.assertRaises(t.CardAssetError):self.handler.deliver_committed(101,55,result)
        self.handler.intents.start_delivery.assert_not_called()

    def test_unknown_callback_does_not_commit(self):
        self.assertEqual(self.handler.handle_update({'callback_query':{'data':'g1:spin:../../','id':'q'}},now=NOW).handled,False)
        self.handler.intents.commit_callback.assert_not_called()

    def test_runtime_requires_explicit_operators_gates(self):
        with self.assertRaises(RuntimeError):verify_operator_environment({})
        env={'GACHA_ENABLE_POLLING':'YES','GACHA_BOT_TOKEN':'123:verySecretToken','GACHA_DATABASE_URL':'postgres://test',
             'GACHA_PRIVATE_CARD_ROOT':'/private/cards','GACHA_EXPECTED_BOT_USERNAME':'velvet_gacha_v1_bot'}
        self.assertEqual(verify_operator_environment(env)[3],'velvet_gacha_v1_bot')
        with self.assertRaises(RuntimeError):verify_operator_environment({**env,'GACHA_EXPECTED_BOT_USERNAME':''})

if __name__=='__main__':unittest.main()
