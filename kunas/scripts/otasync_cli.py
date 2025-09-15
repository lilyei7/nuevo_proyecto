#!/usr/bin/env python3
"""OTASync small CLI

Features:
- Save/read credentials to ~/.config/otasync/credentials.txt (key=value)
- Actions: list-properties, export-properties
- Interactive menu if run without --action
- Non-interactive: pass --token/--username/--password and optionally --save to persist
"""
import os
import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.otasync_client import OTASyncClient

CRED_DIR = os.path.expanduser('~/.config/otasync')
CRED_PATH = os.path.join(CRED_DIR, 'credentials.txt')


def save_credentials(path: str, token: str, username: str, password: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"token={token}\n")
        f.write(f"username={username}\n")
        f.write(f"password={password}\n")
    os.chmod(os.path.dirname(path), 0o700)
    os.chmod(path, 0o600)


def load_credentials(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    data = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '=' not in line:
                continue
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip()
    return data


def list_properties(client: OTASyncClient, token: str, username: str, password: str):
    pkey, resp = client.login(token, username, password)
    print('Login status:', resp.status_code)
    if not pkey:
        print('No se obtuvo pkey. Respuesta:')
        print(resp.text[:1000])
        return None
    props = client.extract_properties_from_response(resp)
    return props


def export_properties_to_file(props, out_path: str, pretty: bool = False):
    if props is None:
        print('No properties to export')
        return
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2 if pretty else None)
    print(f'Properties saved to: {out_path}')


def interactive_menu(client: OTASyncClient, creds: dict):
    while True:
        print('\nChoose an action:')
        print('1) List properties')
        print('2) Export properties to file')
        print('3) Update saved credentials')
        print('4) Exit')
        choice = input('> ').strip()
        if choice == '1':
            props = list_properties(client, creds['token'], creds['username'], creds['password'])
            print(json.dumps(props or [], ensure_ascii=False, indent=2))
        elif choice == '2':
            out = input('Output filename (e.g. properties.json): ').strip() or 'properties.json'
            props = list_properties(client, creds['token'], creds['username'], creds['password'])
            export_properties_to_file(props, out, pretty=True)
        elif choice == '3':
            token = input('token: ')
            username = input('username: ')
            password = input('password: ')
            save_credentials(CRED_PATH, token, username, password)
            creds.update({'token': token, 'username': username, 'password': password})
            print('Credentials updated and saved.')
        elif choice == '4':
            break
        else:
            print('Invalid choice')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--username')
    parser.add_argument('--password')
    parser.add_argument('--save', action='store_true', help='Save provided credentials to credentials.txt')
    parser.add_argument('--action', choices=['list-properties', 'export-properties'], help='Non-interactive action')
    parser.add_argument('--out', help='Output file for export-properties')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output or saved file')
    parser.add_argument('--cred-file', default=CRED_PATH, help='Path to credentials file')
    args = parser.parse_args()

    client = OTASyncClient()

    # Load existing creds
    creds = load_credentials(args.cred_file)

    # Merge CLI-provided creds
    if args.token:
        creds['token'] = args.token
    if args.username:
        creds['username'] = args.username
    if args.password:
        creds['password'] = args.password

    # If --save requested and creds present, save
    if args.save:
        if not (creds.get('token') and creds.get('username') and creds.get('password')):
            print('Need token, username and password to save.')
            return
        save_credentials(args.cred_file, creds['token'], creds['username'], creds['password'])
        print('Credentials saved to', args.cred_file)

    # If non-interactive action requested
    if args.action:
        if not (creds.get('token') and creds.get('username') and creds.get('password')):
            print('Credentials missing: provide via CLI or save them first.')
            return
        if args.action == 'list-properties':
            props = list_properties(client, creds['token'], creds['username'], creds['password'])
            if args.pretty:
                print(json.dumps(props or [], ensure_ascii=False, indent=2))
            else:
                print(json.dumps(props or [], ensure_ascii=False))
            return
        if args.action == 'export-properties':
            props = list_properties(client, creds['token'], creds['username'], creds['password'])
            out = args.out or 'properties.json'
            export_properties_to_file(props, out, pretty=args.pretty)
            return

    # Otherwise interactive
    if not creds.get('token') or not creds.get('username') or not creds.get('password'):
        print('Credentials not found. Enter them now:')
        creds['token'] = input('token: ').strip()
        creds['username'] = input('username: ').strip()
        creds['password'] = input('password: ').strip()
        save = input('Save credentials to file for future use? (y/N): ').strip().lower()
        if save == 'y':
            save_credentials(args.cred_file, creds['token'], creds['username'], creds['password'])
            print('Saved.')

    interactive_menu(client, creds)


if __name__ == '__main__':
    main()
