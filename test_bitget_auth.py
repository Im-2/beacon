#!/usr/bin/env python3
"""Dev-only: read-only validation that BITGET_* credentials in .env actually
authenticate against Bitget's Demo Trading environment. Calls GET
/api/v2/spot/account/assets with the paptrading header — no write/order
endpoint is touched."""
import time
from beacon import config
from beacon.execute import _sign, BASE_URL

PATH = "/api/v2/spot/account/assets"


def main():
    creds = config.bitget_creds()
    timestamp = str(int(time.time() * 1000))
    signature = _sign(timestamp, "GET", PATH, "", creds["secret_key"])
    headers = {
        "ACCESS-KEY": creds["api_key"],
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": creds["passphrase"],
        "Content-Type": "application/json",
        "paptrading": "1",
    }
    import requests
    resp = requests.get(BASE_URL + PATH, headers=headers, timeout=30)
    print("HTTP status:", resp.status_code)
    print(resp.json())


if __name__ == "__main__":
    main()
