"""
utils/kyc_service.py
══════════════════════════════════════════════════════════════
KYC Service — Phần OFF-CHAIN của hệ thống xác thực danh tính

Module này đảm nhiệm phần Admin (off-chain):
  1. Nhận thông tin CCCD từ người dùng
  2. Tạo identityHash từ thông tin thật
  3. Ký KYC proof bằng private key của KYC_SIGNER
  4. Trả signature cho người dùng để submit on-chain

── FLOW ĐẦY ĐỦ ──────────────────────────────────────────────
  [OFF-CHAIN] Người dùng → form điền tên, số CCCD, ngày sinh
       ↓
  [OFF-CHAIN] kyc_service.py tạo identityHash (hash thông tin)
       ↓
  [OFF-CHAIN] Admin xác minh giấy tờ thật (manual review)
       ↓
  [OFF-CHAIN] kyc_service.py ký signature bằng KYC_SIGNER key
       ↓
  [ON-CHAIN]  Người dùng gọi IdentityVerifier.submitKYC(signature)
       ↓
  [ON-CHAIN]  Contract verify signature → lưu KYC record

── BẢO MẬT ──────────────────────────────────────────────────
  identityHash = keccak256(tên + CCCD + ngày sinh)
  → Lưu on-chain nhưng KHÔNG lộ thông tin gốc
  → Chỉ Admin biết mapping hash → người thật
  → Ai cũng có thể verify "ví này đã KYC" mà không biết là ai
══════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import hashlib
import secrets
import json
from datetime import datetime, date
from pathlib  import Path
from typing   import Optional

from eth_account            import Account
from eth_account.messages   import encode_defunct
from web3                   import Web3


# ─── KYC Levels ───────────────────────────────────────────────
KYC_LEVEL = {
    "NONE":     0,
    "BASIC":    1,   # Email + SĐT
    "STANDARD": 2,   # CCCD
    "FULL":     3,   # CCCD + selfie + địa chỉ
}

KYC_LEVEL_LABEL = {v: k for k, v in KYC_LEVEL.items()}


# ─── Tạo Identity Hash (OFF-CHAIN) ────────────────────────────
def create_identity_hash(
    full_name:   str,
    national_id: str,
    date_of_birth: str,  # Format: "YYYY-MM-DD"
    country:     str = "VN"
) -> str:
    """
    Tạo identityHash từ thông tin thật của người dùng.

    Hash này:
      - Lưu on-chain (không lộ thông tin gốc)
      - Dùng để verify "ví này thuộc về người này"
      - Không thể reverse để tìm lại thông tin gốc

    Args:
        full_name:     Họ và tên đầy đủ (chuẩn hóa chữ hoa)
        national_id:   Số CCCD / hộ chiếu
        date_of_birth: Ngày sinh "YYYY-MM-DD"
        country:       Quốc tịch

    Returns:
        identityHash dạng hex string "0x..."
    """
    # Chuẩn hóa: uppercase, loại bỏ khoảng trắng thừa
    name_normalized = " ".join(full_name.upper().split())
    id_normalized   = national_id.strip().upper()
    dob_normalized  = date_of_birth.strip()
    country_norm    = country.upper()

    # Tạo hash bằng keccak256 (giống Solidity)
    raw = f"{name_normalized}|{id_normalized}|{dob_normalized}|{country_norm}"
    identity_hash = Web3.keccak(text=raw)
    return "0x" + identity_hash.hex()


def create_kyc_hash(
    identity_hash: str,
    kyc_level:     int,
    timestamp:     int,
    extra_data:    str = ""
) -> str:
    """
    Tạo kycHash — hash của toàn bộ KYC session.
    Lưu on-chain như audit trail.

    Args:
        identity_hash: Hash danh tính (từ create_identity_hash)
        kyc_level:     Mức KYC (1/2/3)
        timestamp:     Unix timestamp lúc KYC
        extra_data:    Thông tin bổ sung (mã hồ sơ nội bộ, ...)
    """
    raw = f"{identity_hash}|{kyc_level}|{timestamp}|{extra_data}"
    return "0x" + Web3.keccak(text=raw).hex()


# ─── Tạo KYC Signature (OFF-CHAIN, Admin ký) ─────────────────
def sign_kyc_approval(
    wallet_address:   str,
    identity_hash:    str,
    kyc_hash:         str,
    kyc_level:        int,
    nonce:            str,
    chain_id:         int,
    signer_private_key: str
) -> dict:
    """
    Admin ký KYC proof bằng private key của KYC_SIGNER.

    Message được ký (phải khớp với _buildKYCMessage() trong Solidity):
        keccak256("KYC_VERIFY" + identityHash + kycHash + level + nonce + wallet + chainId)

    Args:
        wallet_address:    Ví cổ đông cần được KYC
        identity_hash:     Hash danh tính (0x...)
        kyc_hash:          Hash KYC session (0x...)
        kyc_level:         Mức KYC (1/2/3)
        nonce:             Random bytes32 (0x...) — chống replay
        chain_id:          Chain ID (1337=Ganache, 80002=Amoy)
        signer_private_key: Private key của KYC_SIGNER account

    Returns:
        {
            "signature":   "0x...",   # Chữ ký để submit on-chain
            "messageHash": "0x...",   # Hash message đã ký
            "signer":      "0x...",   # Địa chỉ signer (để verify)
        }
    """
    w3 = Web3()

    # Encode message giống Solidity abi.encodePacked()
    message_bytes = (
        b"KYC_VERIFY"
        + bytes.fromhex(identity_hash[2:])   # bytes32
        + bytes.fromhex(kyc_hash[2:])        # bytes32
        + kyc_level.to_bytes(1, "big")       # uint8
        + bytes.fromhex(nonce[2:])           # bytes32
        + bytes.fromhex(wallet_address[2:])  # address (20 bytes)
        + chain_id.to_bytes(32, "big")       # uint256
    )

    message_hash = Web3.keccak(message_bytes)
    signable     = encode_defunct(primitive=message_hash)
    signed       = w3.eth.account.sign_message(signable, private_key=signer_private_key)

    return {
        "signature":   signed.signature.hex() if not isinstance(signed.signature, str) else signed.signature,
        "messageHash": "0x" + message_hash.hex(),
        "signer":      Account.from_key(signer_private_key).address,
    }


def generate_nonce() -> str:
    """Tạo nonce ngẫu nhiên (bytes32) để chống replay attack."""
    return "0x" + secrets.token_hex(32)


# ─── KYC Admin Service ────────────────────────────────────────
class KYCService:
    """
    Service quản lý quy trình KYC.
    Trong production: chạy trên server bảo mật của Admin.
    Trong demo: chạy local, signer_private_key từ .env.
    """

    def __init__(self, signer_private_key: str, chain_id: int = 1337):
        self.signer_key = signer_private_key
        self.chain_id   = chain_id
        self.signer_address = Account.from_key(signer_private_key).address
        self._pending_kyc: dict[str, dict] = {}  # wallet → pending data

    @property
    def signer(self) -> str:
        return self.signer_address

    def submit_kyc_request(
        self,
        wallet:        str,
        full_name:     str,
        national_id:   str,
        date_of_birth: str,
        country:       str = "VN",
        kyc_level:     int = KYC_LEVEL["STANDARD"],
        extra_notes:   str = ""
    ) -> dict:
        """
        Bước 1: Người dùng submit thông tin KYC.
        Lưu vào pending queue để Admin review.

        Returns:
            {"requestId": str, "status": "PENDING", "identityHash": str}
        """
        identity_hash = create_identity_hash(full_name, national_id, date_of_birth, country)
        request_id    = secrets.token_hex(8)
        timestamp     = int(datetime.now().timestamp())

        self._pending_kyc[wallet.lower()] = {
            "requestId":    request_id,
            "wallet":       wallet,
            "full_name":    full_name,      # OFF-CHAIN: không lên blockchain
            "national_id":  national_id,    # OFF-CHAIN: không lên blockchain
            "date_of_birth": date_of_birth, # OFF-CHAIN: không lên blockchain
            "country":      country,
            "kyc_level":    kyc_level,
            "identity_hash": identity_hash,  # ON-CHAIN: chỉ hash mới lên
            "submitted_at": timestamp,
            "extra_notes":  extra_notes,
            "status":       "PENDING",
        }

        return {
            "requestId":    request_id,
            "status":       "PENDING",
            "identityHash": identity_hash,
            "message":      "KYC request submitted. Awaiting admin review.",
        }

    def approve_kyc(self, wallet: str) -> Optional[dict]:
        """
        Bước 2: Admin xác minh và ký approval.

        Returns:
            {
                "identityHash":    str,
                "kycHash":         str,
                "level":           int,
                "nonce":           str,
                "country":         str,
                "adminSignature":  str,
                "signer":          str,
            }
            Người dùng dùng dict này để gọi submitKYC() on-chain.
        """
        key = wallet.lower()
        if key not in self._pending_kyc:
            raise ValueError(f"Không tìm thấy KYC request cho {wallet}")

        pending = self._pending_kyc[key]
        if pending["status"] != "PENDING":
            raise ValueError(f"KYC request status: {pending['status']}")

        timestamp     = int(datetime.now().timestamp())
        identity_hash = pending["identity_hash"]
        kyc_level     = pending["kyc_level"]
        nonce         = generate_nonce()
        kyc_hash      = create_kyc_hash(identity_hash, kyc_level, timestamp)

        # Admin ký off-chain
        sig_result = sign_kyc_approval(
            wallet_address    = wallet,
            identity_hash     = identity_hash,
            kyc_hash          = kyc_hash,
            kyc_level         = kyc_level,
            nonce             = nonce,
            chain_id          = self.chain_id,
            signer_private_key= self.signer_key,
        )

        pending["status"]    = "APPROVED"
        pending["approved_at"] = timestamp

        return {
            "wallet":          wallet,
            "identityHash":    identity_hash,
            "kycHash":         kyc_hash,
            "level":           kyc_level,
            "nonce":           nonce,
            "country":         pending["country"],
            "adminSignature":  "0x" + sig_result["signature"] if not sig_result["signature"].startswith("0x") else sig_result["signature"],
            "signer":          sig_result["signer"],
            "chainId":         self.chain_id,
            "approvedAt":      timestamp,
            # Hướng dẫn submit on-chain
            "nextStep": (
                "Gọi IdentityVerifier.submitKYC("
                f"'{identity_hash}', '{kyc_hash}', {kyc_level}, '{nonce}', "
                f"'{pending['country']}', '<adminSignature>') từ ví {wallet}"
            ),
        }

    def reject_kyc(self, wallet: str, reason: str):
        """Admin từ chối KYC."""
        key = wallet.lower()
        if key not in self._pending_kyc:
            raise ValueError(f"Không tìm thấy request cho {wallet}")
        self._pending_kyc[key]["status"] = "REJECTED"
        self._pending_kyc[key]["reject_reason"] = reason

    def get_pending_requests(self) -> list[dict]:
        """Lấy danh sách KYC đang chờ duyệt."""
        return [
            {k: v for k, v in req.items()
             if k not in ("national_id", "full_name", "date_of_birth")}  # Ẩn thông tin nhạy cảm
            for req in self._pending_kyc.values()
            if req["status"] == "PENDING"
        ]


# ─── Submit KYC lên On-chain (người dùng gọi) ─────────────────
def submit_kyc_onchain(
    w3,
    identity_verifier_contract,
    wallet_address:   str,
    private_key:      str,
    kyc_approval:     dict,
) -> dict:
    """
    Người dùng submit KYC proof lên IdentityVerifier contract.

    Args:
        kyc_approval: Dict từ KYCService.approve_kyc()

    Returns:
        {"success": bool, "txHash": str, "error": str}
    """
    try:
        wallet = Web3.to_checksum_address(wallet_address)

        # Convert hex strings → bytes32 cho Solidity
        identity_hash_bytes = bytes.fromhex(kyc_approval["identityHash"][2:])
        kyc_hash_bytes      = bytes.fromhex(kyc_approval["kycHash"][2:])
        nonce_bytes         = bytes.fromhex(kyc_approval["nonce"][2:])
        signature_bytes     = bytes.fromhex(
            kyc_approval["adminSignature"][2:]
            if kyc_approval["adminSignature"].startswith("0x")
            else kyc_approval["adminSignature"]
        )

        fn = identity_verifier_contract.functions.submitKYC(
            identity_hash_bytes,         # bytes32
            kyc_hash_bytes,              # bytes32
            kyc_approval["level"],       # uint8 (KYCLevel enum)
            nonce_bytes,                 # bytes32
            kyc_approval["country"],     # string
            signature_bytes,             # bytes
        )

        tx = fn.build_transaction({
            "from":  wallet,
            "nonce": w3.eth.get_transaction_count(wallet),
            "gas":   500_000,
        })
        signed  = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "success": receipt.status == 1,
            "txHash":  tx_hash.hex(),
            "gasUsed": receipt.gasUsed,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Quick demo ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  KYC Service Demo")
    print("=" * 60)

    # Demo: tạo identity hash từ thông tin giả
    id_hash = create_identity_hash(
        full_name    = "Nguyễn Văn An",
        national_id  = "012345678901",
        date_of_birth= "1990-01-15",
        country      = "VN"
    )
    print(f"\n  identityHash (lưu on-chain): {id_hash}")
    print(f"  Thông tin gốc (chỉ Admin biết, OFF-CHAIN): Nguyễn Văn An / 012345678901 / 1990-01-15")

    # Demo: nonce
    nonce = generate_nonce()
    print(f"\n  Nonce (chống replay): {nonce}")

    print("\n  Flow:")
    print("  1. Người dùng gửi CCCD → Admin")
    print("  2. Admin xác minh → gọi KYCService.approve_kyc()")
    print("  3. KYCService ký signature → trả về cho người dùng")
    print("  4. Người dùng gọi IdentityVerifier.submitKYC() on-chain")
    print("  5. Contract verify signature → lưu KYC record")
    print("=" * 60)
