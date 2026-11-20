"""No live Telegram; full mock trace, TGS validation, privacy and one-click contract."""
import gzip
import json
import unittest
from unittest.mock import patch

from scripts.telegram_chat_royal_pilot import (
    CALLBACK, DemoError, SPINUP_CAPTION, SPINNING_CAPTION, FINAL_CAPTION,
    INTRO_SECONDS, OUTCOME_SECONDS, matches_pilot_callback, multipart_request,
    deliver_royal_sequence, cover_photo, demo_reward_photo
)
from scripts.telegram_gacha_tgs import FRAME_RATE, FRAMES, make_tgs


class RoyalChatPilotTests(unittest.TestCase):
    def test_native_tgs_are_small_stable_and_use_no_images(self):
        for launch in (True, False):
            tgs = make_tgs(launch=launch)
            self.assertTrue(tgs.startswith(b'\x1f\x8b'))
            self.assertLessEqual(len(tgs), 65536)
            j = json.loads(gzip.decompress(tgs))
            self.assertEqual((j['w'], j['h'], j['fr'], j['op']), (512, 512, FRAME_RATE, FRAMES))
            self.assertEqual(j['assets'], [])
            self.assertEqual(len(j['layers']), 2)
            core, disk = j['layers']
            self.assertEqual(core['nm'], 'stationary ruby and top pointer')
            self.assertEqual(core['ks']['r'], {'a': 0, 'k': 0})
            self.assertEqual(core['ks']['p']['k'], disk['ks']['p']['k'])
            self.assertEqual(disk['ks']['r']['a'], 1)
            self.assertIn(disk['ks']['r']['k'][0]['s'], ([0], [270]))
            self.assertEqual((disk['ks']['r']['k'][-1]['s'][0] - disk['ks']['r']['k'][0]['s'][0]) % 360, 0)
            for layer in j['layers']:
                self.assertNotIn('refId', layer)

    def test_royal_outcome_rotates_right_sector_under_top_pointer(self):
        j = json.loads(gzip.decompress(make_tgs(launch=False)))
        disk = j['layers'][1]
        self.assertEqual(disk['ks']['r']['k'][-1]['s'], [1350])
        # Golden Royal starts due right (90deg clockwise from pointer). A total
        # 270deg clockwise rotation places that sector at the north pointer.
        self.assertEqual(1350 % 360, 270)

    def test_strict_owner_callback_requires_our_cover(self):
        good = {'callback_query': {
            'data': CALLBACK, 'id': 'unique-q', 'from': {'id': 313},
            'message': {'message_id': 44, 'chat': {'id': 313, 'type': 'private'}}
        }}
        self.assertTrue(matches_pilot_callback(good, 313, 313, 44))
        self.assertFalse(matches_pilot_callback(good, 313, 314, 44))
        self.assertFalse(matches_pilot_callback(good, 313, 313, 45))
        self.assertFalse(matches_pilot_callback({"callback_query": {**good['callback_query'], 'data':'other'}}, 313, 313, 44))
        self.assertFalse(matches_pilot_callback({"callback_query": {**good['callback_query'], 'message': {'message_id':44,'chat':{'id':313,'type':'supergroup'}}}},313,313,44))

    def test_multipart_rejects_non_sticker_or_oversize(self):
        for method in ('sendInvoice', 'sendAnimation', 'deleteMessage'):
            with self.subTest(method=method), self.assertRaises(DemoError):
                multipart_request('token', method, 313, 'photo','a.jpg','image/jpeg',b'\xff\xd8')
        with self.assertRaises(DemoError):
            multipart_request('token','sendSticker',313,'sticker','w.tgs','application/x-tgsticker',b'GIF89a')
        with self.assertRaises(DemoError):
            multipart_request('token','sendSticker',313,'sticker','w.tgs','application/x-tgsticker',b'\x1f\x8b'+ b'x'*65536)

    def test_sticker_uploaded_as_tgs_and_reply_markup_is_encoded(self):
        trace = []
        def capture(request, timeout=20):
            trace.append((request.full_url, request.data))
            return {'message_id': 12}
        with patch('scripts.telegram_chat_royal_pilot._read_response', capture):
            r = multipart_request('1:TEST_TOKEN', 'sendSticker', 313,
                                  'sticker', 'launch.tgs', 'application/x-tgsticker', make_tgs(launch=True))
            self.assertEqual(r['message_id'], 12)
        self.assertIn(b'application/x-tgsticker', trace[0][1])
        self.assertIn(b'gacha', trace[0][1])
        self.assertTrue(trace[0][1].count(b'\x1f\x8b') == 1)

    def test_royal_sequence_does_not_reveal_before_stickers_finish(self):
        trace = []
        def edit(token, chat, message, caption):
            trace.append(('edit', caption))
        def sticker(token, chat, *, start):
            trace.append(('sticker', 'launch' if start else 'ROYAL'))
            return {'message_id': 100}
        def sleep(seconds):
            trace.append(('sleep', seconds))
        def api(token, method, payload):
            trace.append(('message', payload['text']))
            return {'message_id': 101}
        def media(token, method, chat, field, file, mime, payload, *, caption=None, reply_markup=None):
            trace.append(('card', caption))
            return {'message_id': 102}
        with patch('scripts.telegram_chat_royal_pilot.edit_caption', edit), \
             patch('scripts.telegram_chat_royal_pilot.send_sticker', sticker), \
             patch('scripts.telegram_chat_royal_pilot.api', api), \
             patch('scripts.telegram_chat_royal_pilot.multipart_request', media), \
             patch('scripts.telegram_chat_royal_pilot.demo_reward_photo', return_value=b'\xff\xd8'):
            deliver_royal_sequence('token', 313, 66, sleeper=sleep)
        self.assertEqual([x[0] for x in trace], ['edit', 'sticker', 'sleep', 'edit', 'sticker', 'sleep', 'edit', 'message', 'card'])
        self.assertEqual(trace[0][1], SPINUP_CAPTION)
        self.assertEqual(trace[3][1], SPINNING_CAPTION)
        self.assertEqual(trace[6][1], FINAL_CAPTION)
        self.assertGreaterEqual(trace[2][1], INTRO_SECONDS)
        self.assertGreaterEqual(trace[5][1], OUTCOME_SECONDS)
        self.assertIn('ROYAL', trace[7][1])
        for stage in trace[:7]:
            self.assertNotIn('ROYAL', stage[1] if isinstance(stage[1], str) and stage[0] == 'edit' else '')

    def test_reward_not_sent_when_sticker_upload_fails(self):
        with patch('scripts.telegram_chat_royal_pilot.edit_caption'), \
             patch('scripts.telegram_chat_royal_pilot.send_sticker', side_effect=DemoError('network failed')), \
             patch('scripts.telegram_chat_royal_pilot.api') as ap, \
             patch('scripts.telegram_chat_royal_pilot.multipart_request') as media:
            with self.assertRaises(DemoError):
                deliver_royal_sequence('token', 313, 66, sleeper=lambda _: None)
        ap.assert_not_called()
        media.assert_not_called()

    def test_tgs_visual_scene_exposes_six_wedges_and_ruby(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow runs in the GitHub Actions rendering job')
        from scripts.render_tgs_visual_smoke import assert_visible_sectors_and_core, render_frame
        image = assert_visible_sectors_and_core(make_tgs(launch=True))
        self.assertEqual(image.size, (512, 512))
        # Royal should become the topmost wedge at the settled end of the result.
        settled = render_frame(make_tgs(launch=False), 179)
        self.assertGreater(settled.getpixel((256, 163))[0], 120)

    def test_cover_and_demo_card_are_valid_jpegs_when_pillow_available(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow only in multimedia GitHub Actions job')
        for blob in (cover_photo(), demo_reward_photo()):
            self.assertTrue(blob.startswith(b'\xff\xd8'))
            self.assertLess(len(blob), 5_000_000)
            import io
            with Image.open(io.BytesIO(blob)) as im:
                self.assertEqual(im.format, 'JPEG')
                self.assertGreater(im.width, 400)


if __name__ == '__main__':
    unittest.main()
