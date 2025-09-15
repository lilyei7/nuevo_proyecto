#!/usr/bin/env python3
"""Interactive helper moved to kunas/ - manages price updates across all properties.

Now reads credentials from kunas/credentials.txt and stores backups in kunas/backups/.
"""
import os
import sys
import json
from datetime import datetime, timedelta
from getpass import getpass

# ensure repo root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.otasync_client import OTASyncClient

KUNAS_DIR = os.path.dirname(__file__)
BACKUPS_DIR = os.path.join(KUNAS_DIR, 'backups')
os.makedirs(BACKUPS_DIR, exist_ok=True)

CREDENTIALS_FILE = os.path.join(KUNAS_DIR, 'credentials.txt')


def read_credentials_from_file():
    creds = {}
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' not in line:
                    continue
                k, v = line.strip().split('=', 1)
                creds[k] = v
    return creds


def save_credentials_to_file(token, username, password):
    with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
        f.write(f"token={token}\n")
        f.write(f"username={username}\n")
        f.write(f"password={password}\n")
    print('Saved credentials to', CREDENTIALS_FILE)


def prompt_for_credentials():
    creds = read_credentials_from_file()
    if creds.get('token') and creds.get('username') and creds.get('password'):
        print('Found existing credentials in', CREDENTIALS_FILE)
        use = input('Use them? (Y/n): ').strip().lower() or 'y'
        if use == 'y':
            return creds
    print('Enter OTASync credentials (they will optionally be saved to kunas/credentials.txt)')
    token = input('Token: ').strip()
    username = input('Username: ').strip()
    password = getpass('Password: ')
    save = input('Save to kunas/credentials.txt? (y/N): ').strip().lower()
    if save == 'y':
        save_credentials_to_file(token, username, password)
    return {'token': token, 'username': username, 'password': password}


def export_properties(creds):
    client = OTASyncClient()
    pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
    print('Login status:', resp.status_code)
    if not pkey:
        print('Login failed. Response:', resp.text[:400])
        return None
    props, resp2 = client.get_properties_via_login(creds['token'], creds['username'], creds['password'])
    if not props:
        # try extract from resp
        props = client.extract_properties_from_response(resp)
    if not props:
        print('No properties found.')
        return None
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(BACKUPS_DIR, f'properties_{ts}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
    print('Exported properties to', out)
    return out


def safe_get_calendar(client, creds, pkey, id_properties, date=None, days=20):
    date = date or datetime.utcnow().strftime('%Y-%m-%d')
    r = client.get_calendar(creds['token'], pkey, int(id_properties), date=date, days=days)
    try:
        return r.json()
    except Exception:
        return None


def set_prices_for_property(client, creds, pkey, id_properties, price, days=20):
    # fetch calendar for property to discover room_type and pricing plan
    cal = safe_get_calendar(client, creds, pkey, id_properties, days=days)
    if not cal:
        print(f'Could not fetch calendar for property {id_properties}')
        return {'ok': False, 'error': 'no_calendar'}
    # find room_types
    room_types = []
    if isinstance(cal, dict):
        if 'room_types' in cal and isinstance(cal['room_types'], list):
            room_types = cal['room_types']
        elif 'filters' in cal and isinstance(cal['filters'], dict) and 'room_types' in cal['filters']:
            room_types = cal['filters']['room_types']
    if not room_types:
        print(f'No room_types available for property {id_properties}, skipping')
        return {'ok': False, 'error': 'no_room_types'}
    target = room_types[0]
    id_room_types = int(target.get('id_room_types'))
    # determine pricing plan id if present
    id_pricing_plans = None
    if isinstance(cal, dict):
        id_pricing_plans = cal.get('id_pricing_plans') or (cal.get('filters') or {}).get('default_price')
        try:
            id_pricing_plans = int(id_pricing_plans) if id_pricing_plans else None
        except Exception:
            id_pricing_plans = None
    start_date = datetime.utcnow().date()
    end_date = start_date + timedelta(days=days-1)
    payload = {
        'token': creds['token'],
        'key': pkey,
        'id_properties': int(id_properties),
        'id_pricing_plans': id_pricing_plans,
        'dfrom': start_date.isoformat(),
        'dto': end_date.isoformat(),
        'rooms': [{'id_room_types': id_room_types, 'value': price}],
        'variation_type': 0,
        'weekdays': [1,1,1,1,1,1,1]
    }
    print('Prepared payload for property', id_properties)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    # before sending, save current calendar/prices as backup
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    cal_backup = os.path.join(BACKUPS_DIR, f'calendar_{id_properties}_{ts}.json')
    with open(cal_backup, 'w', encoding='utf-8') as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)
    print('Saved calendar backup to', cal_backup)
    # send
    resp = client.update_prices(token=creds['token'], key=pkey, id_properties=int(id_properties),
                               id_pricing_plans=id_pricing_plans or 0, dfrom=payload['dfrom'], dto=payload['dto'],
                               rooms=payload['rooms'], variation_type=0, weekdays=payload['weekdays'])
    print('Response status:', resp.status_code)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    # save response
    resp_backup = os.path.join(BACKUPS_DIR, f'response_{id_properties}_{ts}.json')
    with open(resp_backup, 'w', encoding='utf-8') as f:
        json.dump({'status': resp.status_code, 'body': body}, f, ensure_ascii=False, indent=2)
    print('Saved response to', resp_backup)
    return {'ok': resp.status_code in (200, 204), 'status': resp.status_code, 'body': body, 'backups': {'calendar': cal_backup, 'response': resp_backup}}


def apply_to_all_properties(creds, price, days=20):
    client = OTASyncClient()
    pkey, resp = client.login(creds['token'], creds['username'], creds['password'])
    print('Login status:', resp.status_code)
    if not pkey:
        print('Login failed. Response:', resp.text[:400])
        return
    # get properties list
    props, _ = client.get_properties_via_login(creds['token'], creds['username'], creds['password'])
    if not props:
        props = client.extract_properties_from_response(resp) or []
    if not props:
        print('No properties to process')
        return
    results = []
    for p in props:
        idp = p.get('id_properties') or p.get('id_properties')
        if idp is None:
            continue
        print('\nProcessing property', idp, '-', p.get('name'))
        res = set_prices_for_property(client, creds, pkey, idp, price, days=days)
        results.append({'id': idp, 'name': p.get('name'), 'result': res})
    # save aggregated results
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(BACKUPS_DIR, f'set_prices_results_{ts}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('\nWrote results to', out)
    return out


def main():
    print('Manage prices helper (kunas)')
    creds = read_credentials_from_file()
    if not creds:
        creds = prompt_for_credentials()
    while True:
        print('\nChoose an action:')
        print('  1) Export properties to kunas/backups/')
        print('  2) Apply price to ALL properties (execute)')
        print('  3) Exit')
        choice = input('Select 1-3: ').strip()
        if choice == '1':
            export_properties(creds)
        elif choice == '2':
            price = input('Price to set (number): ').strip()
            try:
                price = int(price)
            except Exception:
                print('Invalid price')
                continue
            days = input('Days (default 20): ').strip() or '20'
            try:
                days = int(days)
            except Exception:
                print('Invalid days')
                continue
            print('This will process all properties found for the account.')
            confirm = input('Continue? (y/N): ').strip().lower()
            if confirm != 'y':
                print('Aborted by user')
                continue
            apply_to_all_properties(creds, price, days=days)
        elif choice == '3':
            print('Bye')
            break
        else:
            print('Invalid choice')

if __name__ == '__main__':
    main()
