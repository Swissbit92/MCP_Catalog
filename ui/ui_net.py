# ui/ui_net.py
# Tiny requests helper for background POSTs

import requests

def post_async(url: str, payload: dict, timeout: int, out_dict: dict):
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        try:
            out_dict["json"] = resp.json()
        except Exception:
            out_dict["json"] = None
        out_dict["text"] = resp.text
        out_dict["ok"] = resp.ok
        out_dict["status_code"] = resp.status_code
    except Exception as e:
        out_dict["error"] = str(e)
        out_dict["ok"] = False
