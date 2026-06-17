"""
utils/web3_helpers.py
─────────────────────────────────────────────────────────────
Các helper dùng trong Streamlit dashboard.

── ON-CHAIN (module này ĐỌC từ blockchain) ──────────────────
  HSTToken, Registry, Governance, VotingCertificate

── OFF-CHAIN (module này QUẢN LÝ) ───────────────────────────
  contract_addresses.json, ABI artifacts, certificate files
─────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
from pathlib import Path
from typing  import Optional
from web3          import Web3
from web3.contract import Contract

ROOT           = Path(__file__).parent.parent
ARTIFACTS      = ROOT / "artifacts" / "contracts"
ADDRESSES_FILE = ROOT / "dashboard" / "contract_addresses.json"


def connect_web3(rpc_url: str = "http://127.0.0.1:7545") -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Không thể kết nối tới {rpc_url}")
    return w3


def load_abi(contract_name: str) -> list:
    abi_path = ARTIFACTS / f"{contract_name}.sol" / f"{contract_name}.json"
    if not abi_path.exists():
        raise FileNotFoundError(f"ABI không tìm thấy: {abi_path}\nChạy: npx hardhat compile")
    with open(abi_path, encoding="utf-8") as f:
        return json.load(f)["abi"]


def load_addresses() -> dict:
    if not ADDRESSES_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy {ADDRESSES_FILE}\nChạy: npx hardhat run scripts/setup_demo.js")
    with open(ADDRESSES_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_contract(w3: Web3, contract_name: str, address: str) -> Contract:
    abi = load_abi(contract_name)
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def get_all_contracts(w3: Web3) -> dict[str, Contract]:
    addrs = load_addresses()
    result = {
        "hst":      get_contract(w3, "HSTToken",            addrs["hstToken"]),
        "registry": get_contract(w3, "ShareholderRegistry", addrs["registry"]),
        "gov":      get_contract(w3, "GovernanceContract",  addrs["governance"]),
        "cert":     None,
    }
    if addrs.get("votingCertificate"):
        try:
            result["cert"] = get_contract(w3, "VotingCertificate", addrs["votingCertificate"])
        except Exception:
            pass
    return result


# ─── Token Info (Nhận xét thầy #1) ───────────────────────────
def get_token_info(hst: Contract) -> dict:
    """
    Vai trò token HST:
      [1] Chứng nhận sở hữu: 1 HST = 1 đơn vị cổ phần
      [2] Quyền biểu quyết: cần delegate() để kích hoạt
      [3] Chứng minh tư cách: số HST xác định Tier cổ đông
    """
    try:
        raw = hst.functions.getTokenInfo().call()
        return {
            "name":        raw[0],
            "symbol":      raw[1],
            "decimals":    raw[2],
            "totalSupply": raw[3],
            "supplyHST":   raw[4],
            "owner":       raw[5],
            "roles": {
                "ownership":   "1 HST = 1 đơn vị cổ phần",
                "votingPower": "Cần delegate() để kích hoạt voting power",
                "tierBasis":   "Tier 0-3 dựa theo % HST nắm giữ",
            }
        }
    except Exception as e:
        return {"error": str(e)}


def get_delegation_status(hst: Contract, wallet: str) -> dict:
    try:
        wallet = Web3.to_checksum_address(wallet)
        raw    = hst.functions.getDelegationStatus(wallet).call()
        bal    = hst.functions.balanceOf(wallet).call() / 10**18
        return {
            "isDelegated": raw[0],
            "votingPower": raw[1] / 10**18,
            "balance":     bal,
            "hint": "✅ Đã kích hoạt voting power" if raw[0]
                    else "⚠️ Chưa delegate — gọi delegate() để vote được"
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Shareholder ──────────────────────────────────────────────
def get_shareholder_info(registry: Contract, wallet: str) -> Optional[dict]:
    TIER_LABEL = ["Nhỏ lẻ (<1%)", "Tổ chức (≥1%)", "Chiến lược (≥10%)", "Sáng lập (≥30%)"]
    try:
        wallet = Web3.to_checksum_address(wallet)
        raw    = registry.functions.getShareholderInfo(wallet).call()
        return {
            "wallet":       raw[0],
            "identityHash": raw[1].hex(),
            "lockUntil":    raw[2],
            "registeredAt": raw[3],
            "isActive":     raw[4],
            "tier":         raw[5],
            "tierLabel":    TIER_LABEL[raw[5]] if raw[5] < 4 else "?",
        }
    except Exception:
        return None


def get_voting_power(hst: Contract, wallet: str) -> float:
    return hst.functions.getVotes(Web3.to_checksum_address(wallet)).call() / 10**18


def get_token_balance(hst: Contract, wallet: str) -> float:
    return hst.functions.balanceOf(Web3.to_checksum_address(wallet)).call() / 10**18


# ─── Campaign (Nhận xét thầy #2) ─────────────────────────────
def get_campaign_data(gov: Contract, campaign_id: int) -> Optional[dict]:
    """
    Ánh xạ trạng thái campaign sang quy trình nghiệp vụ:
      ACTIVE   → đang nhận phiếu (cổ đông bỏ phiếu)
      COMMIT   → Commit-Reveal: giai đoạn gửi hash kín
      REVEAL   → Commit-Reveal: giai đoạn tiết lộ
      EXECUTED → đã thông qua PASS
      DEFEATED → không đạt
    """
    STATUS = ["DRAFT","ACTIVE","COMMIT","REVEAL","TALLYING","EXECUTED","DEFEATED","CANCELLED","QUEUED","EXECUTABLE"]
    TYPES  = ["Routine","Major","M&A"]
    MECHS  = ["Linear","Quadratic","Equal"]
    try:
        raw  = gov.functions.getCampaign(campaign_id).call()
        data = {
            "id":             raw[0],
            "title":          raw[1],
            "description":    raw[2],
            "proposer":       raw[3],
            "proposalType":   TYPES[raw[4]] if raw[4] < len(TYPES) else "?",
            "proposalTypeInt":raw[4],
            "mechanism":      MECHS[raw[5]] if raw[5] < len(MECHS) else "?",
            "mechanismInt":   raw[5],
            "status":         STATUS[raw[6]] if raw[6] < len(STATUS) else "UNKNOWN",
            "statusInt":      raw[6],
            "createdAt":      raw[7],
            "snapshotBlock":  raw[8],
            "votingStart":    raw[9],
            "votingDeadline": raw[10],
            "commitDeadline": raw[11],
            "revealStart":    raw[12],
            "revealDeadline": raw[13],
            "isCommitReveal": raw[14],
            "forVotes":       raw[15] / 10**18,
            "againstVotes":   raw[16] / 10**18,
            "abstainVotes":   raw[17] / 10**18,
            "passThreshold":  raw[18] / 100,
            "quorumBps":      raw[19] / 100,
        }
        decisive = data["forVotes"] + data["againstVotes"]
        data["forPct"] = round(data["forVotes"] / decisive * 100, 2) if decisive > 0 else 0
        return data
    except Exception:
        return None


def get_all_campaigns(gov: Contract) -> list[dict]:
    try:
        counter = gov.functions.campaignCounter().call()
    except Exception:
        return []
    return [c for i in range(1, counter + 1) if (c := get_campaign_data(gov, i))]


def get_vote_participation(gov: Contract, hst: Contract, campaign_id: int) -> dict:
    """
    Tính tỷ lệ tham gia dựa trên totalSupply tại snapshotBlock (ON-CHAIN, chính xác).
    Tránh bị ảnh hưởng bởi mint/burn sau snapshot.
    """
    try:
        c = get_campaign_data(gov, campaign_id)
        if not c:
            return {}
        total_supply_wei = hst.functions.getPastTotalSupply(c["snapshotBlock"]).call()
        total_supply     = total_supply_wei / 10**18
        total_voted      = c["forVotes"] + c["againstVotes"] + c["abstainVotes"]
        decisive         = c["forVotes"] + c["againstVotes"]
        return {
            "forVotes":         c["forVotes"],
            "againstVotes":     c["againstVotes"],
            "abstainVotes":     c["abstainVotes"],
            "totalVoted":       total_voted,
            "totalSupply":      total_supply,
            "snapshotBlock":    c["snapshotBlock"],
            "participationPct": round(total_voted / total_supply * 100, 2) if total_supply > 0 else 0,
            "forPct":           round(c["forVotes"] / decisive * 100, 2) if decisive > 0 else 0,
            "againstPct":       round(c["againstVotes"] / decisive * 100, 2) if decisive > 0 else 0,
            "quorumMet":        (total_voted / total_supply * 100 >= c["quorumBps"]) if total_supply > 0 else False,
        }
    except Exception:
        return {}


# ─── Certificate (Nhận xét thầy #3) ──────────────────────────
def get_certificate(cert_contract, campaign_id: int) -> Optional[dict]:
    """
    Đọc biên bản chữ ký số từ VotingCertificate contract (ON-CHAIN).
    Biên bản này được tạo tự động sau finalizeCampaign().
    certificateHash dùng để verify tính toàn vẹn.
    """
    if cert_contract is None:
        return None
    try:
        if not cert_contract.functions.hasCertificate(campaign_id).call():
            return None
        raw = cert_contract.functions.getCertificate(campaign_id).call()
        TYPE_L = ["Routine (Thường lệ)", "Major (Quan trọng)", "M&A (Sáp nhập)"]
        MECH_L = ["Linear (Tuyến tính)", "Quadratic (Căn bậc 2)", "Equal (Đồng đều)"]
        return {
            "campaignId":        raw[0],
            "campaignTitle":     raw[1],
            "passed":            raw[2],
            "forVotes":          raw[3] / 10**18,
            "againstVotes":      raw[4] / 10**18,
            "abstainVotes":      raw[5] / 10**18,
            "totalParticipants": raw[6],
            "quorumPct":         raw[7] / 100,
            "participationPct":  raw[8] / 100,
            "passThreshold":     raw[9] / 100,
            "forPct":            raw[10] / 100,
            "proposalType":      TYPE_L[raw[11]] if raw[11] < 3 else "?",
            "mechanism":         MECH_L[raw[12]] if raw[12] < 3 else "?",
            "finalizedBy":       raw[13],
            "finalizedAt":       raw[14],
            "snapshotBlock":     raw[15],
            "certificateHash":   "0x" + raw[16].hex(),
            "result":            "✅ THÔNG QUA (PASS)" if raw[2] else "❌ KHÔNG ĐẠT (DEFEAT)",
        }
    except Exception:
        return None


def verify_certificate(cert_contract, campaign_id: int) -> dict:
    """
    Xác minh hash biên bản trên blockchain.
    Nếu isValid=True → dữ liệu biên bản chưa bị sửa.
    """
    if cert_contract is None:
        return {"isValid": False, "message": "VotingCertificate chưa deploy"}
    try:
        r = cert_contract.functions.verifyCertificate(campaign_id).call()
        return {
            "isValid":      r[0],
            "storedHash":   "0x" + r[1].hex(),
            "computedHash": "0x" + r[2].hex(),
            "message": "✅ Biên bản hợp lệ" if r[0] else "❌ Hash không khớp!",
        }
    except Exception as e:
        return {"isValid": False, "message": f"Lỗi: {e}"}


def get_all_certificates(cert_contract) -> list[dict]:
    if cert_contract is None:
        return []
    try:
        ids = cert_contract.functions.getAllCertifiedCampaigns().call()
        return [c for cid in ids if (c := get_certificate(cert_contract, cid))]
    except Exception:
        return []


# ─── Build transaction ────────────────────────────────────────
def build_tx(w3: Web3, fn_call, sender: str, private_key: str) -> dict:
    """
    Ký (OFF-CHAIN) và gửi transaction (ON-CHAIN).
    Private key chỉ dùng để ký, không lưu trữ.
    """
    try:
        sender = Web3.to_checksum_address(sender)
        tx     = fn_call.build_transaction({
            "from":  sender,
            "nonce": w3.eth.get_transaction_count(sender),
            "gas":   3_000_000,
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


if __name__ == "__main__":
    try:
        w3    = connect_web3()
        addrs = load_addresses()
        print(f"✅ Connected | Block: {w3.eth.block_number} | ChainID: {w3.eth.chain_id}")
        print(f"   HSTToken          : {addrs['hstToken']}")
        print(f"   Registry          : {addrs['registry']}")
        print(f"   Governance        : {addrs['governance']}")
        print(f"   VotingCertificate : {addrs.get('votingCertificate','Chưa deploy')}")
    except Exception as e:
        print(f"⚠️  {e}")


# ─── KYC / IdentityVerifier (Feature 2) ──────────────────────
def get_identity_verifier(w3, addrs: dict):
    """Load IdentityVerifier contract nếu đã deploy."""
    if not addrs.get("identityVerifier"):
        return None
    try:
        return get_contract(w3, "IdentityVerifier", addrs["identityVerifier"])
    except Exception:
        return None


def get_kyc_status(id_verifier, wallet: str) -> dict:
    """
    Lấy trạng thái KYC của một ví — ON-CHAIN.

    Returns:
        {
            "isVerified": bool,
            "isExpired":  bool,
            "isRevoked":  bool,
            "level":      int,   0=NONE 1=BASIC 2=STANDARD 3=FULL
            "levelLabel": str,
            "expiresAt":  int,   Unix timestamp
            "daysLeft":   int,
            "identityHash": str,
            "canVoteKYC": bool,  True nếu KYC còn hạn và chưa bị revoke
        }
    """
    LEVEL_LABEL = {0: "NONE", 1: "BASIC", 2: "STANDARD", 3: "FULL"}
    if id_verifier is None:
        return {"error": "IdentityVerifier not deployed", "canVoteKYC": True}
    try:
        wallet  = Web3.to_checksum_address(wallet)
        status  = id_verifier.functions.getKYCStatus(wallet).call()
        record  = id_verifier.functions.getKYCRecord(wallet).call()
        id_hash = "0x" + record[1].hex() if record[1] != b'\x00'*32 else None

        is_verified, is_expired, is_revoked, level, expires_at, days_left = status
        return {
            "isVerified":   is_verified,
            "isExpired":    is_expired,
            "isRevoked":    is_revoked,
            "level":        level,
            "levelLabel":   LEVEL_LABEL.get(level, "?"),
            "expiresAt":    expires_at,
            "daysLeft":     days_left,
            "identityHash": id_hash,
            "country":      record[8] if len(record) > 8 else "N/A",
            "canVoteKYC":   is_verified and not is_expired and not is_revoked,
        }
    except Exception as e:
        return {"error": str(e), "canVoteKYC": False}


def check_can_vote_full(contracts: dict, wallet: str) -> dict:
    """
    Kiểm tra toàn diện tư cách bỏ phiếu:
      [1] Đăng ký trong Registry (isActive, lockUntil)
      [2] Có token HST
      [3] Đã delegate (có voting power)
      [4] KYC hợp lệ (nếu requireKYC=true)

    Returns dict với từng điều kiện và hint sửa lỗi.
    """
    result = {
        "canVote":       False,
        "inRegistry":    False,
        "hasToken":      False,
        "hasDelegated":  False,
        "kycValid":      True,   # Default True — nếu không có KYC requirement
        "issues":        [],
        "hints":         [],
    }
    try:
        wallet_cs = Web3.to_checksum_address(wallet)
        hst      = contracts.get("hst")
        registry = contracts.get("registry")
        cert     = contracts.get("cert")
        id_ver   = contracts.get("id_verifier")

        # [1] Registry
        if registry:
            info = get_shareholder_info(registry, wallet_cs)
            if info and info.get("isActive"):
                result["inRegistry"] = True
            else:
                result["issues"].append("Chưa đăng ký trong ShareholderRegistry")
                result["hints"].append("Liên hệ Admin để được thêm vào danh sách cổ đông")

        # [2] Token
        if hst:
            bal = get_token_balance(hst, wallet_cs)
            if bal > 0:
                result["hasToken"] = True
            else:
                result["issues"].append("Số dư HST = 0")
                result["hints"].append("Cần có HST token để bỏ phiếu")

        # [3] Delegation
        if hst:
            ds = get_delegation_status(hst, wallet_cs)
            if ds.get("isDelegated"):
                result["hasDelegated"] = True
            else:
                result["issues"].append("Chưa activate voting power")
                result["hints"].append("Gọi delegate(địa_chỉ_của_bạn) trong tab Cổ đông")

        # [4] KYC (nếu có IdentityVerifier)
        if id_ver:
            kyc = get_kyc_status(id_ver, wallet_cs)
            if not kyc.get("canVoteKYC", True):
                result["kycValid"] = False
                if kyc.get("isRevoked"):
                    result["issues"].append("KYC đã bị thu hồi")
                    result["hints"].append("Liên hệ Admin để xác minh lại danh tính")
                elif kyc.get("isExpired"):
                    result["issues"].append("KYC đã hết hạn")
                    result["hints"].append("Gia hạn KYC trong tab 🪪 KYC")
                else:
                    result["issues"].append("Chưa có KYC")
                    result["hints"].append("Đăng ký KYC trong tab 🪪 KYC")

        result["canVote"] = (
            result["inRegistry"] and
            result["hasToken"]   and
            result["hasDelegated"] and
            result["kycValid"]
        )

    except Exception as e:
        result["issues"].append(f"Lỗi kiểm tra: {e}")

    return result
