"""Offline tests: source-verified seven-card PRIVATE import, no real Telegram.

Synthetic PNG bytes are created only inside TemporaryDirectory and NEVER
packaged as production card art.
"""
import binascii
from hashlib import sha256
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import zlib

from gacha_core import card_store as cs


def png(width, height, rgb):
    def chunk(name,data):
        return struct.pack('>I',len(data))+name+data+struct.pack('>I',binascii.crc32(name+data)&0xffffffff)
    row=b'\x00'+bytes(rgb)*width
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
            chunk(b'IDAT',zlib.compress(row*height,9))+chunk(b'IEND',b''))


class SevenCardPrivateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.private=self.dir/'private'
        original=cs.approved_cards()
        self.cards=[]
        self.payload={}
        for i,c in enumerate(original):
            c=dict(c)
            data=png(c['width'],c['height'],((i*23)%255,(i*41)%255,(i*89)%255))
            c.update(sha256=sha256(data).hexdigest(),bytes=len(data))
            self.cards.append(c)
            self.payload[c['filename']]=data
        self.manifest=self.dir/'manifest.json'
        self.manifest.write_text(json.dumps({'schema_version':1,'cards':self.cards},ensure_ascii=False),encoding='utf-8')
        self.archive=self.dir/'cards.zip'
        self.write_archive()
        self.patch=patch.object(cs,'MANIFEST_PATH',self.manifest)
        self.patch.start();self.addCleanup(self.patch.stop)

    def write_archive(self, *, additions=None, overwrite=None):
        entries={'manifest.json':json.dumps({'schema_version':1,'cards':self.cards},ensure_ascii=False).encode(),
                 'README.txt':b'fixture'}|self.payload
        entries.update(additions or {})
        entries.update(overwrite or {})
        with ZipFile(self.archive,'w') as z:
            for filename,data in entries.items():z.writestr(filename,data)

    def test_exact_seven_private_install_read_and_idempotence(self):
        self.assertEqual(cs.install_bundle(self.archive,self.private),7)
        self.assertEqual(cs.install_bundle(self.archive,self.private),7)
        self.assertEqual(len(cs.verify_private_cards(self.private)),7)
        self.assertEqual(tuple(c['rarity'] for c in cs.approved_cards()),
                         ('Classic','Elite','Royal','Epic','Mythic','Eternal',None))
        for c in self.cards:
            self.assertEqual(cs.image_for_card(self.private,c['card_id']),self.payload[c['filename']])
            self.assertEqual((self.private/c['filename']).stat().st_mode & 0o777,0o600)
        self.assertEqual(self.private.stat().st_mode & 0o777,0o700)

    def test_changed_bytes_never_install(self):
        c=self.cards[2]
        self.write_archive(overwrite={c['filename']:self.payload[c['filename']]+b'x'})
        with self.assertRaises(cs.CardAssetError):cs.install_bundle(self.archive,self.private)
        self.assertFalse(self.private.exists())

    def test_changed_metadata_never_install(self):
        self.cards[2]['title']='wrong card'
        self.write_archive()
        with self.assertRaises(cs.CardAssetError):cs.install_bundle(self.archive,self.private)
        self.assertFalse(self.private.exists())

    def test_unexpected_archive_paths_refused(self):
        self.write_archive(additions={'../../secret.txt':b'x'})
        with self.assertRaises(cs.CardAssetError):cs.install_bundle(self.archive,self.private)
        self.assertFalse(self.private.exists())

    def test_existing_file_modification_rejected_not_overwritten(self):
        cs.install_bundle(self.archive,self.private)
        dest=self.private/self.cards[0]['filename']
        dest.write_bytes(b'corrupted')
        with self.assertRaises(cs.CardAssetError):cs.install_bundle(self.archive,self.private)
        self.assertEqual(dest.read_bytes(),b'corrupted')
        with self.assertRaises(cs.CardAssetError):cs.verify_private_cards(self.private)

    def test_symbolic_link_to_outside_forbidden(self):
        self.private.mkdir()
        (self.private/'cards').symlink_to(self.dir,target_is_directory=True)
        with self.assertRaises(cs.CardAssetError):cs.install_bundle(self.archive,self.private)

    def test_no_arbitrary_file_access_by_user_supplied_card_id(self):
        cs.install_bundle(self.archive,self.private)
        for cid in ('../etc/passwd','velvet_22_aydan.png','wrong',None):
            with self.subTest(cid=cid),self.assertRaises(cs.CardAssetError):
                cs.image_for_card(self.private,cid)

    def test_exact_public_manifest_describes_approved_seven(self):
        # Read the REAL committed manifest despite the synthetic test fixture.
        with patch.object(cs,'MANIFEST_PATH',Path(cs.__file__).resolve().parent/'catalog/approved_cards.json'):
            data=cs.approved_cards()
        self.assertEqual(len(data),7)
        self.assertEqual(data[0]['title'],'Эшмар — Пенная капитуляция')
        self.assertEqual(data[1]['title'],'Тисс — Тень цветущих руин')
        self.assertEqual(data[6]['title'],'Эйдан — Кровавый соблазн')
        self.assertEqual(data[6]['kind'],'event')
        self.assertEqual(data[6]['rarity'],None)
        self.assertEqual([d['number'] for d in data],[6,9,15,13,17,21,22])


if __name__=='__main__':unittest.main()
