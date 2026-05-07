"""
utils/web3_helpers.py
─────────────────────
Các helper dùng trong Streamlit dashboard:
  - Kết nối Web3 tới Ganache
  - Load ABI từ artifacts/
  - Load địa chỉ contract từ dashboard/contract_addresses.json
  - Đọc dữ liệu on-chain: cổ đông, chiến dịch, voting power
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from web3 import Web3
from web3.contract import Contract

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
ARTIFACTS = ROOT / "artifacts" / "contracts"
ADDRESSES_FILE = ROOT / "dashboard" / "contract_addresses.json"


# ─── Connection ───────────────────────────────────────────────────────────────
def connect_web3(rpc_url: str = "http://127.0.0.1:7545") -> Web3:
    """
    Kết nối tới Ganache (hoặc bất kỳ EVM node nào).
    Raise ConnectionError nếu không thể kết nối.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(
            f"❌ Không thể kết nối tới {rpc_url}\n"
            "Hãy chắc chắn Ganache đang chạy."
        )
    return w3


# ─── ABI Loader ───────────────────────────────────────────────────────────────
def load_abi(contract_name: str) -> list:
    """
    Đọc ABI từ file artifacts Hardhat.
    Path: artifacts/contracts/{ContractName}.sol/{ContractName}.json
    """
    abi_path = ARTIFACTS / f"{contract_name}.sol" / f"{contract_name}.json"
    if not abi_path.exists():
        raise FileNotFoundError(
            f"ABI không tìm thấy: {abi_path}\n"
            "Hãy chạy: npx hardhat compile"
        )
    with open(abi_path, encoding='utf-8') as f:
        artifact = json.load(f)
    return artifact["abi"]


# ─── Address Loader ───────────────────────────────────────────────────────────
def load_addresses() -> dict:
    """
    Đọc địa chỉ contract đã deploy từ dashboard/contract_addresses.json.
    File này được tạo tự động bởi scripts/setup_demo.js.
    """
    if not ADDRESSES_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {ADDRESSES_FILE}\n"
            "Hãy chạy: npx hardhat run scripts/setup_demo.js"
        )
    with open(ADDRESSES_FILE, encoding='utf-8') as f:
        return json.load(f)


# ─── Contract Factory ─────────────────────────────────────────────────────────
def get_contract(w3: Web3, contract_name: str, address: str) -> Contract:
    """
    Tạo contract instance từ ABI + địa chỉ.
    """
    abi = load_abi(contract_name)
    checksum_addr = Web3.to_checksum_address(address)
    return w3.eth.contract(address=checksum_addr, abi=abi)


def get_all_contracts(w3: Web3) -> dict[str, Contract]:
    """
    Tiện ích: load toàn bộ contracts cùng một lúc.
    Returns:
        {
            "hst":      HSTToken contract,
            "registry": ShareholderRegistry contract,
            "gov":      GovernanceContract contract,
        }
    """
    addresses = load_addresses()
    return {
        "hst":      get_contract(w3, "HSTToken",             addresses["hstToken"]),
        "registry": get_contract(w3, "ShareholderRegistry",  addresses["registry"]),
        "gov":      get_contract(w3, "GovernanceContract",   addresses["governance"]),
    }


# ─── On-chain Queries ─────────────────────────────────────────────────────────
def get_shareholder_info(registry: Contract, wallet: str) -> Optional[dict]:
    """
    Đọc thông tin cổ đông từ registry.
    Returns None nếu địa chỉ chưa đăng ký.
    """
    try:
        wallet = Web3.to_checksum_address(wallet)
        raw = registry.functions.getShareholderInfo(wallet).call()
        return {
            "wallet":        raw[0],
            "identityHash":  raw[1].hex(),
            "lockUntil":     raw[2],
            "registeredAt":  raw[3],
            "isActive":      raw[4],
            "tier":          raw[5],
        }
    except Exception:
        return None


