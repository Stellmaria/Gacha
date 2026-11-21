"""No DB, no Telegram: unit tests for approved game rules."""
from datetime import datetime, timezone
import unittest
from uuid import uuid4
from gacha_core.domain import (DAILY_LIMIT, MSK, ODDS, choose_rarity,
                               game_day_moscow, _telegram_id, _uuid)

class MVP1PureDomainTests(unittest.TestCase):
    def test_approved_rarities_and_probability_buckets(self):
        self.assertEqual(ODDS, (('Classic',25),('Elite',22),('Royal',19),
                                ('Epic',16),('Mythic',11),('Eternal',7)))
        self.assertEqual(DAILY_LIMIT,10)
        result={rarity:0 for rarity,_ in ODDS}
        for roll in range(100):result[choose_rarity(roll)]+=1
        self.assertEqual(tuple(result.values()),(25,22,19,16,11,7))
        self.assertEqual([choose_rarity(x) for x in (0,25,47,66,82,93)],
                         ['Classic','Elite','Royal','Epic','Mythic','Eternal'])

    def test_invalid_rolls_fail_closed(self):
        for roll in (-1,100,True,1.5,'0',None):
            with self.subTest(roll=roll),self.assertRaises(ValueError):choose_rarity(roll)

    def test_one_moscow_midnight_both_sides_and_new_year(self):
        self.assertEqual(MSK.key,'Europe/Moscow')
        for year,month,day,next_day in [(2026,11,21,'2026-11-22'),(2027,1,1,'2027-01-02')]:
            before=datetime(year,month,day,20,59,59,tzinfo=timezone.utc)
            after=datetime(year,month,day,21,0,0,tzinfo=timezone.utc)
            self.assertEqual(game_day_moscow(before).isoformat(),before.date().isoformat())
            self.assertEqual(game_day_moscow(after).isoformat(),next_day)
        with self.assertRaises(ValueError):game_day_moscow(datetime(2026,11,21,0,0))

    def test_telegram_identity_strict_int64(self):
        self.assertEqual(_telegram_id(123456789012),123456789012)
        for bad in (0,-1,True,'123',None,2**63):
            with self.subTest(bad=bad),self.assertRaises(ValueError):_telegram_id(bad)

    def test_uuid_request_keys(self):
        value=uuid4()
        self.assertEqual(_uuid(value),value)
        self.assertEqual(_uuid(str(value)),value)
        for bad in (None,'','same-button',True):
            with self.subTest(bad=bad),self.assertRaises(ValueError):_uuid(bad)

if __name__=='__main__':unittest.main()
