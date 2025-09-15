#!/usr/bin/env python3
"""Prices manager for OTASync

Actions:
 - list-properties
 - get-prices (calendar)  --property <id> --start YYYY-MM-DD --days N
 - update-boards     --property <id> --boards-file file.json [--dry-run] [--yes]

Examples:
  python scripts/prices_manager.py --action list-properties --pretty
  python scripts/prices_manager.py --action get-prices --property 9355 --start 2025-09-05 --days 7 --pretty
  python scripts/prices_manager.py --action update-boards --property 9355 --boards-file boards.json --dry-run

Notes:
- Reads credentials from env or ./credentials.txt in project root.
- update-boards sends payload to POST /boards/edit/boards using the token and pkey.
"""
import os
import sys
import argparse
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.otasync_client import OTASyncClient


def read_project_credentials():
    # Prefer credentials stored in kunas/ (user requested move). Fallback to repo root ./credentials.txt
    repo_root = os.path.dirname(os.path.dirname(__file__))
    kunas_cred = os.path.join(repo_root, 'kunas', 'credentials.txt')
    repo_cred = os.path.join(repo_root, 'credentials.txt')
    creds = {}
    for cred_file in (kunas_cred, repo_cred):
        if os.path.exists(cred_file):
            with open(cred_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' not in line:
                        continue
                    k, v = line.strip().split('=', 1)
                    creds[k] = v
            if creds:
                break
    # fallback to env
    creds.setdefault('token', os.getenv('OTASYNC_TOKEN'))
    creds.setdefault('username', os.getenv('OTASYNC_USERNAME'))
    creds.setdefault('password', os.getenv('OTASYNC_PASSWORD'))
    return creds


def ensure_creds(creds):
    if not (creds.get('token') and creds.get('username') and creds.get('password')):
        raise SystemExit('Missing credentials. Set env vars or create ./credentials.txt')


def list_properties(client, creds, pretty=False):
    pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
    print('Login status:', resp.status_code)
    if not pkey:
        print('Login failed. Response:')
        print(resp.text[:1000])
        return None
    props = client.extract_properties_from_response(resp)
    if pretty:
        print(json.dumps(props or [], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(props or [], ensure_ascii=False))
    return props


def get_prices(client, creds, id_properties, start_date=None, days=30, pretty=False):
    pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
    print('Login status:', resp.status_code)
    if not pkey:
        print('Login failed')
        return None
    # call calendar endpoint
    date_str = start_date or datetime.utcnow().strftime('%Y-%m-%d')
    r = client.get_calendar(creds['token'], pkey, int(id_properties), date=date_str, days=days)
    try:
        data = r.json()
    except Exception:
        data = r.text
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)
    return data


def update_boards(client, creds, id_properties, boards, dry_run=False, assume_yes=False):
    pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
    print('Login status:', resp.status_code)
    if not pkey:
        print('Login failed')
        return None
    payload = {
        'token': creds['token'],
        'key': pkey,
        'id_properties': int(id_properties),
        'boards': boards
    }
    print('Prepared payload:')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if dry_run:
        print('Dry run enabled, not sending request.')
        return payload
    if not assume_yes:
        yn = input('Apply update to remote? (y/N): ').strip().lower()
        if yn != 'y':
            print('Aborted by user.')
            return None
    r = client.update_boards_prices(creds['token'], pkey, int(id_properties), boards)
    print('Response status:', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text[:1000])
    return r


def load_boards_from_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', choices=['list-properties', 'get-prices', 'update-boards', 'set-prices', 'export-properties'], required=True)
    parser.add_argument('--property', dest='id_properties', help='id_properties to act on')
    parser.add_argument('--start', help='start date YYYY-MM-DD for get-prices')
    parser.add_argument('--days', type=int, default=30, help='number of days for get-prices')
    parser.add_argument('--boards-file', help='JSON file with "boards" array for update-boards')
    parser.add_argument('--yes', action='store_true', help='Assume yes for destructive operations')
    # set-prices specific
    parser.add_argument('--price', type=int, default=2500, help='Price to set for each date when using set-prices')
    parser.add_argument('--room-type', dest='room_type', help='Optional id_room_types to target (defaults to first found)')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output')
    args = parser.parse_args()

    creds = read_project_credentials()
    try:
        ensure_creds(creds)
    except SystemExit as e:
        print(str(e))
        return

    client = OTASyncClient()

    if args.action == 'list-properties':
        list_properties(client, creds, pretty=args.pretty)
        return

    if args.action == 'export-properties':
        # Export all properties returned by login to a JSON backup file
        try:
            pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
            print('Login status:', resp.status_code)
            if not pkey:
                print('Login failed')
                return
            props = client.extract_properties_from_response(resp)
            # fallback to get_properties_via_login which may parse embedded properties
            if not props:
                props, resp = client.get_properties_via_login(creds['token'], creds['username'], creds['password'])
            if not props:
                print('No properties found for this account.')
                return
            # ensure backups dir
            import os
            from datetime import datetime
            outdir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
            os.makedirs(outdir, exist_ok=True)
            fname = f'properties_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
            fpath = os.path.join(outdir, fname)
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(props, f, ensure_ascii=False, indent=2)
            print('Exported properties to', fpath)
            if args.pretty:
                print(json.dumps(props, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(props, ensure_ascii=False))
        except Exception as e:
            print('Error exporting properties:', str(e))
        return

    if args.action == 'get-prices':
        if not args.id_properties:
            print('Please provide --property id')
            return
        get_prices(client, creds, args.id_properties, start_date=args.start, days=args.days, pretty=args.pretty)
        return

    if args.action == 'update-boards':
        if not args.id_properties:
            print('Please provide --property id')
            return
        if not args.boards_file:
            print('Please provide --boards-file with boards array JSON')
            return
        boards = load_boards_from_file(args.boards_file)
        # if JSON contains top-level object with 'boards', accept both
        if isinstance(boards, dict) and 'boards' in boards:
            boards_list = boards['boards']
        else:
            boards_list = boards
        update_boards(client, creds, args.id_properties, boards_list, assume_yes=args.yes)
        return

    if args.action == 'set-prices':
        # Build a simple boards payload that sets price_adults to the requested price for the next N days
        if not args.id_properties:
            print('Please provide --property id')
            return
        # Perform login once and fetch calendar with the returned pkey
        pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
        print('Login status:', resp.status_code)
        if not pkey:
            print('Login failed')
            return
        # get calendar using obtained pkey
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        r = client.get_calendar(creds['token'], pkey, int(args.id_properties), date=date_str, days=args.days)
        try:
            data = r.json()
        except Exception:
            data = r.text

        # Determine room_type to target (room_types may be at top-level or under 'filters')
        room_types = []
        if isinstance(data, dict):
            if 'room_types' in data and isinstance(data['room_types'], list):
                room_types = data['room_types']
            elif 'filters' in data and isinstance(data['filters'], dict) and 'room_types' in data['filters'] and isinstance(data['filters']['room_types'], list):
                room_types = data['filters']['room_types']
        target_room = None
        if args.room_type:
            for rt in room_types:
                if str(rt.get('id_room_types')) == str(args.room_type) or str(rt.get('id_room_types')) == str(args.room_type):
                    target_room = rt
                    break
        if not target_room and room_types:
            target_room = room_types[0]

        if not target_room:
            print('No room_type found in calendar response; cannot set prices')
            return

        # Use the correct prices/edit/prices endpoint with the proper pricing_plan_id
        print(f'Setting price {args.price} for {args.days} days starting today for property {args.id_properties} (room_type {target_room.get("id_room_types")})')
        
        # pkey already acquired above during calendar fetch
        print(f'Using pkey: {pkey[:10]}...')

        # Calculate dates
        from datetime import timedelta
        start_date = datetime.utcnow().date()
        end_date = start_date + timedelta(days=args.days-1)

        # Use the prices endpoint with the correct parameters from the curl example
        response = client.update_prices(
            token=creds['token'],
            key=pkey,
            id_properties=int(args.id_properties),
            id_pricing_plans=26946,  # ID del plan de precios obtenido del calendario anterior
            dfrom=start_date.isoformat(),
            dto=end_date.isoformat(),
            rooms=[{'id_room_types': int(target_room.get('id_room_types')), 'value': args.price}],
            variation_type=0,
            weekdays=[1,1,1,1,1,1,1]  # Todos los días de la semana como en el ejemplo
        )

        print(f'Update prices response: {response.status_code}')
        if response.status_code == 204:
            print(f'✅ Prices updated successfully from {start_date} to {end_date}')
        else:
            print(f'❌ Error updating prices: {response.text[:200]}')
        return


if __name__ == '__main__':
    main()