def get_voting_power(hst: Contract, wallet: str) -> float:
    """
    Lấy voting power hiện tại (sau delegation) của một địa chỉ.
    Returns số HST (float, không phải wei).
    """
    wallet = Web3.to_checksum_address(wallet)
    vp_wei = hst.functions.getVotes(wallet).call()
    return vp_wei / 10**18


def get_token_balance(hst: Contract, wallet: str) -> float:
    """
    Lấy số dư HST token (không phải voting power).
    Returns số HST (float).
    """
    wallet = Web3.to_checksum_address(wallet)
    bal_wei = hst.functions.balanceOf(wallet).call()
    return bal_wei / 10**18


def get_campaign_data(gov: Contract, campaign_id: int) -> Optional[dict]:
    """
    Đọc thông tin chiến dịch biểu quyết.
    """
    try:
        raw = gov.functions.getCampaign(campaign_id).call()
        status_labels = ["DRAFT","ACTIVE","COMMIT","REVEAL","TALLYING","EXECUTED","DEFEATED","CANCELLED"]
        type_labels   = ["Routine","Major","M&A"]
        mech_labels   = ["Linear","Quadratic","Equal"]

        return {
            "id":              raw[0],
            "title":           raw[1],
            "description":     raw[2],
            "proposer":        raw[3],
            "proposalType":    type_labels[raw[4]],
            "mechanism":       mech_labels[raw[5]],
            "status":          status_labels[raw[6]],
            "createdAt":       raw[7],
            "snapshotBlock":   raw[8],
            "votingStart":     raw[9],
            "votingDeadline":  raw[10],
            "commitDeadline":  raw[11],
            "revealStart":     raw[12],
            "revealDeadline":  raw[13],
            "isCommitReveal":  raw[14],
            "forVotes":        raw[15],
            "againstVotes":    raw[16],
            "abstainVotes":    raw[17],
            "passThreshold":   raw[18] / 100,  # basis points → %
            "quorumBps":       raw[19] / 100,
        }
    except Exception as e:
        return None


def get_all_campaigns(gov: Contract) -> list[dict]:
    """
    Lấy tất cả chiến dịch từ campaign ID 1 đến counter.
    """
    try:
        counter = gov.functions.campaignCounter().call()
    except Exception:
        return []

    campaigns = []
    for i in range(1, counter + 1):
        c = get_campaign_data(gov, i)
        if c:
            campaigns.append(c)
    return campaigns


def get_vote_participation(gov: Contract, hst: Contract, campaign_id: int) -> dict:
    """
    Tính tỷ lệ tham gia cho một chiến dịch.
    Returns dict với for_pct, against_pct, abstain_pct, participation_pct.
    """
    try:
        c = get_campaign_data(gov, campaign_id)
        if not c:
            return {}

        total_voted = c["forVotes"] + c["againstVotes"] + c["abstainVotes"]
        total_supply_wei = hst.functions.totalSupply().call()
        total_supply = total_supply_wei / 10**18

        decisive = c["forVotes"] + c["againstVotes"]

        return {
            "forVotes":         c["forVotes"],
            "againstVotes":     c["againstVotes"],
            "abstainVotes":     c["abstainVotes"],
            "totalVoted":       total_voted,
            "totalSupply":      total_supply,
            "participationPct": round(total_voted / total_supply * 100, 2) if total_supply > 0 else 0,
            "forPct":           round(c["forVotes"] / decisive * 100, 2) if decisive > 0 else 0,
            "againstPct":       round(c["againstVotes"] / decisive * 100, 2) if decisive > 0 else 0,
        }
    except Exception:
        return {}


# ─── Quick test (chạy trực tiếp) ──────────────────────────────────────────────
if __name__ == "__main__":
    try:
        w3 = connect_web3()
        print(f"✅ Connected | Block: {w3.eth.block_number} | ChainID: {w3.eth.chain_id}")
        addrs = load_addresses()
        print(f"   HST Token:  {addrs['hstToken']}")
        print(f"   Registry:   {addrs['registry']}")
        print(f"   Governance: {addrs['governance']}")
    except FileNotFoundError as e:
        print(f"⚠️  {e}")
    except ConnectionError as e:
        print(f"⚠️  {e}")