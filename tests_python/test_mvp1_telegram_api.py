"""Tests the new whitelisted Bot API JSON surface without real requests."""
import unittest
from unittest.mock import patch
from gacha_core import telegram_api as a


class TelegramAPIContractTests(unittest.TestCase):
    def test_required_methods_allowed_no_http(self):
        methods=('getMe','getWebhookInfo','getUpdates','sendMessage',
                 'answerCallbackQuery','editMessageReplyMarkup','editMessageCaption')
        for method in methods:
            with self.subTest(method=method),patch.object(a,'_read_response',return_value={'message_id':41}) as reader:
                self.assertEqual(a.api('123:VALID_TOKEN_XXXXXXXX',method,{}),{'message_id':41})
                request=reader.call_args.args[0]
                self.assertTrue(request.full_url.endswith('/'+method))
                self.assertEqual(request.get_method(),'POST')

    def test_forbidden_methods_cannot_send_external_or_secret_data(self):
        for method in ('deleteMessage','sendInvoice','sendPaidMedia','getFile','eval','sendAnimation','setWebhook'):
            with self.subTest(method=method),patch.object(a,'_read_response') as io:
                with self.assertRaises(Exception):a.api('123:VALID_TOKEN_XXXXXXXX',method,{})
                io.assert_not_called()

    def test_long_poll_transport_timeout_exceeds_telegram_wait(self):
        with patch.object(a,'_read_response',return_value=[]) as call:
            a.api('123:VALID_TOKEN_XXXXXXXX','getUpdates',{'timeout':15})
            self.assertGreater(call.call_args.kwargs['timeout'],15)

    def test_malformed_secret_never_networked(self):
        with patch.object(a,'_read_response') as io:
            with self.assertRaises(Exception):a.api('not-a-token','getMe',{})
            io.assert_not_called()


if __name__=='__main__':unittest.main()
