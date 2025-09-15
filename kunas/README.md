OTASync API minimal client and tester

Files:
- `scripts/otasync_client.py` : minimal client with login/logout/edit_one_signal
- `scripts/run_test.py` : simple CLI to run a login -> one_signal -> logout sequence
- `tests/test_client.py` : unit tests (mocked) to validate parsing behavior

Setup

1) Create a virtualenv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Export credentials (or pass as args):

```bash
export OTASYNC_TOKEN=your_token
export OTASYNC_USERNAME=your_user
export OTASYNC_PASSWORD=your_pass
```

3) Run the test script (it will not run successfully without valid credentials):

```bash
python scripts/run_test.py
```

Save obtained pkey

You can save the `pkey` that the login returns to a secure file with the `--save-key` flag. It will be stored at `~/.config/otasync/pkey` with permissions `600`:

```bash
python scripts/run_test.py --save-key
```

4) Run unit tests (these are mocked and do NOT call the real API):

```bash
pytest -q
```

Notes
- The API sometimes returns `text/html` with embedded JSON; the client includes a heuristic to extract `pkey` from HTML when needed.
- To obtain the partner token contact the API support per the documentation.
