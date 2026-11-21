"""Preflight & reconciliation are safe, read-only, and fail-closed by default."""
import unittest
from unittest.mock import patch
from gacha_core import beta_preflight as p
from gacha_core import beta_reconcile as r


class FakeCursor:
    def __init__(self,rows,*,db='gacha_beta',role='gacha_beta',version=180007,
                 superuser=False,ambiguous=0,migrations=True):
        self.rows=rows
        self.db=db
        self.role=role
        self.version=version
        self.superuser=superuser
        self.ambiguous=ambiguous
        self.migrations=migrations
        self.result=[]
        self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql,params=None):
        self.calls.append(sql)
        if 'current_setting' in sql:self.result=[(self.db,self.role,self.version)]
        elif 'current_database()' in sql:self.result=[(self.db,)]
        elif 'pg_roles' in sql:self.result=[(self.superuser,False,False)]
        elif 'to_regclass' in sql:self.result=[('gacha.schema_migrations',) if self.migrations else (None,)]
        elif 'SELECT version FROM' in sql:self.result=[(x,) for x in p.REQUIRED_MIGRATIONS] if self.migrations else []
        elif 'SELECT card_id, kind' in sql:self.result=self.rows
        elif 'count(*) FROM gacha.delivery_outbox GROUP BY' in sql:self.result=[('uncertain',self.ambiguous)] if self.ambiguous else []
        elif 'updated_at <' in sql:self.result=[(self.ambiguous,)]
        elif 'count(*) FROM gacha.players' in sql:self.result=[(2,)]
        elif 'count(*) FROM gacha.spins' in sql:self.result=[(4,)]
        else:raise AssertionError('Unexpected query')
        return self
    def fetchone(self):return self.result[0] if self.result else None
    def fetchall(self):return self.result


class FakeConnection:
    def __init__(self,**kwargs):
        cards=p.approved_cards()
        rows=[(c['card_id'],c['kind'],c['rarity'],c['drop_key'],c['title'],c['number'],
               c['character'],c['subtitle'],c['sha256'],True) for c in cards]
        self.cur=FakeCursor(rows,**kwargs)
    def cursor(self):return self.cur


class BetaPreflightTests(unittest.TestCase):
    def test_valid_pg18_private_catalog_and_least_privilege_checks(self):
        db=FakeConnection()
        checks=p.check_database(db,'gacha_beta')
        self.assertTrue(all(c.ok for c in checks),[(c.name,c.ok) for c in checks])
        self.assertEqual(len(checks),6)
        self.assertFalse(any('DELETE ' in q.upper() or 'UPDATE ' in q.upper()
                             for q in db.cur.calls))

    def test_refuses_wrong_database_and_superuser_pg17(self):
        for kw in ({'db':'velvet'}, {'role':'postgres','superuser':True}, {'version':170000},
                   {'ambiguous':2}, {'migrations':False}):
            db=FakeConnection(**kw)
            with self.subTest(kw=kw):
                self.assertFalse(all(x.ok for x in p.check_database(db,'gacha_beta')))
        with self.assertRaises(ValueError):p.check_database(FakeConnection(),'postgres')

    def test_wrong_cards_block_readiness(self):
        db=FakeConnection()
        db.cur.rows[0]=(*db.cur.rows[0][:-2], '0'*64,True)
        checks=p.check_database(db,'gacha_beta')
        self.assertFalse(next(c.ok for c in checks if c.name=='card_registry'))

    def test_private_assets_not_available_fail_closed(self):
        checks=p.offline_assets_check('/nonexistent/gacha/private/assets')
        self.assertEqual(len(checks),2)
        self.assertFalse(next(c.ok for c in checks if c.name=='private_cards'))

    def test_validated_private_assets_in_offline_mode_do_not_claim_telegram_live(self):
        with patch.object(p,'verify_private_cards',return_value=p.approved_cards()):
            checks=p.run_preflight('/private/beta',FakeConnection(),'gacha_beta')
        self.assertFalse(all(c.ok for c in checks))
        self.assertFalse(next(c.ok for c in checks if c.name=='telegram_live'))
        self.assertTrue(next(c.ok for c in checks if c.name=='private_cards'))

    def test_telegram_preflight_only_uses_read_only_bot_methods(self):
        methods=[]
        def fake_api(token,method,payload):
            methods.append(method)
            return {'is_bot':True,'username':'gacha_beta_bot'} if method=='getMe' else {'url':''}
        with patch('gacha_core.telegram_api.api',fake_api):
            checks=p.check_telegram('PRIVATE_TOKEN','gacha_beta_bot')
        self.assertEqual(methods,['getMe','getWebhookInfo'])
        self.assertTrue(all(c.ok for c in checks))
        self.assertNotIn('PRIVATE_TOKEN',repr(checks))

    def test_wrong_bot_identity_or_webhook_is_refused(self):
        with patch('gacha_core.telegram_api.api',return_value={'username':'wrong','is_bot':True}) as req:
            result=p.check_telegram('secret','gacha_beta_bot')
        self.assertFalse(all(c.ok for c in result))
        self.assertEqual(req.call_count,1)
        def fake_api(token,method,payload):
            return {'is_bot':True,'username':'gacha_beta_bot'} if method=='getMe' else {'url':'https://webhook.example'}
        with patch('gacha_core.telegram_api.api',fake_api):
            checks=p.check_telegram('secret','gacha_beta_bot')
        self.assertFalse(checks[-1].ok)

    def test_delivery_reconciliation_is_read_only_redacted_no_retry(self):
        db=FakeConnection(ambiguous=1)
        report=r.delivery_summary(db,'gacha_beta')
        self.assertEqual(report['stale_ambiguous_over_15m'],1)
        self.assertEqual(report['player_count'],2)
        self.assertEqual(report['committed_spin_count'],4)
        self.assertFalse(report['auto_redelivery_enabled'])
        self.assertNotIn('telegram_user_id',str(report))
        self.assertFalse(any('UPDATE ' in q.upper() or 'DELETE ' in q.upper() for q in db.cur.calls))
        with self.assertRaises(ValueError):r.delivery_summary(db,'velvet')


if __name__=='__main__':unittest.main()
