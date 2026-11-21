"""Offline-only contract tests for the approved six-outcome Telegram spin."""
from __future__ import annotations

import io
import json
from urllib.error import HTTPError
import unittest
from unittest.mock import patch

from scripts.telegram_inline_smoke import DemoError
from scripts import telegram_wheel6_smoke as m


class SixOutcomeTelegramSmokeTests(unittest.TestCase):
    def test_all_six_original_assets_sha_and_final_angles(self):
        m.verify_original_assets()
        for name in m.OUTCOMES:
            video = m.video_bytes(name)
            self.assertEqual(video[4:8], b'ftyp')
            self.assertLess(len(video), 50_000_000)
        self.assertEqual(len(set(m._expected_hashes()[f'videos/{n}.mp4'] for n in m.OUTCOMES)),6)

    def test_weighted_server_pick_exact_100_bucket_distribution(self):
        self.assertEqual(m.OUTCOMES, ('Classic','Elite','Royal','Epic','Mythic','Eternal'))
        self.assertEqual(tuple(m.WEIGHTS), (25,22,19,16,11,7))
        actual = {name: 0 for name in m.OUTCOMES}
        for roll in range(100):
            actual[m.choose_outcome(roll)] += 1
        self.assertEqual(tuple(actual.values()), tuple(m.WEIGHTS))
        self.assertEqual(m.choose_outcome(0),'Classic')
        self.assertEqual(m.choose_outcome(25),'Elite')
        self.assertEqual(m.choose_outcome(47),'Royal')
        self.assertEqual(m.choose_outcome(66),'Epic')
        self.assertEqual(m.choose_outcome(82),'Mythic')
        self.assertEqual(m.choose_outcome(93),'Eternal')
        with self.assertRaises(ValueError): m.choose_outcome(100)

    def test_caption_does_not_claim_real_grant_and_cannot_inject_unknown(self):
        for name in m.OUTCOMES:
            caption = m.caption_for(name)
            self.assertIn(name.upper(),caption)
            self.assertIn('не выдана', caption)
            self.assertIn('не списана', caption)
        with self.assertRaises(ValueError):m.caption_for('FREE_CARDS')
        for name in m.OUTCOMES:
            self.assertNotIn(name.upper(), m.SPINNING_CAPTION)

    def test_only_single_recent_private_owner(self):
        now=1800000000
        def cmd(chat=111, user=111, typ='private', text=m.COMMAND, age=12, bot=False):
            return {'message': {'text':text, 'date':now-age,
                                'from':{'id':user,'is_bot':bot},
                                'chat':{'id':chat, 'type':typ}}}
        self.assertEqual(m.select_owner([cmd(),cmd(text='/wheel'),cmd(age=700)], now),(111,111))
        for value in (cmd(chat=900),cmd(typ='group'),cmd(text='/royaltest'),cmd(age=700),cmd(bot=True)):
            with self.subTest(value=value),self.assertRaises(DemoError):m.select_owner([value],now)
        with self.assertRaises(DemoError):m.select_owner([cmd(),cmd(chat=222,user=222)],now)

    def test_only_owner_can_trigger_matching_single_message_callback(self):
        query={'callback_query':{'id':'q-foo','data':m.CALLBACK,'from':{'id':111},
                                 'message':{'message_id':44,'chat':{'id':111,'type':'private'}}}}
        self.assertTrue(m.matches_callback(query,111,111,44))
        self.assertFalse(m.matches_callback(query,111,111,45))
        self.assertFalse(m.matches_callback(query,111,222,44))
        self.assertFalse(m.matches_callback(query,112,111,44))
        self.assertFalse(m.matches_callback({'callback_query': {**query['callback_query'], 'data':'royal'}},111,111,44))
        self.assertFalse(m.matches_callback({'callback_query': {**query['callback_query'],
            'message':{'message_id':44,'chat':{'id':111,'type':'group'}}}},111,111,44))

    def test_preferred_edit_media_upload_contract_has_one_attachment_no_results(self):
        wire=[]
        class FakeResponse:
            def __enter__(self):return io.BytesIO(json.dumps({'ok':True,'result':{
                'message_id':44,'animation':{'file_id':'received'}}}).encode())
            def __exit__(self,*args):pass
        def fake_urlopen(request,timeout=55):
            wire.append((request.full_url,request.data,timeout))
            return FakeResponse()
        video=b'\x00\x00\x00\x18ftypmp42SAMPLE'
        with patch.object(m,'urlopen',fake_urlopen):
            edited=m.edit_to_animation('TOKEN',111,44,'Royal',video)
        self.assertEqual(edited['message_id'],44)
        self.assertEqual(len(wire),1)
        url,body,timeout=wire[0]
        self.assertTrue(url.endswith('/editMessageMedia'))
        self.assertIn(b'"type": "animation"',body)
        self.assertIn(b'"media": "attach://wheel_mp4"',body)
        self.assertIn(b'name="wheel_mp4"; filename="royal-wheel.mp4"',body)
        self.assertIn(b'name="reply_markup"',body)
        self.assertIn(b'"inline_keyboard": []',body)
        self.assertNotIn(b'ROYAL',body)
        self.assertLessEqual(timeout,60)

    def test_clearly_rejected_edit_falls_back_only_once_to_original_video(self):
        trace=[]
        def edit(*args):
            trace.append('edit')
            raise m.MediaReplacementRejected('HTTP 400')
        def fallback(token,chat,name,data):
            trace.append('fallback')
            return {'message_id':51,'animation':{'file_id':'fallback'}}
        def sleep(seconds):trace.append(('sleep',seconds))
        def reveal(token,chat,mid,name):
            trace.append(('reveal',mid,name))
            return {'message_id':mid}
        with patch.object(m,'video_bytes',return_value=b'original-mp4'),\
             patch.object(m,'edit_to_animation',edit),\
             patch.object(m,'send_animation_fallback',fallback),\
             patch.object(m,'edit_result_caption',reveal):
            result=m.deliver_spin('secret',111,44,'Royal',sleeper=sleep)
        self.assertEqual(result,(51,True))
        self.assertEqual(trace,['edit','fallback',('sleep',m.REVEAL_DELAY_SECONDS),('reveal',51,'Royal')])

    def test_successful_edit_gives_single_message_after_delayed_caption(self):
        trace=[]
        def edit(token,chat,mid,name,data):
            trace.append(('edit',mid,name))
            return {'message_id':mid,'animation':{'file_id':'id'}}
        def sleep(seconds):trace.append(('delay',seconds))
        def caption(token,chat,mid,name):
            trace.append(('caption',mid,name))
            return {'message_id':mid}
        with patch.object(m,'video_bytes',return_value=b'original-mp4'),\
             patch.object(m,'edit_to_animation',edit),\
             patch.object(m,'send_animation_fallback') as fallback,\
             patch.object(m,'edit_result_caption',caption):
            self.assertEqual(m.deliver_spin('secret',111,44,'Elite',sleeper=sleep),(44,False))
            fallback.assert_not_called()
        self.assertEqual(trace,[('edit',44,'Elite'),('delay',12.0),('caption',44,'Elite')])
        self.assertGreater(m.REVEAL_DELAY_SECONDS, 10.4)

    def test_network_ambiguous_error_does_not_fallback_or_reveal(self):
        with patch.object(m,'video_bytes',return_value=b'bytes'),\
             patch.object(m,'edit_to_animation',side_effect=DemoError('timeout')),\
             patch.object(m,'send_animation_fallback') as fallback,\
             patch.object(m,'edit_result_caption') as caption:
            with self.assertRaises(DemoError):m.deliver_spin('secret',111,44,'Royal',sleeper=lambda _:None)
            fallback.assert_not_called();caption.assert_not_called()

    def test_http400_edit_only_allows_fallback_not_http500_or_transport(self):
        def reject(code):
            def fail(req,timeout):raise HTTPError(req.full_url,code,'rejected',{},None)
            return fail
        media=b'\x00\x00\x00\x18ftypmp42FAKE'
        for status,expected in ((400,m.MediaReplacementRejected),(500,DemoError),(401,DemoError)):
            with self.subTest(status=status),patch.object(m,'urlopen',reject(status)):
                with self.assertRaises(expected):m.edit_to_animation('PRIVATE_TOKEN',111,44,'Royal',media)
        with patch.object(m,'urlopen',side_effect=TimeoutError('ambiguous')):
            with self.assertRaises(DemoError) as err:
                m.edit_to_animation('PRIVATE_TOKEN',111,44,'Royal',media)
        self.assertNotIn('PRIVATE_TOKEN',str(err.exception))

    def test_full_run_acks_and_locks_button_before_single_send(self):
        trace=[]
        chat=111
        update={'update_id':7,'message':{'text':m.COMMAND,'date':1800000000,
                                          'chat':{'id':chat,'type':'private'},
                                          'from':{'id':chat,'is_bot':False}}}
        click={'update_id':8,'callback_query':{'id':'one','data':m.CALLBACK,
            'from':{'id':chat},'message':{'message_id':44,'chat':{'id':chat,'type':'private'}}}}
        calls={'getUpdates':0}
        def api(token,method,payload):
            trace.append(method)
            if method=='getUpdates':
                calls[method]+=1
                return [update] if calls[method]==1 else ([click,click] if calls[method]==3 else [])
            return {'message_id':99}
        def cover(token,chat_id,method,raw,caption,*,reply_markup):
            trace.append('cover')
            self.assertEqual(method,'sendPhoto')
            self.assertEqual(reply_markup['inline_keyboard'][0][0]['callback_data'],m.CALLBACK)
            return {'message_id':44}
        def deliver(token,chat_id,mid,name):
            trace.append(('delivery',name))
            return mid,False
        with patch.dict('os.environ',{'GACHA_BOT_TOKEN':'123:MOCKTOKENABCDEF'}), \
             patch.object(m,'verify_original_assets'), \
             patch.object(m,'check_bot'), \
             patch.object(m,'api',api), \
             patch.object(m,'send_approved_cover',cover), \
             patch.object(m,'deliver_spin',deliver), \
             patch.object(m.secrets,'randbelow',return_value=50), \
             patch.object(m.time,'time',return_value=1800000000):
            m.run()
        self.assertEqual(trace, ['getUpdates','getUpdates','cover','getUpdates',
                                 'answerCallbackQuery','editMessageReplyMarkup',('delivery','Royal')])
        self.assertEqual(calls['getUpdates'],3)

    def test_no_result_if_media_edit_changes_message_id_or_caption_edit_fails(self):
        with patch.object(m,'video_bytes',return_value=b'original'),\
             patch.object(m,'edit_to_animation',return_value={'message_id':45,'animation':{}}),\
             patch.object(m,'send_animation_fallback') as send,\
             patch.object(m,'edit_result_caption') as caption:
            with self.assertRaises(DemoError):m.deliver_spin('secret',111,44,'Royal',sleeper=lambda _:None)
            send.assert_not_called();caption.assert_not_called()


if __name__ == '__main__':
    unittest.main()
