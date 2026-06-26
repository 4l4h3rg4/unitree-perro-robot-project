"""
Compatibility patch for go2-webrtc-connect 0.2.1.

The PyPI package still parses the newer Go2 LAN handshake as plaintext RSA.
Recent Go2 firmware returns con_notify with data2=2, where data1 is AES-GCM
encrypted with Unitree's static legacy key. This patches only the local LAN
SDP exchange, matching upstream unitree_webrtc_connect 2.1.x behavior.
"""

from __future__ import annotations

import base64
import json
import logging
import socket

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from go2_webrtc_driver.encryption import (
    aes_decrypt,
    aes_encrypt,
    generate_aes_key,
    rsa_encrypt,
    rsa_load_public_key,
)
import go2_webrtc_driver.unitree_auth as unitree_auth


_LEGACY_GCM_KEY = bytes(
    [232, 86, 130, 189, 22, 84, 155, 0, 142, 4, 166, 104, 43, 179, 235, 227]
)


class LocalSignalingPortError(RuntimeError):
    def __init__(self, ip: str):
        super().__init__(
            f"Robot at {ip} is not exposing LAN signaling on ports 9991 or 8081."
        )


class AesKeyRequiredError(RuntimeError):
    def __init__(self):
        super().__init__(
            "This robot uses data2=3 LAN auth and requires its per-device "
            "AES-128 key. Fetch the key from the Unitree account/cloud binding."
        )


def _decrypt_data1_legacy(data1_b64: str) -> str:
    raw = base64.b64decode(data1_b64)
    if len(raw) < 28:
        raise ValueError("data1 too short for legacy GCM decrypt")
    tag = raw[-16:]
    nonce = raw[-28:-16]
    ciphertext = raw[:-28]
    return AESGCM(_LEGACY_GCM_KEY).decrypt(nonce, ciphertext + tag, None).decode(
        "utf-8"
    )


def _calc_local_path_ending(data1: str) -> str:
    chars = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    chunks = [data1[-10:][i : i + 2] for i in range(0, 10, 2)]
    out = []
    for chunk in chunks:
        if len(chunk) > 1:
            out.append(chars.index(chunk[1]))
    return "".join(map(str, out))


def _post(url: str, body=None, headers=None):
    response = requests.post(url=url, data=body, headers=headers, timeout=8)
    response.raise_for_status()
    return response if response.status_code == 200 else None


def _probe_tcp_port(ip: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _send_sdp_to_local_peer_old_method(ip: str, sdp: str):
    response = _post(
        f"http://{ip}:8081/offer",
        body=sdp,
        headers={"Content-Type": "application/json"},
    )
    if response:
        return response.text
    return None


def _send_sdp_to_local_peer_new_method(ip: str, sdp: str, aes_128_key: str = None):
    response = _post(f"http://{ip}:9991/con_notify")
    if not response:
        return None

    decoded = json.loads(base64.b64decode(response.text).decode("utf-8"))
    data1 = decoded.get("data1")
    data2 = decoded.get("data2")

    if data2 == 2:
        data1 = _decrypt_data1_legacy(data1)
    elif data2 == 3:
        raise AesKeyRequiredError()

    public_key_pem = data1[10 : len(data1) - 10]
    path_ending = _calc_local_path_ending(data1)

    aes_key = generate_aes_key()
    public_key = rsa_load_public_key(public_key_pem)
    body = {
        "data1": aes_encrypt(sdp, aes_key),
        "data2": rsa_encrypt(aes_key, public_key),
    }

    response = _post(
        f"http://{ip}:9991/con_ing_{path_ending}",
        body=json.dumps(body),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response:
        return aes_decrypt(response.text, aes_key)
    return None


def _send_sdp_to_local_peer(ip: str, sdp: str):
    if _probe_tcp_port(ip, 9991):
        print(f"LAN Signaling Method: con_notify ({ip}:9991)")
        return _send_sdp_to_local_peer_new_method(ip, sdp)
    if _probe_tcp_port(ip, 8081):
        print(f"LAN Signaling Method: legacy /offer ({ip}:8081)")
        return _send_sdp_to_local_peer_old_method(ip, sdp)
    raise LocalSignalingPortError(ip)


def apply_webrtc_compat_patch() -> None:
    unitree_auth.send_sdp_to_local_peer = _send_sdp_to_local_peer
    logging.getLogger(__name__).info("Applied Go2 WebRTC data2=2 compat patch")

