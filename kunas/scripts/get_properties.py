#!/usr/bin/env python3
"""Get properties script for OTASync API.

Usage:
  python scripts/get_properties.py --token <TOKEN> --username <USER> --password <PWD> [--out properties.json] [--pretty]

Reads credentials from env if not provided. Logs in once, extracts `properties` from the login response and prints them.
If --out is provided, writes JSON to that file.
"""
import os
import sys
import argparse
import json

# ensure project root on sys.path so we can import scripts.otasync_client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.otasync_client import OTASyncClient


def main():
    parser = argparse.ArgumentParser(description="Obtener properties desde OTASync API (login -> extract properties)")
    parser.add_argument('--token', help='Partner token', default=os.getenv('OTASYNC_TOKEN'))
    parser.add_argument('--username', help='Username', default=os.getenv('OTASYNC_USERNAME'))
    parser.add_argument('--password', help='Password', default=os.getenv('OTASYNC_PASSWORD'))
    parser.add_argument('--out', help='Archivo JSON de salida (ej: properties.json)')
    parser.add_argument('--pretty', help='Pretty-print JSON', action='store_true')
    parser.add_argument('--save-key', help='Guardar pkey en ~/.config/otasync/pkey', action='store_true')
    args = parser.parse_args()

    # If credentials not provided via env/args, try to read ./credentials.txt in project root
    if not (args.token and args.username and args.password):
        cred_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.txt')
        if os.path.exists(cred_file):
            with open(cred_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' not in line:
                        continue
                    k, v = line.strip().split('=', 1)
                    if k == 'token' and not args.token:
                        args.token = v
                    if k == 'username' and not args.username:
                        args.username = v
                    if k == 'password' and not args.password:
                        args.password = v

    if not (args.token and args.username and args.password):
        print('Faltan credenciales. Exporta OTASYNC_TOKEN/OTASYNC_USERNAME/OTASYNC_PASSWORD o pásalas como argumentos, o crea ./credentials.txt')
        return

    client = OTASyncClient()
    print('Logueando...')
    pkey, resp = client.login(args.token, args.username, args.password)
    print('Login status:', resp.status_code)
    if not pkey:
        print('No se obtuvo pkey. Respuesta:')
        print(resp.text[:1000])
        return

    # optionally save key
    if args.save_key:
        key_dir = os.path.expanduser('~/.config/otasync')
        key_path = os.path.join(key_dir, 'pkey')
        try:
            os.makedirs(key_dir, exist_ok=True)
            with open(key_path, 'w') as f:
                f.write(pkey)
            os.chmod(key_dir, 0o700)
            os.chmod(key_path, 0o600)
            print(f'pkey guardado en: {key_path}')
        except Exception as e:
            print('Error guardando pkey:', e)

    props = client.extract_properties_from_response(resp)
    if props is None:
        print('No se encontraron properties en la respuesta.')
        return

    # print to stdout
    if args.pretty:
        print(json.dumps(props, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(props, ensure_ascii=False))

    # write file if requested
    if args.out:
        try:
            with open(args.out, 'w', encoding='utf-8') as f:
                json.dump(props, f, ensure_ascii=False, indent=2 if args.pretty else None)
            print(f'Properties guardadas en: {args.out}')
        except Exception as e:
            print('Error guardando archivo:', e)


if __name__ == '__main__':
    main()
