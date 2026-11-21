"""Real PostgreSQL 18 integration tests; only run in the ephemeral CI database.

No production database, Telegram tokens, cards, payments or external APIs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import unittest
from uuid import uuid4

try:
    import psycopg
except ImportError:
    psycopg = None

from gacha_core import (GameCore, GameError, MissingActiveCards,
                        InsufficientAttempts)
from gacha_core.migrate import apply_migrations

DSN = os.environ.get('GACHA_TEST_DATABASE_URL')
BEFORE = datetime(2026,11,21,20,59,59,tzinfo=timezone.utc)  # 23:59:59 MSK
AFTER = datetime(2026,11,21,21,0,0,tzinfo=timezone.utc)    # 00:00:00 MSK
RARITIES = ('Classic','Elite','Royal','Epic','Mythic','Eternal')


@unittest.skipUnless(DSN and psycopg, 'Only run against a configured ephemeral PostgreSQL test database')
class MVP1PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = psycopg.connect(DSN, autocommit=True)
        apply_migrations(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.db.execute('TRUNCATE gacha.cards, gacha.players RESTART IDENTITY CASCADE')

    def seed_all_rarities(self, *, include_event: bool = False):
        # Ephemeral metadata only. These are NOT owner-approved art or production seeds.
        for rarity in RARITIES:
            self.db.execute('INSERT INTO gacha.cards (card_id,kind,rarity,title,media_asset_ref,is_active) '
                            'VALUES (%s,%s,%s,%s,%s,true)',
                            ('test_'+rarity.lower(),'standard',rarity,'fixture '+rarity,'fixture://card/'+rarity))
        if include_event:
            self.db.execute('INSERT INTO gacha.cards (card_id,kind,rarity,title,drop_key,media_asset_ref,is_active) '
                            "VALUES ('test_velvet_event','event',NULL,'fixture Velvet event','advent',"
                            "'fixture://event',true)")

    def core(self, *, user=1001, roll=0):
        return GameCore(self.db, rng=lambda upper: (roll if upper == 100 else 0))

    def count(self, table):
        return self.db.execute('SELECT count(*) FROM gacha.'+table).fetchone()[0]

    def test_migration_can_be_reapplied_and_version_recorded_once(self):
        apply_migrations(self.db)
        apply_migrations(self.db)
        self.assertEqual(self.db.execute('SELECT count(*) FROM gacha.schema_migrations').fetchone()[0],1)

    def test_profile_registered_once_has_ten_daily_and_zero_bonus_wallet(self):
        a=self.core().profile(1001, now=BEFORE)
        b=self.core().profile(1001, now=BEFORE)
        self.assertEqual(a,b)
        self.assertEqual(a.daily_remaining,10)
        self.assertEqual(a.bonus_remaining,0)
        self.assertEqual(a.wallet_balance,0)
        self.assertEqual(self.count('daily_grant_audit'),1)
        self.assertEqual(self.count('players'),1)

    def test_midnight_reset_replaces_not_adds_and_bonus_survives(self):
        self.seed_all_rarities()
        core=self.core()
        core.profile(1001,now=BEFORE)
        core.grant_bonus(1001,uuid4(),3,'fixture award')
        for _ in range(4):core.spin(1001,uuid4(),now=BEFORE)
        pre=core.profile(1001,now=BEFORE)
        self.assertEqual((pre.daily_remaining,pre.bonus_remaining),(6,3))
        post=core.profile(1001,now=AFTER)
        self.assertEqual((post.daily_remaining,post.bonus_remaining),(10,3))
        self.assertEqual(post.game_day.isoformat(),'2026-11-22')
        self.assertEqual(self.count('daily_grant_audit'),2)
        self.assertEqual(core.profile(1001,now=AFTER).daily_remaining,10)
        self.assertEqual(self.count('daily_grant_audit'),2)

    def test_no_backdated_event_can_grant_previous_day_again(self):
        self.seed_all_rarities()
        core=self.core()
        core.profile(1001,now=AFTER)
        with self.assertRaises(GameError):core.spin(1001,uuid4(),now=BEFORE)
        self.assertEqual(self.count('spins'),0)
        self.assertEqual(core.profile(1001,now=AFTER).daily_remaining,10)

    def test_no_cards_does_not_charge_or_create_result(self):
        core=self.core()
        with self.assertRaises(MissingActiveCards):core.spin(1001,uuid4(),now=BEFORE)
        self.assertEqual(self.count('spins'),0)
        self.assertEqual(self.count('delivery_outbox'),0)
        # Entire transaction rolls back, including a newly created profile.
        self.assertEqual(self.count('players'),0)
        self.assertEqual(core.profile(1001,now=BEFORE).daily_remaining,10)

    def test_single_spin_persists_card_and_delivery_outbox(self):
        self.seed_all_rarities(include_event=True)
        result=self.core(roll=52).spin(1001,uuid4(),now=BEFORE)
        self.assertEqual(result.rarity,'Royal')
        self.assertEqual(result.card_id,'test_royal')
        self.assertEqual(result.attempt_kind,'daily')
        self.assertFalse(result.replay)
        self.assertEqual(self.core().collection(1001), [('test_royal','standard','Royal',1)])
        self.assertEqual(self.count('spins'),1)
        self.assertEqual(self.count('delivery_outbox'),1)
        self.assertEqual(self.db.execute('SELECT state FROM gacha.delivery_outbox').fetchone()[0],'pending')
        self.assertEqual(self.core().profile(1001,now=BEFORE).daily_remaining,9)
        self.assertEqual(self.count('wallet_ledger'),0)

    def test_duplicate_cards_stack_quantity_and_event_stays_out_of_main_wheel(self):
        self.seed_all_rarities(include_event=True)
        core=self.core()
        for _ in range(4):core.spin(1001,uuid4(),now=BEFORE)
        self.assertEqual(core.collection(1001), [('test_classic','standard','Classic',4)])
        self.assertEqual(self.count('spins'),4)
        self.assertEqual(self.count('player_cards'),1)
        self.assertEqual(self.count('delivery_outbox'),4)
        self.assertEqual(core.profile(1001,now=BEFORE).daily_remaining,6)

    def test_single_request_replay_across_midnight_returns_original(self):
        self.seed_all_rarities()
        core=self.core()
        request=uuid4()
        first=core.spin(1001,request,now=BEFORE)
        same=core.spin(1001,request,now=AFTER)
        self.assertEqual(same.spin_id,first.spin_id)
        self.assertEqual(same.game_day,first.game_day)
        self.assertEqual(same.card_id,first.card_id)
        self.assertTrue(same.replay)
        self.assertEqual(self.count('spins'),1)
        self.assertEqual(self.count('delivery_outbox'),1)
        self.assertEqual(core.profile(1001,now=AFTER).daily_remaining,10)

    def test_ten_daily_then_bonus_then_insufficient(self):
        self.seed_all_rarities()
        core=self.core()
        core.grant_bonus(1001,uuid4(),2,'fixture grant')
        results=[core.spin(1001,uuid4(),now=BEFORE) for _ in range(12)]
        self.assertEqual([r.attempt_kind for r in results],['daily']*10+['bonus']*2)
        self.assertEqual((core.profile(1001,now=BEFORE).daily_remaining,
                          core.profile(1001,now=BEFORE).bonus_remaining),(0,0))
        with self.assertRaises(InsufficientAttempts):core.spin(1001,uuid4(),now=BEFORE)
        self.assertEqual(self.count('spins'),12)
        self.assertEqual(self.count('delivery_outbox'),12)
        self.assertEqual(core.collection(1001)[0][-1],12)

    def test_bonus_grants_are_idempotent_but_cannot_change_payload(self):
        core=self.core()
        request=uuid4()
        self.assertEqual(core.grant_bonus(1001,request,5,'manual test'),5)
        self.assertEqual(core.grant_bonus(1001,request,5,'manual test'),5)
        with self.assertRaises(GameError):core.grant_bonus(1001,request,8,'manual test')
        self.assertEqual(self.count('bonus_grants'),1)
        self.assertEqual(core.profile(1001,now=BEFORE).bonus_remaining,5)

    def test_database_denies_active_card_without_media_and_unknown_rarity(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.db.execute("INSERT INTO gacha.cards (card_id,kind,rarity,title,is_active) "
                            "VALUES ('oops','standard','Elegant','Test',true)")
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.db.execute("INSERT INTO gacha.cards (card_id,kind,rarity,title,is_active) "
                            "VALUES ('missing_art','standard','Elite','Test',true)")

    def test_no_players_share_history_or_inventory(self):
        self.seed_all_rarities()
        self.core().spin(1001,uuid4(),now=BEFORE)
        self.core().spin(2002,uuid4(),now=BEFORE)
        self.assertEqual(self.core().collection(1001)[0][-1],1)
        self.assertEqual(self.core().collection(2002)[0][-1],1)
        self.assertEqual(self.count('players'),2)
        self.assertEqual(self.count('spins'),2)

    def test_concurrent_distinct_requests_cannot_exceed_ten_daily(self):
        self.seed_all_rarities()
        def attempt(_):
            with psycopg.connect(DSN,autocommit=True) as db:
                try:
                    return GameCore(db,rng=lambda upper:0).spin(1001,uuid4(),now=BEFORE)
                except InsufficientAttempts:
                    return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(attempt,range(16)))
        self.assertEqual(len([x for x in results if x is not None]),10)
        self.assertEqual(self.count('spins'),10)
        self.assertEqual(self.count('delivery_outbox'),10)
        self.assertEqual(self.core().profile(1001,now=BEFORE).daily_remaining,0)
        self.assertEqual(self.core().collection(1001)[0][-1],10)

    def test_concurrent_same_request_is_single_charge_and_one_result(self):
        self.seed_all_rarities()
        request=uuid4()
        def attempt(_):
            with psycopg.connect(DSN,autocommit=True) as db:
                return GameCore(db,rng=lambda upper:0).spin(1001,request,now=BEFORE)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(attempt,range(6)))
        self.assertEqual(len({x.spin_id for x in results}),1)
        self.assertEqual(sum(x.replay for x in results),5)
        self.assertEqual(self.count('spins'),1)
        self.assertEqual(self.count('delivery_outbox'),1)
        self.assertEqual(self.core().profile(1001,now=BEFORE).daily_remaining,9)

if __name__=='__main__':unittest.main()
