"""
utils/web3_helpers_amoy.py
══════════════════════════════════════════════════════════════
Helper hỗ trợ kết nối cả Ganache (local) lẫn Polygon Amoy (testnet).

Dashboard tự động detect môi trường dựa trên:
  - Biến môi trường AMOY_MODE=true  → kết nối Amoy
  - Mặc định                        → kết nối Ganache local

Khi dùng Amoy:
  - Đọc contract_addresses_amoy.json thay vì contract_addresses.json
  - RPC URL: https://rpc-amoy.polygon.technology
  - Explorer: https://amoy.polygonscan.com
══════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing  import Optional

from web3 import Web3


ROOT      = Path(__file__).parent.parent
DASH_DIR  = ROOT / "dashboard"

# ── Config theo môi trường ────────────────────────────────────
NETWORK_CONFIG = {
    "ganache": {
        "rpc_url":       os.getenv("GANACHE_RPC_URL", "http://127.0.0.1:7545"),
        "chain_id":      1337,
        "explorer":      None,
        "addresses_file": DASH_DIR / "contract_addresses.json",
        "name":          "Ganache Local",
        "is_testnet":    False,
    },
    "amoy": {
        "rpc_url":       os.getenv("AMOY_RPC_URL", "https://rpc-amoy.polygon.technology"),
        "chain_id":      80002,
        "explorer":      "https://amoy.polygonscan.com",
        "addresses_file": DASH_DIR / "contract_addresses_amoy.json",
        "name":          "Polygon Amoy Testnet",
        "is_testnet":    True,
    },
}


def get_active_network() -> str:
    """
    Xác định mạng đang dùng dựa trên biến môi trường.
    AMOY_MODE=true → amoy
    Mặc định       → ganache
    """
    return "amoy" if os.getenv("AMOY_MODE", "").lower() == "true" else "ganache"


def get_network_config() -> dict:
    """Lấy config của mạng đang active."""
    return NETWORK_CONFIG[get_active_network()]


def connect_web3_auto() -> tuple[Web3, dict]:
    """
    Kết nối tự động dựa trên môi trường.

    Returns:
        (w3, network_config)
    """
    cfg = get_network_config()
    w3  = Web3(Web3.HTTPProvider(cfg["rpc_url"]))

    if not w3.is_connected():
        raise ConnectionError(
            f"Không thể kết nối tới {cfg['name']} ({cfg['rpc_url']})\n"
            + ("Hãy chắc chắn Ganache đang chạy."
               if not cfg["is_testnet"]
               else "Kiểm tra kết nối internet và RPC URL.")
        )
    return w3, cfg


def load_addresses_auto() -> dict:
    """
    Đọc địa chỉ contract theo mạng đang active.
    """
    cfg  = get_network_config()
    file = cfg["addresses_file"]
    if not file.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {file}\n"
            + ("Chạy: npx hardhat run scripts/setup_demo.js --network ganache"
               if not cfg["is_testnet"]
               else "Chạy: npx hardhat run scripts/deploy_amoy.js --network amoy")
        )
    with open(file, encoding="utf-8") as f:
        return json.load(f)


def get_explorer_url(address: str) -> Optional[str]:
    """
    Lấy link Explorer cho một địa chỉ.
    Trả về None nếu đang dùng Ganache (không có explorer).
    """
    cfg = get_network_config()
    if cfg["explorer"] and address:
        return f"{cfg['explorer']}/address/{address}"
    return None


def get_tx_url(tx_hash: str) -> Optional[str]:
    """Link Explorer cho một transaction."""
    cfg = get_network_config()
    if cfg["explorer"] and tx_hash:
        return f"{cfg['explorer']}/tx/{tx_hash}"
    return None


def switch_network(network: str):
    """
    Chuyển đổi mạng bằng cách set biến môi trường.
    Dùng trong Dashboard để toggle Ganache ↔ Amoy.
    """
    if network not in NETWORK_CONFIG:
        raise ValueError(f"Network không hợp lệ: {network}")
    os.environ["AMOY_MODE"] = "true" if network == "amoy" else "false"


# ── Kiểm tra MATIC balance (cho Amoy) ─────────────────────────
def check_matic_balance(w3: Web3, address: str) -> dict:
    """
    Kiểm tra số dư MATIC (ETH native trên Polygon).
    Cần MATIC để trả phí gas khi bỏ phiếu trên Amoy.
    """
    try:
        balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
        balance     = float(Web3.from_wei(balance_wei, "ether"))
        return {
            "balance": balance,
            "sufficient": balance > 0.001,  # Cần ít nhất 0.001 MATIC để vote
            "hint": (
                f"✅ Đủ MATIC ({balance:.4f} MATIC)"
                if balance > 0.001
                else f"⚠️ Thiếu MATIC ({balance:.6f}) — Lấy tại faucet.polygon.technology"
            )
        }
    except Exception as e:
        return {"balance": 0, "sufficient": False, "hint": str(e)}
