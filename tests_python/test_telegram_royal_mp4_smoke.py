"""Offline-only acceptance for exact approved Royal MP4 in Telegram private chat."""
from __future__ import annotations
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.telegram_inline_smoke import DemoError
from scripts.telegram_royal_mp4_smoke import (
    CALLBACK, COMMAND, CAPTION, RESULT_TEXT, REVEAL_DELAY_SECONDS,
    COVER, VIDEO, load_approved_media, select_owner, matches_callback,
    send_media, deliver_royal,
)


class OriginalRoyalMp4SmokeTests(unittest.TestCase):
    def test_original_assets_are_exact_approved_bytes(self):
        cover, mp4 = load_approved_media()
        self.assertEqual(cover, COVER.read_bytes())
        self.assertEqual(mp4, VIDEO.read_bytes())
        self.assertTrue(cover.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(mp4[4:8], b'ftyp')
        self.assertEqual(len(mp4), 7277143)
        self.assertNotIn('sendInvoice', CAPTION)

    def test_bad_signature_or_checksum_fails_closed(self):
        import tempfile
        from scripts import telegram_royal_mp4_smoke as m
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            mp4 = base/'video.mp4'; image = base/'cover.png'; hashes=base/'checks.json'
            image.write_bytes(b'\x89PNG\r\n\x1a\n-test')
            mp4.write_bytes(b'....ftyp-test')
            import hashlib
            def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
            hashes.write_text(json.dumps({'source/master.png':sha(image), 'videos/Royal.mp4':sha(mp4)}))
            with patch.object(m,'VIDEO',mp4), patch.object(m,'COVER',image),patch.object(m,'MANIFEST',hashes):
                self.assertEqual(m.load_approved_media(), (image.read_bytes(),mp4.read_bytes()))
                mp4.write_bytes(b'....NOTMP4')
                with self.assertRaises(DemoError):m.load_approved_media()
                mp4.write_bytes(b'....ftyp-CHANGED')
                with self.assertRaises(DemoError):m.load_approved_media()

    def test_owner_selected_only_for_exact_recent_private_command(self):
        now=1800000000
        def command(user=31, chat=31, typ='private', text=COMMAND, age=10, is_bot=False):
            return {'message':{'text':text,'date':now-age,'from':{'id':user,'is_bot':is_bot},
                               'chat':{'id':chat,'type':typ}}}
        self.assertEqual(select_owner([command(), command(text='/wheel'), command(age=301)],now),(31,31))
        for bad in (command(text='/wheel'),command(chat=10),command(typ='group'),command(age=301),command(is_bot=True)):
            with self.subTest(bad=bad),self.assertRaises(DemoError):select_owner([bad],now)
        with self.assertRaises(DemoError):select_owner([command(),command(user=32,chat=32)],now)

    def test_only_exact_private_owner_can_click_our_photo(self):
        q={'callback_query':{'id':'q1','data':CALLBACK,'from':{'id':31},'message':{
            'message_id':76,'chat':{'id':31,'type':'private'}}}}
        self.assertTrue(matches_callback(q,31,31,76))
        self.assertFalse(matches_callback(q,31,31,77))
        self.assertFalse(matches_callback(q,31,32,76))
        self.assertFalse(matches_callback(q,34,31,76))
        self.assertFalse(matches_callback({'callback_query':{**q['callback_query'],'data':'spin'}},31,31,76))
        self.assertFalse(matches_callback({'callback_query':{**q['callback_query'],'message':{
            'message_id':76,'chat':{'id':31,'type':'group'}}}},31,31,76))

    def test_mp4_multipart_is_animation_not_document_or_sticker(self):
        requests=[]
        def fake_read(request, timeout):
            requests.append((request.full_url,request.data,timeout))
            return {'message_id':89,'animation':{'file_id':'demo-file-id'}}
        with patch('scripts.telegram_royal_mp4_smoke._read_response',fake_read):
            result=send_media('123:TEST_TOKEN',31,'sendAnimation',b'\x00\x00\x00\x18ftypmp42FAKE',CAPTION)
        self.assertEqual(result['message_id'],89)
        self.assertEqual(len(requests),1)
        url,data,timeout=requests[0]
        self.assertTrue(url.endswith('/sendAnimation'))
        self.assertIn(b'name="animation"; filename="velvet-wheel-royal.mp4"',data)
        self.assertIn(b'Content-Type: video/mp4',data)
        self.assertIn(b'name="width"',data)
        self.assertIn(b'name="duration"',data)
        self.assertNotIn(b'name="document"',data)
        self.assertLessEqual(timeout,60)

    def test_png_cover_contains_single_inline_spin_button(self):
        requests=[]
        def fake_read(req,timeout):
            requests.append(req.data)
            return {'message_id':77}
        with patch('scripts.telegram_royal_mp4_smoke._read_response',fake_read):
            send_media('token',31,'sendPhoto',b'\x89PNG\r\n\x1a\nFAKE', 'cover',reply_markup={
                'inline_keyboard':[[{'text':'Крутить Royal','callback_data':CALLBACK}]]})
        self.assertEqual(len(requests),1)
        self.assertIn(b'name="photo"; filename="velvet-wheel-master.png"',requests[0])
        self.assertIn(CALLBACK.encode(),requests[0])

    def test_non_approved_media_or_missing_animation_object_rejected(self):
        for method in ('sendInvoice','sendSticker','sendVideo','deleteMessage'):
            with self.subTest(method=method),self.assertRaises(DemoError):
                send_media('token',31,method,b'123','test')
        with self.assertRaises(DemoError):
            send_media('token',31,'sendAnimation',b'GIF89a','test')
        with patch('scripts.telegram_royal_mp4_smoke._read_response',return_value={'message_id':87}):
            with self.assertRaises(DemoError):
                send_media('token',31,'sendAnimation',b'....ftypTEST','test')

    def test_reveal_after_confirmed_animation_and_full_nominal_duration(self):
        trace=[]
        def media(token,chat,method,data,caption):
            trace.append(('animation',method,caption))
            return {'message_id':89,'animation':{'file_id':'id'}}
        def sleep(sec):trace.append(('sleep',sec))
        def api(token,method,payload):
            trace.append(('result',method,payload['text']))
            return {'message_id':90}
        with patch('scripts.telegram_royal_mp4_smoke.send_media',media),patch('scripts.telegram_royal_mp4_smoke.api',api):
            deliver_royal('token',31,b'royal-mp4',sleeper=sleep)
        self.assertEqual([x[0] for x in trace],['animation','sleep','result'])
        self.assertEqual(trace[0][1],'sendAnimation')
        self.assertGreater(trace[1][1],10.4)
        self.assertEqual(trace[1][1],REVEAL_DELAY_SECONDS)
        self.assertNotIn('ROYAL',trace[0][2])
        self.assertIn('ROYAL',trace[2][2])
        self.assertEqual(trace[2][2],RESULT_TEXT)

    def test_no_result_when_video_fails(self):
        with patch('scripts.telegram_royal_mp4_smoke.send_media',side_effect=DemoError('rejected')) , \
             patch('scripts.telegram_royal_mp4_smoke.api') as api_mock:
            with self.assertRaises(DemoError):
                deliver_royal('token',31,b'media',sleeper=lambda sec: None)
        api_mock.assert_not_called()

    def test_network_error_does_not_expose_bot_token(self):
        token='123:TEST_SENSITIVE_TOKEN'
        def fail(req,timeout):
            raise DemoError('Telegram request failed; network or response error.')
        with patch('scripts.telegram_royal_mp4_smoke._read_response',fail):
            with self.assertRaises(DemoError) as raised:
                send_media(token,31,'sendAnimation',b'....ftypTEST',CAPTION)
        self.assertNotIn(token,str(raised.exception))


if __name__ == '__main__':
    unittest.main()
