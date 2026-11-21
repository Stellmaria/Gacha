"""Install seven approved owner-supplied PNG cards into PRIVATE local storage.

This module intentionally stores NO binary artwork in public GitHub. The ZIP
is supplied separately and must match the exact recorded owner-upload hashes.
Do not accept card paths or hashes from Telegram or any untrusted callback.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import struct
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, BadZipFile

MANIFEST_PATH = Path(__file__).resolve().parent / 'catalog/approved_cards.json'
ORDER = ('Classic', 'Elite', 'Royal', 'Epic', 'Mythic', 'Eternal')


class CardAssetError(Exception):
    """Unexpected, absent or corrupted card asset; no card is made active."""


def approved_cards() -> tuple[dict, ...]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    cards = manifest.get('cards')
    if manifest.get('schema_version') != 1 or not isinstance(cards, list) or len(cards) != 7:
        raise CardAssetError('Approved catalog needs exactly seven source cards')
    if tuple(c.get('rarity') for c in cards[:6]) != ORDER:
        raise CardAssetError('Standard card rarity order differs from approved wheel')
    ids = set()
    for i, c in enumerate(cards):
        cid = c.get('card_id')
        if not isinstance(cid, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', cid) or cid in ids:
            raise CardAssetError('Duplicate or invalid card identifier')
        ids.add(cid)
        if c.get('kind') != ('standard' if i < 6 else 'event'):
            raise CardAssetError('Invalid rarity versus event category')
        if (c.get('drop_key') != ('main' if i < 6 else 'velvet_event') or
                c.get('filename') != f'cards/{cid}.png' or
                not isinstance(c.get('sha256'),str) or
                not re.fullmatch(r'[a-f0-9]{64}', c['sha256']) or
                type(c.get('bytes')) is not int or not 0 < c['bytes'] <= 10_000_000 or
                c.get('width') != 1024 or c.get('height') not in (1535,1536) or
                not isinstance(c.get('title'),str) or len(c['title']) > 200):
            raise CardAssetError('Invalid approved file metadata')
    if cards[-1].get('rarity') is not None or cards[-1].get('card_id') != 'velvet_22_aydan':
        raise CardAssetError('Velvet card must only be an event')
    return tuple(cards)


def _check_image(data: bytes, card: dict) -> None:
    if (len(data) != card['bytes'] or
            sha256(data).hexdigest() != card['sha256'] or
            not data.startswith(b'\x89PNG\r\n\x1a\n') or
            len(data) < 32 or data[12:16] != b'IHDR' or
            struct.unpack_from('>II', data, 16) != (card['width'],card['height'])):
        raise CardAssetError('Card image differs from the exact approved original')


def _store_root(root: str | Path, *, create: bool) -> Path:
    p = Path(root).expanduser().absolute()
    if p.is_relative_to(Path(__file__).resolve().parents[1]):
        raise CardAssetError('Private card directory must be outside public repository')
    if p.is_symlink():
        raise CardAssetError('Private card directory cannot be a symlink')
    if create:
        p.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not p.is_dir():
        raise CardAssetError('Private card directory is unavailable')
    if create:
        p.chmod(0o700)
    cards = p / 'cards'
    if cards.is_symlink():
        raise CardAssetError('Card directory cannot be a symlink')
    if create:
        cards.mkdir(mode=0o700, exist_ok=True)
        cards.chmod(0o700)
    if not cards.is_dir():
        raise CardAssetError('Private cards are not installed')
    return p


def install_bundle(archive: str | Path, private_root: str | Path) -> int:
    """Validate ALL seven bytes before touching private card files.

    Never extract ZIP paths directly; fixed names from the approved manifest.
    No overwriting a different existing image, even if the ZIP was altered.
    """
    cards = approved_cards()
    expected = {c['filename'] for c in cards} | {'manifest.json','README.txt'}
    try:
        with ZipFile(archive) as z:
            names = z.namelist()
            if len(names) != len(expected) or set(names) != expected:
                raise CardAssetError('Private archive contains unexpected or missing files')
            for info in z.infolist():
                if (info.is_dir() or info.file_size > 10_000_000 or
                        (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK):
                    raise CardAssetError('Private archive has forbidden ZIP entry')
            embedded = json.loads(z.read('manifest.json'))
            if embedded.get('cards') != list(cards) or embedded.get('schema_version') != 1:
                raise CardAssetError('Bundled card manifest does not match repository manifest')
            payload = {c['filename']: z.read(c['filename']) for c in cards}
    except (OSError, BadZipFile, ValueError, KeyError) as e:
        raise CardAssetError('Cannot read the approved private card bundle') from e
    for c in cards:
        _check_image(payload[c['filename']], c)
    root = _store_root(private_root, create=True)
    for c in cards:
        dest = root / c['filename']
        if dest.is_symlink():
            raise CardAssetError('Refusing to overwrite a symlink')
        if dest.exists():
            _check_image(dest.read_bytes(), c)
            continue
        # Replace only at the final path, after ALL source files have been checked.
        with NamedTemporaryFile(dir=dest.parent, prefix='.card-', delete=False) as tmp:
            name = tmp.name
            try:
                os.fchmod(tmp.fileno(), 0o600)
                tmp.write(payload[c['filename']])
                tmp.flush()
                os.fsync(tmp.fileno())
            except BaseException:
                Path(name).unlink(missing_ok=True)
                raise
        os.replace(name, dest)
    verify_private_cards(root)
    return len(cards)


def verify_private_cards(private_root: str | Path) -> tuple[dict, ...]:
    root = _store_root(private_root, create=False)
    cards = approved_cards()
    for card in cards:
        path = root / card['filename']
        if not path.is_file() or path.is_symlink():
            raise CardAssetError('Approved private card is missing or linked elsewhere')
        _check_image(path.read_bytes(), card)
    return cards


def image_for_card(private_root: str | Path, card_id: str) -> bytes:
    # Only fixed approved IDs, never remote-provided file paths.
    match = next((c for c in approved_cards() if c['card_id'] == card_id), None)
    if match is None:
        raise CardAssetError('Unknown card ID')
    root = _store_root(private_root, create=False)
    path = root / match['filename']
    if path.is_symlink() or not path.is_file():
        raise CardAssetError('Approved private card not installed')
    data = path.read_bytes()
    _check_image(data, match)
    return data


def register_approved_cards(conn, private_root: str | Path) -> int:
    """Register and activate exactly the seven locally verified originals.

    A previously-registered same ID with changed identity is rejected rather
    than mutated, since it might already belong to a player inventory.
    """
    verified = verify_private_cards(private_root)
    with conn.transaction():
        with conn.cursor() as cur:
            for card in verified:
                cur.execute('SELECT kind, rarity, title, drop_key, media_asset_ref, '
                            'card_number, character_name, subtitle, media_sha256 '
                            'FROM gacha.cards WHERE card_id = %s FOR UPDATE', (card['card_id'],))
                existing = cur.fetchone()
                ref = 'private://' + card['filename']
                fields = (card['kind'],card['rarity'],card['title'],card['drop_key'],ref,
                          card['number'],card['character'],card['subtitle'],card['sha256'])
                if existing is not None and tuple(existing) != fields:
                    raise CardAssetError('Card ID already exists with different original metadata')
                if existing is None:
                    cur.execute('INSERT INTO gacha.cards '
                                '(card_id, kind, rarity, title, drop_key, media_asset_ref, '
                                'card_number, character_name, subtitle, media_sha256, is_active) '
                                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)',
                                (card['card_id'],*fields))
                else:
                    cur.execute('UPDATE gacha.cards SET is_active=true WHERE card_id=%s',
                                (card['card_id'],))
    return len(verified)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Install approved card originals outside public Gacha repo')
    parser.add_argument('--bundle',required=True,help='Owner-supplied approved private ZIP')
    parser.add_argument('--private-root',required=True,help='Location outside public Gacha checkout')
    parser.add_argument('--register',action='store_true',help='Register/activate catalog in dedicated PostgreSQL')
    args = parser.parse_args()
    count = install_bundle(args.bundle,args.private_root)
    if args.register:
        dsn = os.environ.get('GACHA_DATABASE_URL')
        if not dsn:
            parser.error('--register requires GACHA_DATABASE_URL in secure environment')
        import psycopg
        with psycopg.connect(dsn,autocommit=True) as conn:
            register_approved_cards(conn,args.private_root)
    print(f'Gacha private original cards verified: {count}; registration: {bool(args.register)}')


if __name__=='__main__':
    main()
