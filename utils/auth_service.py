"""
utils/auth_service.py — Xác thực ví bằng chữ ký số
"""
from __future__ import annotations
import secrets
import time
from typing import Optional

from eth_account          import Account
from eth_account.messages import encode_defunct
from web3                 import Web3


class AuthChallenge:
    """Challenge-response auth. Challenge hết hạn sau 5 phút, dùng 1 lần."""

    EXPIRY_SECONDS = 300

    def __init__(self):
        self._store: dict[str, dict] = {}

    def create(self, wallet: str) -> dict:
        nonce     = secrets.token_hex(16)
        issued    = int(time.time())
        expires   = issued + self.EXPIRY_SECONDS

        msg = (
            f"Sign in to DAO Voting System\n\n"
            f"Wallet: {wallet}\n"
            f"Nonce: {nonce}\n"
            f"Expires: {_fmt(expires)}\n\n"
            f"This signature only authenticates your identity."
        )
        self._store[wallet.lower()] = {
            "message": msg, "nonce": nonce,
            "expires": expires, "used": False,
        }
        return {"message": msg, "nonce": nonce, "expires": expires}

    def verify(self, wallet: str, signature: str) -> dict:
        key  = wallet.lower()
        rec  = self._store.get(key)
        if not rec:
            return {"ok": False, "msg": "Không tìm thấy challenge. Tạo lại."}
        if time.time() > rec["expires"]:
            self._store.pop(key, None)
            return {"ok": False, "msg": "Challenge đã hết hạn (5 phút)."}
        if rec["used"]:
            return {"ok": False, "msg": "Challenge đã được dùng. Tạo lại."}

        try:
            signable  = encode_defunct(text=rec["message"])
            recovered = Web3().eth.account.recover_message(signable, signature=signature)
        except Exception as e:
            return {"ok": False, "msg": f"Chữ ký không hợp lệ: {e}"}

        if recovered.lower() != wallet.lower():
            return {"ok": False, "msg": "Chữ ký không khớp với địa chỉ ví."}

        rec["used"] = True
        return {"ok": True, "wallet": recovered}


class SessionManager:
    """Session token sau khi xác thực. Hết hạn sau 4 tiếng."""

    SESSION_TTL = 4 * 3600

    def __init__(self):
        self._store: dict[str, dict] = {}

    def create(self, wallet: str, info: dict = None) -> str:
        token = secrets.token_urlsafe(32)
        now   = int(time.time())
        self._store[token] = {
            "wallet":  wallet,
            "expires": now + self.SESSION_TTL,
            "info":    info or {},
        }
        return token

    def get(self, token: str) -> Optional[dict]:
        if not token:
            return None
        s = self._store.get(token)
        if not s:
            return None
        if time.time() > s["expires"]:
            self._store.pop(token, None)
            return None
        return s

    def wallet(self, token: str) -> Optional[str]:
        s = self.get(token)
        return s["wallet"] if s else None

    def destroy(self, token: str):
        self._store.pop(token, None)


def sign_and_send(w3, fn_call, wallet: str, private_key: str) -> dict:
    """
    Ký và gửi transaction. Private key dùng xong không giữ lại.

    FIX LỖI #6: trước đây gán private_key = None nhưng Python không
    thực sự xóa object — chỉ xóa tên biến local. Cách tốt nhất là
    không lưu key vào bất kỳ attribute hay global nào.
    """
    _k = private_key  # local only, không assign ra ngoài
    try:
        sender = Web3.to_checksum_address(wallet)
        tx     = fn_call.build_transaction({
            "from":  sender,
            "nonce": w3.eth.get_transaction_count(sender),
            "gas":   3_000_000,
        })
        signed  = w3.eth.account.sign_transaction(tx, _k)
        _k      = None  # xóa sớm nhất có thể
        # Compatible với cả web3.py 5.x (rawTransaction) và 6.x (raw_transaction)
        raw_tx  = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"success": receipt.status == 1, "txHash": tx_hash.hex(), "gasUsed": receipt.gasUsed}
    except Exception as e:
        _k = None
        return {"success": False, "error": str(e)}


def sign_message(message: str, private_key: str) -> str:
    """Ký message để xác thực (không tạo tx). Dùng trong demo."""
    signable = encode_defunct(text=message)
    signed   = Web3().eth.account.sign_message(signable, private_key=private_key)
    return signed.signature.hex()


def _fmt(ts: int) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S %d/%m/%Y")


# Singletons — dùng chung trong process Streamlit
_challenge = AuthChallenge()
_sessions  = SessionManager()

def challenges() -> AuthChallenge: return _challenge
def sessions()   -> SessionManager: return _sessions