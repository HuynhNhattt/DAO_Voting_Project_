"""
dashboard/app.py  — v3.0.0
═══════════════════════════════════════════════════════════════════
DAO Voting System — Hệ thống Biểu quyết Cổ đông Blockchain
• Đăng nhập bằng địa chỉ ví + private key (Ganache demo)
• Kiểm tra đủ điều kiện qua ShareholderRegistry.canVote()
• Bỏ phiếu kín: castVote() on-chain (standard) hoặc
  commitVote() → revealVote() (commit-reveal)
• Kết quả cập nhật thực từ blockchain, danh tính người vote ẩn
• Tuân thủ: mỗi ví chỉ vote 1 lần, revert nếu vi phạm
Chạy: streamlit run dashboard/app.py --server.fileWatcherType none
═══════════════════════════════════════════════════════════════════
"""
import os, sys, json, math, time, hashlib, secrets
os.environ["PYTHONUTF8"] = "1"

import streamlit as st
from datetime import datetime
from pathlib import Path

# ─── Page config (PHẢI là lệnh đầu tiên) ────────────────────────────────────
st.set_page_config(
    page_title="DAO Voting System",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Web3 import ─────────────────────────────────────────────────────────────
_root = Path(__file__).parent
for _c in [_root / "utils", _root.parent / "utils", _root]:
    if (_c / "web3_helpers.py").exists():
        sys.path.insert(0, str(_c)); break

WEB3_AVAILABLE = False
try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    from eth_account import Account
    from web3_helpers import (
        connect_web3, get_all_contracts,
        get_shareholder_info, get_voting_power, get_token_balance,
        get_all_campaigns, get_campaign_data, load_addresses,
    )
    WEB3_AVAILABLE = True
except ImportError as _e:
    _WEB3_ERR = str(_e)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS — Dark blockchain aesthetic
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;700;800&display=swap');

*, body { font-family: 'Syne', sans-serif; }
code, .mono { font-family: 'JetBrains Mono', monospace !important; }

[data-testid="stAppViewContainer"] { background: #080c14; }
[data-testid="stSidebar"] {
    background: #0c1220 !important;
    border-right: 1px solid #1a2744;
}
[data-testid="stMain"] { background: #080c14; }

/* Inputs */
input, textarea, select,
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] select { 
    background: #0d1626 !important; 
    border: 1px solid #1e3560 !important; 
    color: #c8d8f0 !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus { border-color: #3a7aff !important; box-shadow: 0 0 0 2px #3a7aff33 !important; }

/* Password field special */
[data-testid="stTextInput"][aria-label*="key"] input,
[data-testid="stTextInput"][aria-label*="Key"] input { color: #3aff8a !important; }

/* Buttons */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #1a3a7a, #0d2655) !important;
    color: #7ab4ff !important;
    border: 1px solid #2a4a8a !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #2a4a9a, #1a3a7a) !important;
    border-color: #3a6afa !important;
    color: #aad4ff !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px #1a4aff22 !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #1a6aff, #0a4acc) !important;
    color: white !important;
    border-color: #3a8aff !important;
}

/* Cards */
.dao-card {
    background: linear-gradient(135deg, #0d1626 0%, #111d36 100%);
    border: 1px solid #1e3560;
    border-radius: 14px;
    padding: 22px;
    margin: 8px 0;
    transition: border-color 0.2s;
}
.dao-card:hover { border-color: #2a5aaa; }

/* Wallet panel */
.wallet-panel {
    background: linear-gradient(135deg, #0a1a10, #0d2210);
    border: 1px solid #1a5a2a;
    border-radius: 14px;
    padding: 20px;
    margin: 8px 0;
}
.wallet-addr {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #3aff8a;
    word-break: break-all;
    background: #0a1808;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid #1a4a20;
    margin: 6px 0;
}

/* Badge không xuống dòng */
.badge { padding: 3px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-block; white-space: nowrap; flex-shrink: 0; }
.badge-active   { background:#0a3020; color:#3aff6a; border:1px solid #3aff6a; }
.badge-commit   { background:#1a2040; color:#7aafff; border:1px solid #7aafff; }
.badge-reveal   { background:#201a40; color:#aa7aff; border:1px solid #aa7aff; }
.badge-executed { background:#0a1a3a; color:#3a8aff; border:1px solid #3a8aff; }
.badge-defeated { background:#2a0a0a; color:#ff4a4a; border:1px solid #ff4a4a; }
.badge-other    { background:#1a1a2a; color:#8899aa; border:1px solid #445566; }

/* Card title+badge row */
.card-title-row { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:8px; }
.card-title-row b { color:#eef; flex:1; min-width:0; word-break:break-word; }

/* Vote bar */
.vbar { background:#0d1626; border-radius:8px; height:20px; overflow:hidden; display:flex; margin: 6px 0; }
.vbar-for  { background:linear-gradient(90deg,#0d5a2a,#2adc6a); height:100%; display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff; }
.vbar-ag   { background:linear-gradient(90deg,#5a0d0d,#dc2a2a); height:100%; display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff; }
.vbar-abs  { background:#1a1d2a; height:100%; }

/* Alerts */
.alert-ok   { background:#0a2a18; border:1px solid #2adc6a; border-radius:10px; padding:14px 18px; color:#4dfca4; font-size:13px; margin: 8px 0; }
.alert-warn { background:#2a200a; border:1px solid #dcaa2a; border-radius:10px; padding:14px 18px; color:#fcd06a; font-size:13px; margin: 8px 0; }
.alert-err  { background:#2a0a0a; border:1px solid #dc2a2a; border-radius:10px; padding:14px 18px; color:#fc6a6a; font-size:13px; margin: 8px 0; }
.alert-info { background:#0a1a3a; border:1px solid #2a6adc; border-radius:10px; padding:14px 18px; color:#6aaafc; font-size:13px; margin: 8px 0; }

/* Section headers */
.sec-hdr { font-size:17px; font-weight:700; color:#5a9aff; border-bottom:1px solid #1a3060; padding-bottom:8px; margin:20px 0 14px 0; font-family:'Syne',sans-serif; }

/* Tier chip */
.tier3 { color:#ffd700; } .tier2 { color:#c0c0c0; } .tier1 { color:#cd7f32; } .tier0 { color:#8899bb; }

/* Scrollbar */
::-webkit-scrollbar { width:8px; } 
::-webkit-scrollbar-track { background:#0d1626; }
::-webkit-scrollbar-thumb { background:#2a3a5e; border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background:#3a5aaa; }

/* Radio clean — chữ trắng dễ đọc */
[data-testid="stRadio"] label { color:#ffffff !important; font-family:'Syne',sans-serif !important; font-size:14px !important; }
[data-testid="stRadio"] label:hover { color:#7ab4ff !important; }
[data-testid="stRadio"] label p { color:#ffffff !important; }

/* Scrollbar */
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
_defaults = {
    "w3": None,
    "contracts": None,
    "conn_checked": False,
    "conn_error": None,
    # Wallet session
    "wallet_addr": None,       # địa chỉ ví đã đăng nhập (checksum)
    "wallet_name": None,       # tên cổ đông (nếu tìm thấy trong registry)
    "wallet_info": None,       # dict shareholder info on-chain
    "wallet_vp": 0.0,          # voting power
    "wallet_balance": 0.0,     # HST balance
    "can_vote": False,         # registry.canVote()
    "private_key": None,       # private key (chỉ lưu in-memory, không persist)
    # UI
    "live_shareholders": None,
    "live_campaigns": None,
    "page": "🏠 Tổng quan",
    "selected_campaign_id": None,
    # Vote tracking (client-side cache — không phải nguồn sự thật)
    "my_votes": {},            # {campaign_id: "FOR"/"AGAINST"/"ABSTAIN"/"COMMITTED"}
    # commit_salt → key: {wallet}_{campaign_id} trong session_state
    "commit_store": {},        # {"{wallet}_{cid}": {"salt": ..., "option": ...}}
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def fmt_num(n): return f"{int(n):,}".replace(",", ".")
def fmt_hst(n): return f"{fmt_num(n)} HST"
def short_addr(a): return a[:8] + "…" + a[-6:] if a and len(a) > 14 else (a or "")

def tier_label(t):
    return {3:"🥇 Sáng lập", 2:"🥈 Chiến lược", 1:"🥉 Tổ chức", 0:"🔵 Nhỏ lẻ"}.get(t, "?")

def tier_color(t):
    return {3:"#ffd700", 2:"#c0c0c0", 1:"#cd7f32", 0:"#8899bb"}.get(t, "#aaa")

def status_badge(s):
    m = {
        "ACTIVE":   ("badge-active", "● ACTIVE"),
        "COMMIT":   ("badge-commit", "🔒 COMMIT"),
        "REVEAL":   ("badge-reveal", "👁 REVEAL"),
        "EXECUTED": ("badge-executed", "✓ EXECUTED"),
        "DEFEATED": ("badge-defeated", "✗ DEFEATED"),
    }
    cls, label = m.get(s, ("badge-other", s))
    return f'<span class="badge {cls}">{label}</span>'


def vote_bar(fv, av, absv):
    total = fv + av + absv
    if total == 0:
        return '<div class="vbar"><div style="width:100%;background:#1a2030;height:100%"></div></div>'
    fp = fv/total*100; ap = av/total*100
    return (f'<div class="vbar">'
            f'<div class="vbar-for" style="width:{fp:.1f}%">{fp:.0f}%</div>'
            f'<div class="vbar-ag"  style="width:{ap:.1f}%">{ap:.0f}%</div>'
            f'<div class="vbar-abs" style="width:{100-fp-ap:.1f}%"></div>'
            f'</div>')

def is_connected():
    w3 = st.session_state.get("w3")
    if w3 is None: return False
    try:
        _ = w3.eth.block_number
        return True
    except Exception:
        st.session_state.update({"w3": None, "contracts": None, "conn_checked": False})
        return False

def do_connect(rpc_url: str):
    if not WEB3_AVAILABLE:
        st.session_state["conn_error"] = "Chưa cài web3: pip install -r requirements.txt"
        return False
    try:
        w3 = connect_web3(rpc_url)
        contracts = get_all_contracts(w3)
        st.session_state.update({"w3": w3, "contracts": contracts, "conn_error": None, "conn_checked": True})
        _refresh_live_data()
        return True
    except FileNotFoundError:
        st.session_state.update({"conn_error": "Chưa deploy contract. Chạy setup_demo.js", "conn_checked": True})
    except Exception as e:
        st.session_state.update({"conn_error": str(e)[:100], "conn_checked": True})
    st.session_state["w3"] = None
    return False

def _refresh_live_data():
    contracts = st.session_state.get("contracts")
    if not contracts: return
    try:
        addrs = load_addresses()
        sh_list = []
        for sh in addrs.get("shareholders", []):
            wallet = sh["address"]
            try:
                bal = get_token_balance(contracts["hst"], wallet)
                vp  = get_voting_power(contracts["hst"], wallet)
                info = get_shareholder_info(contracts["registry"], wallet)
                is_active = info["isActive"] if info else False
                # Bỏ qua ví không đăng ký (accounts[9] nhận token tạm, không phải cổ đông)
                if not is_active and info is None:
                    continue
                sh_list.append({
                    "name": sh["name"], "address": wallet,
                    "hst": bal, "vp": vp,
                    "tier": info["tier"] if info else sh.get("tier", 0),
                    "active": is_active,
                })
            except Exception:
                sh_list.append({"name": sh["name"], "address": wallet,
                                 "hst": float(sh.get("hst", 0)), "vp": 0,
                                 "tier": sh.get("tier", 0), "active": False})
        st.session_state["live_shareholders"] = sh_list
    except Exception:
        st.session_state["live_shareholders"] = None
    try:
        camps = get_all_campaigns(contracts["gov"])
        st.session_state["live_campaigns"] = camps
    except Exception:
        st.session_state["live_campaigns"] = None

def get_shareholders():
    if is_connected():
        live = st.session_state.get("live_shareholders")
        if live is not None: return live, True
    return DEMO_SHAREHOLDERS, False

def get_campaigns():
    if is_connected():
        live = st.session_state.get("live_campaigns")
        if live is not None: return live, True
    return DEMO_CAMPAIGNS, False

def get_total_supply():
    if is_connected():
        try:
            return st.session_state["contracts"]["hst"].functions.totalSupply().call() / 10**18
        except Exception: pass
    return 10_000_000.0

# ─── Wallet Login ─────────────────────────────────────────────────────────────
def do_wallet_login(addr_input: str, pk_input: str):
    """
    Đăng nhập ví:
    1. Validate định dạng địa chỉ
    2. Nếu có private key → verify khớp với địa chỉ
    3. Kiểm tra registry.canVote() on-chain
    4. Lưu vào session
    """
    # Validate địa chỉ
    try:
        addr = Web3.to_checksum_address(addr_input.strip())
    except Exception:
        return False, "❌ Địa chỉ ví không hợp lệ (phải bắt đầu bằng 0x, 42 ký tự)"

    # Nếu nhập private key → verify
    if pk_input.strip():
        try:
            pk = pk_input.strip()
            if not pk.startswith("0x"): pk = "0x" + pk
            derived = Account.from_key(pk).address
            if derived.lower() != addr.lower():
                return False, "❌ Private key không khớp với địa chỉ ví. Kiểm tra lại."
            st.session_state["private_key"] = pk
        except Exception as e:
            return False, f"❌ Private key không hợp lệ: {str(e)[:60]}"
    else:
        st.session_state["private_key"] = None

    # Kiểm tra on-chain nếu kết nối
    if is_connected():
        contracts = st.session_state["contracts"]

        bal = get_token_balance(contracts["hst"], addr)
        vp  = get_voting_power(contracts["hst"], addr)

        if bal == 0:
            return False, "❌ Ví không có HST token. Chỉ cổ đông có token mới được đăng nhập."

        # Thử lấy thông tin registry (có thể None nếu accounts[0] chưa addShareholder)
        info = get_shareholder_info(contracts["registry"], addr)

        # Kiểm tra isActive chỉ khi đã đăng ký — cảnh báo thay vì chặn
        if info and not info.get("isActive", True):
            # Vẫn cho đăng nhập nhưng cảnh báo không thể vote
            pass

        # canVote — nếu không có trong registry thì False nhưng vẫn cho đăng nhập
        try:
            can = contracts["registry"].functions.canVote(addr).call()
        except Exception:
            can = False

        # Tìm tên trong danh sách contract_addresses.json
        name = addr
        try:
            addrs_json = load_addresses()
            for sh in addrs_json.get("shareholders", []):
                if sh["address"].lower() == addr.lower():
                    name = sh["name"]; break
        except Exception: pass

        # Xóa toàn bộ salt_draft_* của tài khoản cũ
        for k in list(st.session_state.keys()):
            if k.startswith("salt_draft_"):
                del st.session_state[k]

        st.session_state.update({
            "wallet_addr":    addr,
            "wallet_name":    name,
            "wallet_info":    info,
            "wallet_vp":      vp,
            "wallet_balance": bal,
            "can_vote":       can,
            "my_votes":       {},      # reset vote cache khi đổi tài khoản
            "commit_store":   {},      # reset commit store khi đổi tài khoản
        })

        if not can:
            if info and not info.get("isActive", True):
                note = "Tài khoản bị vô hiệu hóa trong Registry (isActive=false) — chạy lại setup_demo.js để fix"
            elif info is None:
                note = "Chưa đăng ký trong Registry — chạy lại setup_demo.js"
            else:
                note = "Chưa self-delegate hoặc VP = 0"
            return True, f"⚠️ Đăng nhập thành công nhưng CHƯA ĐỦ điều kiện biểu quyết ({note})."
        return True, f"✅ Đăng nhập thành công! Chào {name}. Voting power: {fmt_hst(vp)}"
    else:
        # Offline mode — chỉ validate địa chỉ
        st.session_state.update({
            "wallet_addr": addr,
            "wallet_name": short_addr(addr),
            "wallet_info": None,
            "wallet_vp": 0.0,
            "wallet_balance": 0.0,
            "can_vote": False,
        })
        return True, "⚠️ Đã ghi nhận địa chỉ nhưng chưa kết nối Ganache — không thể xác minh eligibility."

def do_wallet_logout():
    for k in ["wallet_addr","wallet_name","wallet_info","wallet_vp","wallet_balance",
              "can_vote","private_key","my_votes"]:
        st.session_state[k] = _defaults.get(k)
    st.session_state["commit_store"] = {}
    for k in list(st.session_state.keys()):
        if k.startswith("salt_draft_"):
            del st.session_state[k]

def _commit_key(campaign_id):
    """Key lưu commit theo ví + chiến dịch."""
    addr = st.session_state.get("wallet_addr") or "anon"
    return f"{addr}_{campaign_id}"

def save_commit(campaign_id, option_idx, salt_hex):
    """Lưu commit salt+option vào session (persist qua rerun)."""
    if "commit_store" not in st.session_state:
        st.session_state["commit_store"] = {}
    st.session_state["commit_store"][_commit_key(campaign_id)] = {
        "salt": salt_hex, "option": option_idx
    }

def load_commit(campaign_id):
    """Đọc commit đã lưu. Returns (salt, option) hoặc (None, 0)."""
    store = st.session_state.get("commit_store", {})
    entry = store.get(_commit_key(campaign_id), {})
    return entry.get("salt"), entry.get("option", 0)

# ─── On-chain Voting ──────────────────────────────────────────────────────────
def evm_time_jump(w3, seconds: int) -> tuple:
    """Nháº£y thá»i gian Ganache báº±ng evm_increaseTime + evm_mine."""
    try:
        w3.provider.make_request("evm_increaseTime", [int(seconds)])
        w3.provider.make_request("evm_mine", [])
        block_ts = w3.eth.get_block("latest")["timestamp"]
        return True, f"✅ Đã nhảy {seconds}s | block.timestamp={block_ts}"
    except Exception as e:
        return False, f"evm_increaseTime thất bại: {str(e)[:80]}"

def build_tx(func, from_addr: str, w3) -> dict:
    """Xây transaction dict cơ bản."""
    gas = func.estimate_gas({"from": from_addr})
    return func.build_transaction({
        "from": from_addr,
        "gas": int(gas * 1.2),
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(from_addr),
    })

def send_signed_tx(tx: dict, private_key: str, w3: Web3):
    """Ký và gửi transaction, trả về receipt."""
    signed = Account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

def cast_vote_onchain(campaign_id: int, option_idx: int) -> tuple[bool, str]:
    """
    Gọi GovernanceContract.castVote(campaignId, option).
    option: 0=FOR, 1=AGAINST, 2=ABSTAIN
    Trả về (success, message).
    """
    if not is_connected():
        return False, "Chưa kết nối Ganache"
    pk = st.session_state.get("private_key")
    if not pk:
        return False, "Cần nhập Private Key để ký transaction"
    addr = st.session_state["wallet_addr"]
    contracts = st.session_state["contracts"]
    w3 = st.session_state["w3"]

    # Kiểm tra lại trước khi gửi
    try:
        already = contracts["gov"].functions.hasVoted(campaign_id, addr).call()
        if already:
            return False, "Bạn đã bỏ phiếu cho chiến dịch này rồi (on-chain)"
        can = contracts["registry"].functions.canVote(addr).call()
        if not can:
            return False, "Ví không đủ điều kiện biểu quyết (canVote = false)"
    except Exception as e:
        return False, f"Lỗi kiểm tra điều kiện: {e}"

    try:
        func = contracts["gov"].functions.castVote(campaign_id, option_idx)
        tx = build_tx(func, addr, w3)
        receipt = send_signed_tx(tx, pk, w3)
        if receipt["status"] == 1:
            labels = ["FOR", "AGAINST", "ABSTAIN"]
            st.session_state["my_votes"][campaign_id] = labels[option_idx]
            return True, f"✅ Phiếu bầu ghi nhận trên blockchain! Tx: {receipt['transactionHash'].hex()[:20]}…"
        else:
            return False, "Transaction bị revert (status=0)"
    except Exception as e:
        msg = str(e)
        if "already voted" in msg.lower():
            return False, "Bạn đã bỏ phiếu cho chiến dịch này rồi"
        if "not eligible" in msg.lower() or "not active" in msg.lower():
            return False, "Ví không đủ điều kiện biểu quyết"
        if "voting ended" in msg.lower():
            return False, "Thời gian biểu quyết đã kết thúc"
        return False, f"Lỗi: {msg[:120]}"

def commit_vote_onchain(campaign_id: int, option_idx: int, salt_hex: str) -> tuple[bool, str]:
    """Phase 1 Commit-Reveal: gửi hash lên chain."""
    if not is_connected(): return False, "Chưa kết nối Ganache"
    pk = st.session_state.get("private_key")
    if not pk: return False, "Cần Private Key để ký"
    addr = st.session_state["wallet_addr"]
    contracts = st.session_state["contracts"]
    w3 = st.session_state["w3"]

    try:
        # hash = keccak256(abi.encodePacked(uint8(option), salt, msg.sender))
        salt_bytes = bytes.fromhex(salt_hex.replace("0x", ""))
        vote_hash = w3.keccak(
            b"".join([
                option_idx.to_bytes(1, "big"),
                salt_bytes,
                bytes.fromhex(addr.replace("0x", "")),
            ])
        )
        func = contracts["gov"].functions.commitVote(campaign_id, vote_hash)
        tx = build_tx(func, addr, w3)
        receipt = send_signed_tx(tx, pk, w3)
        if receipt["status"] == 1:
            # Lưu salt + option persist theo wallet+campaign
            save_commit(campaign_id, option_idx, salt_hex)
            st.session_state["my_votes"][campaign_id] = "COMMITTED"
            return True, f"✅ Commit thành công! Tx: {receipt['transactionHash'].hex()[:20]}… — Lưu lại salt để reveal sau!"
        return False, "Transaction revert"
    except Exception as e:
        return False, f"Lỗi: {str(e)[:120]}"

def reveal_vote_onchain(campaign_id: int, option_idx: int, salt_hex: str) -> tuple[bool, str]:
    """Phase 2 Commit-Reveal: reveal phiếu thực tế."""
    if not is_connected(): return False, "Chưa kết nối Ganache"
    pk = st.session_state.get("private_key")
    if not pk: return False, "Cần Private Key để ký"
    addr = st.session_state["wallet_addr"]
    contracts = st.session_state["contracts"]
    w3 = st.session_state["w3"]
    try:
        salt_bytes32 = bytes.fromhex(salt_hex.replace("0x", "")).ljust(32, b"\x00")[:32]
        func = contracts["gov"].functions.revealVote(campaign_id, option_idx, salt_bytes32)
        tx = build_tx(func, addr, w3)
        receipt = send_signed_tx(tx, pk, w3)
        if receipt["status"] == 1:
            labels = ["FOR", "AGAINST", "ABSTAIN"]
            st.session_state["my_votes"][campaign_id] = labels[option_idx]
            return True, f"✅ Reveal thành công! Phiếu {labels[option_idx]} được ghi nhận. Tx: {receipt['transactionHash'].hex()[:20]}…"
        return False, "Transaction revert"
    except Exception as e:
        return False, f"Lỗi: {str(e)[:120]}"

# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-CONNECT
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state["conn_checked"] and WEB3_AVAILABLE:
    do_connect("http://127.0.0.1:7545")
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# DEMO DATA (fallback khi offline)
# ═══════════════════════════════════════════════════════════════════════════════
DEMO_SHAREHOLDERS = [
    {"name":"Chủ tịch HĐQT",      "address":"0x7CdDA1906f74bC60489c88014E59D43c5aE1E090","hst":4_500_000,"vp":4_500_000,"tier":3,"active":True},
    {"name":"Quỹ phát triển",      "address":"0xF154cdf664a7503dc99F583F3938Ae1025DB5700","hst":2_500_000,"vp":2_500_000,"tier":2,"active":True},
    {"name":"Cổ đông A (Tổ chức)","address":"0x925A4276bb6dc38f343986545Ff93173205c51B5","hst":1_500_000,"vp":1_500_000,"tier":1,"active":True},
    {"name":"Cổ đông B (Tổ chức)","address":"0xFd0Cc892A5c8F13f82234f1d19DCA19fe7Dcd59a","hst":1_000_000,"vp":1_000_000,"tier":1,"active":True},
    {"name":"Cổ đông C (Nhỏ lẻ)", "address":"0x78f45F34CdB10fF819C1706228012B50DbD91985","hst":  500_000,"vp":  500_000,"tier":0,"active":True},
]
DEMO_CAMPAIGNS = [
    {"id":1,"title":"Phê duyệt ngân sách R&D 2025","description":"Phân bổ 2 tỷ VNĐ cho R&D Q1-Q2 2025.","proposalType":"Routine","mechanism":"Linear","status":"EXECUTED","forVotes":8_000_000*10**18,"againstVotes":1_500_000*10**18,"abstainVotes":500_000*10**18,"passThreshold":50.0,"quorumBps":10.0,"isCommitReveal":False,"votingDeadline":0},
    {"id":2,"title":"Chia cổ tức 15% năm 2024","description":"Chia cổ tức 15% từ lợi nhuận 2024.","proposalType":"Major","mechanism":"Linear","status":"ACTIVE","forVotes":7_000_000*10**18,"againstVotes":1_000_000*10**18,"abstainVotes":0,"passThreshold":66.0,"quorumBps":20.0,"isCommitReveal":False,"votingDeadline":0},
    {"id":3,"title":"Bầu CEO nhiệm kỳ 2025-2028","description":"Bầu chọn CEO nhiệm kỳ 2025-2028 bằng cơ chế Quadratic.","proposalType":"Major","mechanism":"Quadratic","status":"ACTIVE","forVotes":2_828,"againstVotes":3_805,"abstainVotes":0,"passThreshold":66.0,"quorumBps":20.0,"isCommitReveal":False,"votingDeadline":0},
    {"id":4,"title":"Sáp nhập M&A — TechCorp Ltd","description":"M&A chiến lược, định giá 150 tỷ VNĐ.","proposalType":"M&A","mechanism":"Linear","status":"COMMIT","forVotes":0,"againstVotes":0,"abstainVotes":0,"passThreshold":75.0,"quorumBps":30.0,"isCommitReveal":True,"votingDeadline":0},
]

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏛️ DAO Voting")
    st.markdown("<small style='color:#556'>Blockchain Governance Platform</small>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Navigation ───────────────────────────────────────────────────────────
    page = st.radio(
        "Menu",
        ["🏠 Tổng quan", "🔐 Đăng nhập ví", "🗳️ Bỏ phiếu", "👥 Cổ đông", "📊 Phân tích", "⚙️ Hướng dẫn"],
        index=["🏠 Tổng quan","🔐 Đăng nhập ví","🗳️ Bỏ phiếu","👥 Cổ đông","📊 Phân tích","⚙️ Hướng dẫn"].index(
            st.session_state.get("page","🏠 Tổng quan")
        ),
        label_visibility="collapsed",
    )
    st.session_state["page"] = page

    st.markdown("---")

    # ── Wallet status ────────────────────────────────────────────────────────
    addr = st.session_state.get("wallet_addr")
    if addr:
        can = st.session_state.get("can_vote", False)
        st.markdown(f"""
        <div class="wallet-panel">
        <div style="font-size:12px;color:#3aff8a;font-weight:700;margin-bottom:4px">🔓 ĐÃ ĐĂNG NHẬP</div>
        <div style="font-size:13px;color:#cce;font-weight:600">{st.session_state.get('wallet_name','')}</div>
        <div class="wallet-addr">{short_addr(addr)}</div>
        <div style="font-size:12px;color:#778;margin-top:6px">
          HST: <b style="color:#ffd700">{fmt_hst(st.session_state.get('wallet_balance',0))}</b><br>
          VP:  <b style="color:#4a9eff">{fmt_hst(st.session_state.get('wallet_vp',0))}</b><br>
          Trạng thái: {'<span style="color:#3aff6a">✅ Đủ điều kiện</span>' if can else '<span style="color:#ff8a3a">⚠️ Chưa đủ điều kiện</span>'}
        </div>
        </div>""", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            do_wallet_logout()
            st.rerun()
    else:
        st.markdown("""
        <div style="background:#1a1a2a;border:1px solid #2a2a4a;border-radius:10px;padding:14px;text-align:center;color:#778;font-size:13px">
        🔒 Chưa đăng nhập<br><small>Vào <b>Đăng nhập ví</b> để biểu quyết</small>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Connection ───────────────────────────────────────────────────────────
    st.markdown("<small style='color:#556;font-weight:600'>⚙️ KẾT NỐI GANACHE</small>", unsafe_allow_html=True)
    rpc_url = st.text_input("RPC URL", value="http://127.0.0.1:7545", key="rpc_input", label_visibility="collapsed")

    c1, c2 = st.columns([4, 1])
    with c1:
        if st.button("🔌 Kết nối", use_container_width=True):
            with st.spinner("Đang kết nối..."):
                ok = do_connect(rpc_url)
            if ok:
                st.success("✅ OK")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error(st.session_state.get("conn_error","Lỗi"))
    with c2:
        dot = "#2ddc64" if is_connected() else "#dc6a2d"
        st.markdown(f'<div style="margin-top:8px;text-align:center"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{dot};box-shadow:0 0 6px {dot}"></span></div>', unsafe_allow_html=True)

    if is_connected():
        if st.button("🔄 Refresh", use_container_width=True):
            _refresh_live_data()
            # Cập nhật wallet info nếu đang login
            if st.session_state.get("wallet_addr"):
                contracts = st.session_state["contracts"]
                a = st.session_state["wallet_addr"]
                st.session_state["wallet_balance"] = get_token_balance(contracts["hst"], a)
                st.session_state["wallet_vp"] = get_voting_power(contracts["hst"], a)
                try:
                    st.session_state["can_vote"] = contracts["registry"].functions.canVote(a).call()
                except Exception: pass
            st.rerun()
        try:
            w3 = st.session_state["w3"]
            st.markdown(f'<div style="background:#0a1a0a;border:1px solid #2adc6a;border-radius:8px;padding:8px;font-size:11px;color:#4dfc84;margin-top:6px">✅ Block #{w3.eth.block_number}</div>', unsafe_allow_html=True)
        except Exception: pass
    else:
        err = st.session_state.get("conn_error")
        if err:
            st.markdown(f'<div style="background:#1a1000;border:1px solid #aa7000;border-radius:8px;padding:8px;font-size:11px;color:#ddc060;margin-top:6px">⚠️ Demo mode<br><small>{err[:70]}</small></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<small style='color:#334'>v3.0.0 • Hardhat + Web3.py + Streamlit</small>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Tổng quan
# ═══════════════════════════════════════════════════════════════════════════════
if "🏠 Tổng quan" in page:
    st.markdown("# 🏛️ DAO Voting System")
    st.markdown("**Hệ thống Biểu quyết Cổ đông trên Blockchain — v3.0.0**")

    connected = is_connected()
    if connected:
        try:
            w3 = st.session_state["w3"]
            st.markdown(f'<div class="alert-ok">✅ Kết nối Ganache | Block #{w3.eth.block_number} | ChainID: {w3.eth.chain_id} | Dữ liệu thực on-chain</div>', unsafe_allow_html=True)
        except Exception: pass
    else:
        err = st.session_state.get("conn_error") or "Chưa kết nối Ganache."
        st.markdown(f'<div class="alert-warn">🔌 {err} — Đang hiển thị dữ liệu demo.</div>', unsafe_allow_html=True)

    st.markdown("---")
    shareholders, _ = get_shareholders()
    campaigns, _ = get_campaigns()

    total_hst = sum(s["hst"] for s in shareholders)  # tổng từ cổ đông thực, bỏ accounts tạm
    active_c  = sum(1 for c in campaigns if c["status"] in ("ACTIVE","COMMIT","REVEAL"))
    exec_c    = sum(1 for c in campaigns if c["status"] == "EXECUTED")

    cs = "background:linear-gradient(135deg,#0d1a3a,#111d44);border:1px solid #1e3a6a;border-radius:12px;padding:0 16px;text-align:center;height:100px;display:flex;flex-direction:column;align-items:center;justify-content:center;"
    ls = "font-size:11px;color:#6688aa;text-transform:uppercase;letter-spacing:1px;"
    vs = "font-size:26px;font-weight:800;color:#4a9eff;font-family:'Syne',sans-serif;"

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div style="{cs}"><div style="{ls}">Cổ đông</div><div style="{vs}">{len(shareholders)}</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div style="{cs}"><div style="{ls}">Tổng cung HST</div><div style="{vs}">{total_hst/1e6:.0f}M</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div style="{cs}"><div style="{ls}">Đang mở</div><div style="{vs}">{active_c}</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div style="{cs}"><div style="{ls}">Nghị quyết pass</div><div style="{vs}">{exec_c}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown('<div class="sec-hdr">📋 Chiến dịch đang mở</div>', unsafe_allow_html=True)
        open_camps = [c for c in campaigns if c["status"] in ("ACTIVE","COMMIT","REVEAL")]
        if not open_camps:
            st.info("Không có chiến dịch nào đang mở.")
        for c in open_camps:
            fv, av, absv = c["forVotes"], c["againstVotes"], c["abstainVotes"]
            _badge = status_badge(c["status"])
            st.markdown(
                f'<div class="dao-card">'
                f'<div class="card-title-row">'
                f'<b>#{c["id"]} — {c["title"]}</b>'
                + _badge +
                f'</div><div style="font-size:12px;color:#778;margin-bottom:6px">📌 {c["proposalType"]} | ⚙️ {c["mechanism"]}{"  🔒 Commit-Reveal" if c.get("isCommitReveal") else ""}</div>'
                + vote_bar(fv, av, absv) + "</div>",
                unsafe_allow_html=True
            )
            if st.button(f"Bỏ phiếu →", key=f"go_vote_{c['id']}"):
                st.session_state["selected_campaign_id"] = c["id"]
                st.session_state["page"] = "🗳️ Bỏ phiếu"
                st.rerun()

    with col_r:
        st.markdown('<div class="sec-hdr">👥 Phân bổ Token</div>', unsafe_allow_html=True)
        total_sh = sum(s["hst"] for s in shareholders)
        for s in shareholders:
            pct = s["hst"]/total_sh*100 if total_sh > 0 else 0
            color = tier_color(s["tier"])
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin:5px 0;padding:8px 12px;background:#0d1626;border-radius:8px;border-left:3px solid {color}">
              <div style="flex:1"><div style="color:#ccd;font-size:13px;font-weight:600">{s['name']}</div><div style="color:#556;font-size:11px">{tier_label(s['tier'])}</div></div>
              <div style="text-align:right"><div style="color:{color};font-weight:700;font-size:13px">{pct:.1f}%</div><div style="color:#778;font-size:11px">{fmt_hst(s['hst'])}</div></div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Đăng nhập ví
# ═══════════════════════════════════════════════════════════════════════════════
elif "🔐 Đăng nhập ví" in page:
    st.markdown("# 🔐 Đăng nhập Ví Blockchain")
    st.markdown("Nhập địa chỉ ví và private key để xác thực quyền biểu quyết.")

    # Nếu đã đăng nhập → hiện thông tin
    if st.session_state.get("wallet_addr"):
        addr = st.session_state["wallet_addr"]
        name = st.session_state.get("wallet_name", addr)
        can  = st.session_state.get("can_vote", False)
        info = st.session_state.get("wallet_info")

        st.markdown(f'<div class="alert-ok">✅ Đã đăng nhập: <b>{name}</b> ({short_addr(addr)})</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("💰 Số dư HST", fmt_hst(st.session_state.get("wallet_balance", 0)))
        with col2: st.metric("⚡ Voting Power", fmt_hst(st.session_state.get("wallet_vp", 0)))
        with col3:
            tier_n = info["tier"] if info else 0
            st.metric("🏷️ Tier", tier_label(tier_n))

        if can:
            st.markdown('<div class="alert-ok">✅ Ví đủ điều kiện biểu quyết (canVote = true)</div>', unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-warn">⚠️ Ví chưa đủ điều kiện. Có thể do:
            <ul><li>Chưa self-delegate token (chạy: <code>hst.delegate(yourAddress)</code> qua Hardhat console)</li>
            <li>Tài khoản đang bị khóa (lockUntil chưa hết)</li>
            <li>Chưa kết nối Ganache</li></ul></div>""", unsafe_allow_html=True)

        if info:
            st.markdown('<div class="sec-hdr">📋 Thông tin Cổ đông (on-chain)</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="dao-card">
                <div style="color:#778;font-size:12px;margin-bottom:12px">SHAREHOLDER REGISTRY</div>
                <div style="margin:6px 0"><span style="color:#556">Địa chỉ:</span> <span class="mono" style="color:#3aff8a;font-size:12px">{short_addr(info['wallet'])}</span></div>
                <div style="margin:6px 0"><span style="color:#556">Đăng ký lúc:</span> <span style="color:#ccd">{datetime.fromtimestamp(info['registeredAt']).strftime('%d/%m/%Y %H:%M') if info.get('registeredAt') else 'N/A'}</span></div>
                <div style="margin:6px 0"><span style="color:#556">Tier:</span> <span style="color:{tier_color(info['tier'])};font-weight:700">{tier_label(info['tier'])}</span></div>
                <div style="margin:6px 0"><span style="color:#556">Trạng thái:</span> {'<span style="color:#3aff6a">● Hoạt động</span>' if info['isActive'] else '<span style="color:#ff6a3a">✕ Vô hiệu</span>'}</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                lock = info.get("lockUntil", 0)
                lock_str = datetime.fromtimestamp(lock).strftime('%d/%m/%Y') if lock > 0 else "Không"
                st.markdown(f"""
                <div class="dao-card">
                <div style="color:#778;font-size:12px;margin-bottom:12px">VOTING ELIGIBILITY</div>
                <div style="margin:6px 0"><span style="color:#556">canVote:</span> {'<span style="color:#3aff6a;font-weight:700">✅ TRUE</span>' if can else '<span style="color:#ff6a3a;font-weight:700">❌ FALSE</span>'}</div>
                <div style="margin:6px 0"><span style="color:#556">Khóa đến:</span> <span style="color:#ccd">{lock_str}</span></div>
                <div style="margin:6px 0"><span style="color:#556">Private key:</span> {'<span style="color:#3aff6a">✅ Đã nhập</span>' if st.session_state.get("private_key") else '<span style="color:#aa8822">⚠️ Chưa nhập (chỉ xem)</span>'}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🚪 Đăng xuất", type="primary"):
            do_wallet_logout()
            st.rerun()
    else:
        # ── Form đăng nhập ────────────────────────────────────────────────────
        st.markdown('<div class="dao-card">', unsafe_allow_html=True)
        st.markdown("### Xác thực bằng Ví Ethereum")
        st.markdown("""
        <div class="alert-info">
        ℹ️ <b>Về bảo mật:</b> Private key chỉ được dùng để ký transaction cục bộ và <b>không bao giờ</b> được gửi ra ngoài. 
        Trong môi trường production, nên dùng MetaMask hoặc hardware wallet. Đây là demo trên Ganache nên dùng private key trực tiếp.
        </div>""", unsafe_allow_html=True)

        with st.form("login_form"):
            wallet_addr = st.text_input(
                "🏦 Địa chỉ ví (Ethereum Address)",
                placeholder="",
                help="Địa chỉ ví 42 ký tự bắt đầu bằng 0x"
            )
            private_key = st.text_input(
                "🔑 Private Key",
                placeholder="",
                type="password",
                help="Private key để ký transaction bỏ phiếu. Để trống nếu chỉ muốn xem thông tin."
            )
            submitted = st.form_submit_button("🔐 Đăng nhập", use_container_width=True, type="primary")

        if submitted and wallet_addr:
            with st.spinner("Đang xác minh..."):
                success, msg = do_wallet_login(wallet_addr, private_key)
            if success:
                st.success(msg)
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(msg)

        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Bỏ phiếu
# ═══════════════════════════════════════════════════════════════════════════════
elif "🗳️ Bỏ phiếu" in page:
    st.markdown("# 🗳️ Bỏ phiếu Kín On-chain")

    wallet_addr = st.session_state.get("wallet_addr")

    # ── Kiểm tra đăng nhập ───────────────────────────────────────────────────
    if not wallet_addr:
        st.markdown("""
        <div class="alert-warn">
        🔒 <b>Chưa đăng nhập ví.</b><br>
        Vào trang <b>Đăng nhập ví</b> để xác thực trước khi biểu quyết.
        </div>""", unsafe_allow_html=True)
        if st.button("→ Đến trang Đăng nhập", type="primary"):
            st.session_state["page"] = "🔐 Đăng nhập ví"
            st.rerun()
        st.stop()

    # ── Hiển thị danh sách chiến dịch ────────────────────────────────────────
    campaigns, camp_live = get_campaigns()

    if camp_live:
        st.markdown('<div class="alert-ok">✅ Dữ liệu on-chain từ Ganache</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-warn">⚠️ Demo mode — kết nối Ganache để bỏ phiếu thực</div>', unsafe_allow_html=True)

    if not campaigns:
        st.info("Chưa có chiến dịch nào.")
        st.stop()

    # ── Chọn chiến dịch ──────────────────────────────────────────────────────
    camp_opts = {f"#{c['id']} — {c['title']}": c for c in campaigns}
    preselect_id = st.session_state.get("selected_campaign_id")
    default_key = next((k for k, c in camp_opts.items() if c["id"] == preselect_id), list(camp_opts.keys())[0])
    selected_key = st.selectbox("Chọn chiến dịch", list(camp_opts.keys()), index=list(camp_opts.keys()).index(default_key))
    c = camp_opts[selected_key]
    campaign_id = c["id"]

    st.markdown("---")

    # ── Chi tiết chiến dịch ──────────────────────────────────────────────────
    col_info, col_stat = st.columns([3, 1])
    with col_info:
        st.markdown(f"## #{c['id']} — {c['title']}")
        st.markdown(f"*{c['description']}*")
    with col_stat:
        cr_tag = "<br>🔒 Commit-Reveal" if c.get("isCommitReveal") else ""
        st.markdown(f"""
        <div style="text-align:center;padding:20px;background:#0d1626;border-radius:12px;margin-top:10px">
        {status_badge(c['status'])}
        <div style="margin-top:10px;font-size:12px;color:#778">
        📌 {c['proposalType']}<br>⚙️ {c['mechanism']}{cr_tag}
        </div></div>""", unsafe_allow_html=True)

    # ── Kết quả tổng hợp (ẩn danh) ───────────────────────────────────────────
    mechanism = c.get("mechanism", "Linear")

    # forVotes/againstVotes/abstainVotes là raw uint256 từ contract:
    # Linear   → HST wei (phải chia 10^18)
    # Quadratic→ sqrt(wei), số nhỏ, KHÔNG chia
    # Equal    → số người, KHÔNG chia
    _raw_fv, _raw_av, _raw_absv = c["forVotes"], c["againstVotes"], c["abstainVotes"]
    if mechanism == "Linear":
        fv   = _raw_fv   / 10**18
        av   = _raw_av   / 10**18
        absv = _raw_absv / 10**18
    else:
        fv, av, absv = float(_raw_fv), float(_raw_av), float(_raw_absv)

    total_voted  = fv + av + absv
    total_supply = get_total_supply()

    # Đơn vị hiển thị tuỳ cơ chế
    if mechanism == "Linear":
        def fmt_vote(v): return fmt_hst(v)
        unit_note = "HST"
    elif mechanism == "Quadratic":
        def fmt_vote(v): return f"{int(v):,} wgt".replace(",", ".")
        unit_note = "√HST weight"
    else:  # Equal
        def fmt_vote(v): return f"{int(v)} phiếu"
        unit_note = "phiếu (1 người = 1)"

    # Tham gia: chỉ Linear tính được chính xác từ totalSupply
    # Quadratic/Equal: weight không tương đương HST → không tính % tham gia
    if mechanism == "Linear" and total_supply > 0:
        part = total_voted / total_supply * 100
        part_str = f"{part:.1f}%"
        quorum_ok = part >= c["quorumBps"]
    elif mechanism == "Linear":
        part = 0; part_str = "N/A"; quorum_ok = False
    else:
        # Quadratic/Equal: dùng getParticipationRate on-chain (bps so với totalSupply HST)
        # Chú ý: đây là tỉ lệ weight/supply, không phải % người — chỉ dùng để check quorum
        part = 0; quorum_ok = False
        if is_connected():
            try:
                bps = st.session_state["contracts"]["gov"].functions.getParticipationRate(c["id"]).call()
                part = bps / 100
                quorum_ok = bps >= int(c["quorumBps"] * 100)
            except Exception:
                pass
        part_str = f"~{part:.2f}%" if part > 0 else "N/A"

    st.markdown("---")
    st.markdown('<div class="sec-hdr">📊 Kết quả Tổng hợp (Ẩn danh)</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="alert-info">
    🔒 <b>Bỏ phiếu kín:</b> Tổng số phiếu theo từng lựa chọn được công khai nhưng <b>danh tính người bỏ phiếu không hiển thị</b> trên dashboard.
    Dữ liệu gốc chỉ truy cập được qua smart contract với quyền AUDITOR.<br>
    <small style="color:#4a7aaa">⚙️ Cơ chế: <b>{mechanism}</b> — đơn vị hiển thị: <b>{unit_note}</b></small>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("✅ FOR",     fmt_vote(fv),   f"{fv/total_voted*100:.1f}%" if total_voted > 0 else "0%")
    with col2: st.metric("❌ AGAINST", fmt_vote(av),   f"{av/total_voted*100:.1f}%" if total_voted > 0 else "0%")
    with col3: st.metric("⬜ ABSTAIN", fmt_vote(absv), f"{absv/total_voted*100:.1f}%" if total_voted > 0 else "0%")
    with col4: st.metric("📊 Tham gia", part_str, f"Ngưỡng: {c['quorumBps']:.0f}%")

    st.markdown(vote_bar(fv, av, absv), unsafe_allow_html=True)

    # Kết quả tạm thời
    if total_voted > 0:
        decisive = fv + av
        pass_pct = fv/decisive*100 if decisive > 0 else 0
        pass_ok   = pass_pct > c["passThreshold"]
        if quorum_ok and pass_ok:
            st.markdown(f'<div class="alert-ok">✅ Đang DẪN — FOR: {pass_pct:.1f}% > {c["passThreshold"]:.0f}% | Quorum: {part_str} ≥ {c["quorumBps"]:.0f}%</div>', unsafe_allow_html=True)
        elif not quorum_ok:
            st.markdown(f'<div class="alert-warn">⚠️ Chưa đủ quorum — {part_str} < {c["quorumBps"]:.0f}%</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-err">❌ AGAINST đang thắng — FOR: {pass_pct:.1f}% < {c["passThreshold"]:.0f}%</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Finalize panel ───────────────────────────────────────────────────────
    if c["status"] in ("ACTIVE", "REVEAL") and is_connected():
        deadline = c.get("votingDeadline", 0)
        now = int(time.time())
        deadline_passed = deadline > 0 and now >= deadline

        st.markdown('<div class="sec-hdr">⏱️ Kết thúc biểu quyết</div>', unsafe_allow_html=True)

        if deadline_passed:
            st.markdown('<div class="alert-warn">⏰ Thời gian biểu quyết đã kết thúc — có thể finalize ngay.</div>', unsafe_allow_html=True)
            if st.button("🏁 Finalize Campaign (ghi kết quả lên chain)", type="primary", use_container_width=True, key=f"finalize_{campaign_id}"):
                pk = st.session_state.get("private_key")
                if not pk:
                    st.error("Cần Private Key để ký transaction finalize.")
                else:
                    try:
                        w3_  = st.session_state["w3"]
                        gov_ = st.session_state["contracts"]["gov"]
                        func = gov_.functions.finalizeCampaign(campaign_id)
                        tx   = build_tx(func, st.session_state["wallet_addr"], w3_)
                        receipt = send_signed_tx(tx, pk, w3_)
                        if receipt["status"] == 1:
                            st.success("✅ Finalize thành công! Kết quả đã ghi lên blockchain.")
                            _refresh_live_data()
                            time.sleep(0.5); st.rerun()
                        else:
                            st.error("Transaction revert.")
                    except Exception as e:
                        st.error(f"Lỗi finalize: {str(e)[:120]}")
        else:
            remaining = deadline - now if deadline > 0 else 0
            days  = remaining // 86400
            hours = (remaining % 86400) // 3600
            mins  = (remaining % 3600) // 60
            st.markdown(f'<div class="alert-info">⏳ Còn <b>{days}d {hours}h {mins}m</b> trước khi có thể finalize.</div>', unsafe_allow_html=True)

            with st.expander("⚡ Ganache Demo: Bỏ qua thời gian (evm_increaseTime)"):
                st.warning("⚠️ Chỉ dùng trên Ganache local. KHÔNG dùng trên testnet/mainnet.")
                if st.button("⏩ Nhảy qua votingDeadline", key=f"skip_time_{campaign_id}"):
                    try:
                        w3_ = st.session_state["w3"]
                        jump = remaining + 60
                        w3_.provider.make_request("evm_increaseTime", [jump])
                        w3_.provider.make_request("evm_mine", [])
                        st.success(f"✅ Đã nhảy {jump}s. Bấm Finalize bên dưới.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"evm_increaseTime thất bại: {e}")

    st.markdown("---")

    # ── Panel bỏ phiếu ───────────────────────────────────────────────────────
    can_vote = st.session_state.get("can_vote", False)
    my_vote  = st.session_state.get("my_votes", {}).get(campaign_id)
    has_pk   = bool(st.session_state.get("private_key"))

    st.markdown('<div class="sec-hdr">🗳️ Bỏ phiếu của bạn</div>', unsafe_allow_html=True)

    # Kiểm tra on-chain hasVoted
    already_voted_onchain = False
    already_committed_onchain = False
    if is_connected() and wallet_addr:
        try:
            already_voted_onchain = st.session_state["contracts"]["gov"].functions.hasVoted(campaign_id, wallet_addr).call()
        except Exception: pass
        # Kiểm tra đã commit chưa (cho commit-reveal campaigns)
        if c.get("isCommitReveal") and c["status"] in ("COMMIT", "REVEAL"):
            try:
                commitment = st.session_state["contracts"]["gov"].functions.getCommitment(campaign_id, wallet_addr).call()
                # commitment là bytes32 — nếu khác 0x000...000 thì đã commit
                # Xử lý mọi type: HexBytes (web3.py trả về), bytes, bytearray, int, str
                _cb: bytes
                if isinstance(commitment, int):
                    _cb = commitment.to_bytes(32, "big")
                elif isinstance(commitment, (bytes, bytearray)):
                    # HexBytes kế thừa từ bytes → isinstance sẽ đúng
                    _cb = bytes(commitment)
                elif isinstance(commitment, str):
                    _hex = commitment.replace("0x", "")
                    try:
                        _cb = bytes.fromhex(_hex.zfill(64))
                    except Exception:
                        _cb = b'\x00' * 32
                else:
                    # fallback: thử ép str rồi parse hex
                    try:
                        _cb = bytes.fromhex(str(commitment).replace("0x", "").zfill(64))
                    except Exception:
                        _cb = b'\x00' * 32

                already_committed_onchain = _cb != b'\x00' * 32

                # FIX 2: Sync session dựa trên kết quả on-chain THỰC (không dùng session làm fallback)
                if already_committed_onchain:
                    # Ví này ĐÃ commit on-chain → đánh dấu vào my_votes của ví hiện tại
                    st.session_state.setdefault("my_votes", {})[campaign_id] = "COMMITTED"
                else:
                    # Ví này CHƯA commit on-chain → xóa trạng thái COMMITTED cũ
                    # (quan trọng khi đổi ví: ví mới không thừa hưởng trạng thái của ví cũ)
                    st.session_state.get("my_votes", {}).pop(campaign_id, None)
                    my_vote = None  # cập nhật lại biến local để logic bên dưới đúng
            except Exception:
                # Nếu contract không có hàm getCommitment → KHÔNG dùng session làm nguồn sự thật
                # Để tránh Bug 2: reset về False thay vì fallback sang my_vote
                already_committed_onchain = False

    # Đã bỏ phiếu rồi (standard vote hoặc sau reveal)
    if already_voted_onchain or my_vote in ("FOR","AGAINST","ABSTAIN"):
        vote_display = my_vote or "✅ Đã ghi nhận"
        colors = {"FOR":"#3aff6a","AGAINST":"#ff4a4a","ABSTAIN":"#778"}
        color = colors.get(my_vote, "#4a9eff")
        st.markdown(f"""
        <div class="dao-card" style="text-align:center;padding:30px">
        <div style="font-size:48px;margin-bottom:12px">✅</div>
        <div style="font-size:18px;color:#ccd;font-weight:600;margin-bottom:8px">Bạn đã bỏ phiếu</div>
        <div style="font-size:28px;font-weight:800;color:{color};margin-bottom:8px">{vote_display}</div>
        <div style="font-size:12px;color:#556">Danh tính được bảo mật • Phiếu đã ghi lên blockchain</div>
        </div>""", unsafe_allow_html=True)

    elif already_committed_onchain or my_vote == "COMMITTED":
        st.session_state.setdefault("my_votes", {})[campaign_id] = "COMMITTED"
        st.markdown("""
        <div class="dao-card" style="text-align:center;padding:24px">
        <div style="font-size:48px;margin-bottom:12px">🔒</div>
        <div style="font-size:18px;color:#ccd;font-weight:600;margin-bottom:8px">Đã COMMIT phiếu thành công</div>
        <div style="font-size:13px;color:#778">Commit đã ghi lên blockchain. Chờ giai đoạn REVEAL để công bố phiếu thực tế.</div>
        </div>""", unsafe_allow_html=True)

        # Luôn hiện nút skip/transition sau khi commit (KHÔNG dùng expander, tránh bị ẩn)
        if c["status"] == "COMMIT" and is_connected():
            commit_deadline = c.get("commitDeadline", 0)
            try:
                chain_now_ck = st.session_state["w3"].eth.get_block("latest")["timestamp"]
            except Exception:
                chain_now_ck = int(time.time())
            commit_ended_ck = commit_deadline > 0 and chain_now_ck >= commit_deadline

            if commit_ended_ck:
                st.markdown('<div class="alert-warn">⏰ Commit phase đã kết thúc — bấm nút bên dưới để chuyển sang REVEAL.</div>', unsafe_allow_html=True)
                pk_ck = st.session_state.get("private_key")
                col_ck1, col_ck2 = st.columns([2, 1])
                with col_ck1:
                    if pk_ck and st.button("▶ Chuyển sang REVEAL", type="primary", use_container_width=True, key=f"committed_transition_{campaign_id}"):
                        try:
                            w3_ = st.session_state["w3"]
                            gov_ = st.session_state["contracts"]["gov"]
                            try: w3_.provider.make_request("evm_mine", [])
                            except Exception: pass
                            func = gov_.functions.transitionToReveal(campaign_id)
                            tx = build_tx(func, wallet_addr, w3_)
                            receipt = send_signed_tx(tx, pk_ck, w3_)
                            if receipt["status"] == 1:
                                st.success("✅ Đã chuyển sang REVEAL!")
                                _refresh_live_data(); time.sleep(0.5); st.rerun()
                            else:
                                st.error("Transaction revert.")
                        except Exception as e:
                            st.error(f"Lỗi: {str(e)[:120]}")
                    elif not pk_ck:
                        st.markdown('<div class="alert-warn">⚠️ Cần Private Key (CAMPAIGN_MANAGER_ROLE) để chuyển sang REVEAL.</div>', unsafe_allow_html=True)
                with col_ck2:
                    if st.button("⛏ Mine block", use_container_width=True, key=f"committed_mine_end_{campaign_id}"):
                        try:
                            w3_ = st.session_state["w3"]
                            for _ in range(3): w3_.provider.make_request("evm_mine", [])
                            st.success(f"Block #{w3_.eth.block_number} | ts={w3_.eth.get_block('latest')['timestamp']}")
                            st.rerun()
                        except Exception as ex: st.error(str(ex)[:80])
            else:
                remaining_ck = commit_deadline - chain_now_ck if commit_deadline > 0 else 0
                d_ck = remaining_ck // 86400; h_ck = (remaining_ck % 86400) // 3600; m_ck = (remaining_ck % 3600) // 60
                st.markdown(
                    f'<div class="alert-info">⏳ Commit phase còn <b>{d_ck}d {h_ck}h {m_ck}m</b> — '
                    f'Bạn đã commit xong, chờ hết thời gian rồi chuyển sang REVEAL.</div>',
                    unsafe_allow_html=True
                )
                # Nút skip hiện thẳng, KHÔNG bọc trong expander để không bị mất sau rerun
                st.markdown('<div class="alert-warn">⚡ <b>Ganache Demo</b> — Bỏ qua thời gian chờ:</div>', unsafe_allow_html=True)
                col_sk1, col_sk2 = st.columns([2, 1])
                with col_sk1:
                    if st.button("⏩ Nhảy qua commitDeadline", key=f"committed_skip_{campaign_id}", use_container_width=True):
                        w3_ = st.session_state["w3"]
                        ok_j, msg_j = evm_time_jump(w3_, remaining_ck + 60)
                        if ok_j:
                            st.success(msg_j + " — Bấm Mine block rồi bấm Chuyển sang REVEAL.")
                            st.rerun()
                        else:
                            st.error(msg_j)
                with col_sk2:
                    if st.button("⛏ Mine block", use_container_width=True, key=f"committed_mine_skip_{campaign_id}"):
                        try:
                            w3_ = st.session_state["w3"]
                            for _ in range(3): w3_.provider.make_request("evm_mine", [])
                            st.success(f"Block #{w3_.eth.block_number} | ts={w3_.eth.get_block('latest')['timestamp']}")
                            st.rerun()
                        except Exception as ex:
                            st.error(str(ex)[:80])

        # FIX Bug 1: khi status == REVEAL trong block "da COMMIT", chi hien form neu vi da commit on-chain
        if c["status"] == "REVEAL":
            if not already_committed_onchain:
                st.markdown("""
                <div class="alert-warn">
                ⚠️ <b>Ví này chưa commit phiếu</b> trong chiến dịch này.<br>
                Giai đoạn COMMIT đã kết thúc — không thể commit thêm. Chỉ những ví đã commit mới có thể reveal.
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("#### Giai đoạn 2: REVEAL — Công bố phiếu thực tế")
                saved_salt, saved_opt = load_commit(campaign_id)
                if saved_salt:
                    st.markdown('<div class="alert-ok">✅ Tìm thấy commit đã lưu — salt được điền sẵn bên dưới.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="alert-warn">⚠️ Không tìm thấy commit đã lưu trong session — nhập thủ công bên dưới.</div>', unsafe_allow_html=True)
                    saved_opt = 0
                vote_choice_r = st.radio("Phiếu đã commit:", ["FOR (0)", "AGAINST (1)", "ABSTAIN (2)"], index=saved_opt or 0, horizontal=True, key=f"reveal_radio_committed_{campaign_id}")
                option_map_r = {"FOR (0)": 0, "AGAINST (1)": 1, "ABSTAIN (2)": 2}
                reveal_option_r = option_map_r[vote_choice_r]
                reveal_salt_r = st.text_input("Salt đã dùng lúc Commit:", value=saved_salt or "", key=f"reveal_salt_committed_{campaign_id}")
                if st.button("👁 GỦI REVEAL", type="primary", use_container_width=True, key=f"reveal_btn_committed_{campaign_id}"):
                    with st.spinner("Đang reveal vote..."):
                        ok_rv, msg_rv = reveal_vote_onchain(campaign_id, reveal_option_r, reveal_salt_r)
                    if ok_rv:
                        st.success(msg_rv)
                        _refresh_live_data()
                        time.sleep(0.5); st.rerun()
                    else:
                        st.error(msg_rv)

    elif c["status"] not in ("ACTIVE","COMMIT","REVEAL"):
        st.markdown(f'<div class="alert-warn">⚠️ Chiến dịch trạng thái <b>{c["status"]}</b> — không thể bỏ phiếu.</div>', unsafe_allow_html=True)

    elif not is_connected():
        st.markdown("""
        <div class="alert-err">
        ❌ <b>Chưa kết nối Ganache.</b><br>
        Bỏ phiếu yêu cầu kết nối blockchain thực. Bấm <b>🔌 Kết nối</b> ở sidebar.
        </div>""", unsafe_allow_html=True)

    elif not can_vote:
        st.markdown("""
        <div class="alert-err">
        ❌ <b>Ví chưa đủ điều kiện biểu quyết.</b><br>
        Nguyên nhân có thể: số dư HST = 0, chưa self-delegate, hoặc tài khoản bị khóa.<br>
        Chạy lại <code>setup_demo.js</code> và <code>setup_campaign.js</code> rồi đăng nhập lại.
        </div>""", unsafe_allow_html=True)

    elif not has_pk:
        st.markdown("""
        <div class="alert-warn">
        ⚠️ <b>Chưa nhập Private Key.</b><br>
        Vào <b>Đăng nhập ví</b> và nhập private key Ganache để ký transaction bỏ phiếu.
        </div>""", unsafe_allow_html=True)

    else:
        # ── Form bỏ phiếu thực sự ────────────────────────────────────────────
        if not c.get("isCommitReveal"):
            # Standard vote
            st.markdown("""
            <div class="alert-info">
            ℹ️ <b>Bỏ phiếu thông thường</b> — Lựa chọn của bạn được ghi trực tiếp lên blockchain.
            Tổng kết quả hiển thị công khai nhưng danh tính người bỏ phiếu được ẩn trên dashboard.
            </div>""", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ BỎ PHIẾU: FOR", use_container_width=True, key="vote_for"):
                    with st.spinner("Đang gửi transaction..."):
                        ok, msg = cast_vote_onchain(campaign_id, 0)
                    if ok:
                        st.success(msg)
                        _refresh_live_data()
                        time.sleep(0.5); st.rerun()
                    else:
                        st.error(msg)
            with col2:
                if st.button("❌ BỎ PHIẾU: AGAINST", use_container_width=True, key="vote_ag"):
                    with st.spinner("Đang gửi transaction..."):
                        ok, msg = cast_vote_onchain(campaign_id, 1)
                    if ok:
                        st.success(msg)
                        _refresh_live_data()
                        time.sleep(0.5); st.rerun()
                    else:
                        st.error(msg)
            with col3:
                if st.button("⬜ BỎ PHIẾU: ABSTAIN", use_container_width=True, key="vote_abs"):
                    with st.spinner("Đang gửi transaction..."):
                        ok, msg = cast_vote_onchain(campaign_id, 2)
                    if ok:
                        st.success(msg)
                        _refresh_live_data()
                        time.sleep(0.5); st.rerun()
                    else:
                        st.error(msg)

        else:
            # Commit-Reveal
            st.markdown("""
            <div class="alert-info">
            🔒 <b>Bỏ phiếu kín Commit-Reveal</b> — Giai đoạn 2 bước để đảm bảo không ai biết phiếu của nhau trước khi kết thúc.
            </div>""", unsafe_allow_html=True)

            if c["status"] == "COMMIT":
                # Lấy block.timestamp on-chain để so sánh chính xác với commitDeadline
                commit_deadline = c.get("commitDeadline", 0)
                try:
                    chain_now = st.session_state["w3"].eth.get_block("latest")["timestamp"] if is_connected() else int(time.time())
                except Exception:
                    chain_now = int(time.time())
                commit_ended = commit_deadline > 0 and chain_now >= commit_deadline

                if commit_ended:
                    # Commit phase đã kết thúc — chờ chuyển sang REVEAL
                    remaining_reveal = c.get("revealStart", 0) - chain_now
                    st.markdown('<div class="alert-warn">⏰ <b>Giai đoạn COMMIT đã kết thúc.</b> Cần chuyển sang REVEAL để tiếp tục.</div>', unsafe_allow_html=True)

                    pk = st.session_state.get("private_key")
                    if pk:
                        if st.button("▶ Chuyển sang giai đoạn REVEAL (transitionToReveal)", type="primary", use_container_width=True, key=f"transition_{campaign_id}"):
                            try:
                                w3_  = st.session_state["w3"]
                                gov_ = st.session_state["contracts"]["gov"]
                                func = gov_.functions.transitionToReveal(campaign_id)
                                tx   = build_tx(func, wallet_addr, w3_)
                                receipt = send_signed_tx(tx, pk, w3_)
                                if receipt["status"] == 1:
                                    st.success("✅ Đã chuyển sang REVEAL!")
                                    _refresh_live_data()
                                    time.sleep(0.5); st.rerun()
                                else:
                                    st.error("Transaction revert.")
                            except Exception as e:
                                st.error(f"Lỗi: {str(e)[:120]}")
                    else:
                        st.markdown('<div class="alert-warn">⚠️ Cần Private Key (có CAMPAIGN_MANAGER_ROLE) để chuyển sang REVEAL.</div>', unsafe_allow_html=True)

                    with st.expander("⚡ Ganache Demo: Bỏ qua thời gian commit"):
                        st.warning("Chỉ dùng trên Ganache local.")
                        if st.button("⏩ Nhảy qua commitDeadline", key=f"skip_commit_ended_{campaign_id}"):
                            try:
                                w3_ = st.session_state["w3"]
                                jump = max(commit_deadline - chain_now + 60, 60)
                                w3_.provider.make_request("evm_increaseTime", [jump])
                                w3_.provider.make_request("evm_mine", [])
                                st.success(f"✅ Đã nhảy {jump}s. Bấm transitionToReveal.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"evm_increaseTime thất bại: {e}")
                else:
                    # Commit phase còn hiệu lực
                    remaining_commit = commit_deadline - chain_now if commit_deadline > 0 else 0
                    days_c  = remaining_commit // 86400
                    hours_c = (remaining_commit % 86400) // 3600
                    mins_c  = (remaining_commit % 3600) // 60
                    st.markdown(f'<div class="alert-info">⏳ Giai đoạn COMMIT còn <b>{days_c}d {hours_c}h {mins_c}m</b>.</div>', unsafe_allow_html=True)

                    st.markdown("#### Giai đoạn 1: COMMIT — Gửi hash phiếu kín")

                    vote_choice = st.radio("Chọn phiếu (sẽ được mã hóa):", ["FOR (0)", "AGAINST (1)", "ABSTAIN (2)"], horizontal=True)
                    option_map = {"FOR (0)": 0, "AGAINST (1)": 1, "ABSTAIN (2)": 2}
                    option_idx = option_map[vote_choice]

                    _salt_draft_key = f"salt_draft_{campaign_id}"
                    if st.button("🎲 Tạo Salt ngẫu nhiên"):
                        st.session_state[_salt_draft_key] = "0x" + secrets.token_hex(32)
                    salt_val = st.text_input("Salt bí mật (lưu lại!)", value=st.session_state.get(_salt_draft_key,""), key="salt_input")

                    if salt_val:
                        try:
                            w3 = st.session_state.get("w3") or Web3()
                            salt_bytes = bytes.fromhex(salt_val.replace("0x",""))
                            preview_hash = w3.keccak(b"".join([option_idx.to_bytes(1,"big"), salt_bytes, bytes.fromhex(wallet_addr.replace("0x",""))])).hex()
                            st.markdown(f'<div style="background:#0a1020;padding:10px;border-radius:8px;font-family:monospace;font-size:11px;color:#6aafff;word-break:break-all">Hash sẽ gửi: 0x{preview_hash}</div>', unsafe_allow_html=True)
                        except Exception as ex:
                            st.warning(f"Không thể tính hash preview: {ex}")

                    st.markdown("""<div class="alert-warn">⚠️ <b>Quan trọng:</b> Lưu lại Salt này! Bạn cần salt để REVEAL phiếu ở giai đoạn 2. Mất salt = mất phiếu.</div>""", unsafe_allow_html=True)

                    if salt_val and st.button("🔒 GỬI COMMIT", type="primary", use_container_width=True):
                        with st.spinner("Đang commit vote lên blockchain..."):
                            ok, msg = commit_vote_onchain(campaign_id, option_idx, salt_val)
                        if ok:
                            st.success(msg)
                            time.sleep(0.5); st.rerun()
                        else:
                            st.error(msg)

                    with st.expander("⚡ Ganache Demo: Bỏ qua thời gian commit"):
                        st.warning("Chỉ dùng trên Ganache local.")
                        if st.button("⏩ Nhảy qua commitDeadline", key=f"skip_commit_active_{campaign_id}"):
                            try:
                                w3_ = st.session_state["w3"]
                                jump = remaining_commit + 60
                                w3_.provider.make_request("evm_increaseTime", [jump])
                                w3_.provider.make_request("evm_mine", [])
                                st.success(f"✅ Đã nhảy {jump}s. Refresh để cập nhật.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"evm_increaseTime thất bại: {e}")

            elif c["status"] == "REVEAL":
                # Chỉ hiện form reveal nếu ví này ĐÃ commit on-chain
                # (already_committed_onchain đã được tính ở trên với wallet hiện tại)
                if not already_committed_onchain:
                    st.markdown("""
                    <div class="alert-warn">
                    ⚠️ <b>Ví này chưa commit phiếu</b> trong chiến dịch này.<br>
                    Giai đoạn COMMIT đã kết thúc — không thể commit thêm. Chỉ những ví đã commit mới có thể reveal.
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown("#### Giai đoạn 2: REVEAL — Công bố phiếu thực tế")
                    saved_salt, saved_opt = load_commit(campaign_id)
                    if saved_salt:
                        st.markdown('<div class="alert-ok">✅ Tìm thấy commit đã lưu — salt được điền sẵn bên dưới.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="alert-warn">⚠️ Không tìm thấy commit đã lưu trong session (có thể do restart trình duyệt) — nhập thủ công bên dưới.</div>', unsafe_allow_html=True)
                        saved_opt = 0

                    vote_choice = st.radio("Phiếu đã commit:", ["FOR (0)", "AGAINST (1)", "ABSTAIN (2)"], index=saved_opt or 0, horizontal=True, key=f"reveal_radio_normal_{campaign_id}")
                    option_map = {"FOR (0)": 0, "AGAINST (1)": 1, "ABSTAIN (2)": 2}
                    reveal_option = option_map[vote_choice]
                    reveal_salt = st.text_input("Salt đã dùng lúc Commit:", value=saved_salt or "", key=f"reveal_salt_normal_{campaign_id}")

                    if st.button("👁 GỬI REVEAL", type="primary", use_container_width=True, key=f"reveal_btn_normal_{campaign_id}"):
                        with st.spinner("Đang reveal vote..."):
                            ok, msg = reveal_vote_onchain(campaign_id, reveal_option, reveal_salt)
                        if ok:
                            st.success(msg)
                            _refresh_live_data()
                            time.sleep(0.5); st.rerun()
                        else:
                            st.error(msg)
            else:
                st.info(f"Commit-Reveal campaign hiện đang ở trạng thái {c['status']} — không thể tương tác.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Cổ đông
# ═══════════════════════════════════════════════════════════════════════════════
elif "👥 Cổ đông" in page:
    st.markdown("# 👥 Danh sách Cổ đông")
    shareholders, sh_live = get_shareholders()
    if sh_live:
        st.markdown('<div class="alert-ok">✅ Dữ liệu on-chain</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-warn">⚠️ Demo mode</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2,1])
    with col1: search = st.text_input("🔍 Tìm kiếm", "")
    with col2: tf = st.selectbox("Tier", ["Tất cả","🥇 Tier 3","🥈 Tier 2","🥉 Tier 1","🔵 Tier 0"])

    tm = {"🥇 Tier 3":3,"🥈 Tier 2":2,"🥉 Tier 1":1,"🔵 Tier 0":0}
    filtered = shareholders
    if search: filtered = [s for s in filtered if search.lower() in s["name"].lower()]
    if tf != "Tất cả": filtered = [s for s in filtered if s["tier"] == tm[tf]]

    st.markdown("""
    <div style="display:grid;grid-template-columns:2.5fr 2fr 2fr 1.2fr 1.2fr;gap:8px;padding:8px 12px;background:#0d1626;border-radius:8px;margin-top:12px;font-size:11px;color:#556;font-weight:700;letter-spacing:1px">
    <div>TÊN</div><div>HST</div><div>VOTING POWER</div><div>TIER</div><div>TRẠNG THÁI</div>
    </div>""", unsafe_allow_html=True)

    for s in filtered:
        color = tier_color(s["tier"])
        status_html = '<span style="color:#3aff6a">● Active</span>' if s.get("active",True) else '<span style="color:#ff6a3a">✕ Khóa</span>'
        vp = s.get("vp", s["hst"])
        st.markdown(
            f'<div style="display:grid;grid-template-columns:2.5fr 2fr 2fr 1.2fr 1.2fr;gap:8px;padding:12px;background:#0d1626;border-radius:8px;margin:3px 0;border:1px solid #1a2a44;font-size:13px;align-items:center">'
            f'<div style="color:#ccd;font-weight:600">{s["name"]}</div>'
            f'<div style="color:{color};font-weight:700">{fmt_num(s["hst"])}</div>'
            f'<div style="color:#4a9eff">{fmt_num(vp)}</div>'
            f'<div style="color:{color}">{tier_label(s["tier"])}</div>'
            f'<div>{status_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Phân tích
# ═══════════════════════════════════════════════════════════════════════════════
elif "📊 Phân tích" in page:
    st.markdown("# 📊 Phân tích Cơ chế Biểu quyết")
    shareholders, _ = get_shareholders()
    campaigns, _ = get_campaigns()

    tab1, tab2 = st.tabs(["⚖️ Linear vs Quadratic vs Equal", "📈 Tỷ lệ tham gia"])

    with tab1:
        names    = [s["name"] for s in shareholders]
        balances = [int(s["hst"]) for s in shareholders]
        quad_w   = [int(math.sqrt(b)) for b in balances]
        total_l  = sum(balances); total_q = sum(quad_w)
        lin_pct  = [b/total_l*100 for b in balances] if total_l > 0 else [0]*len(balances)
        qua_pct  = [b/total_q*100 for b in quad_w] if total_q > 0 else [0]*len(balances)
        eq_pct   = [100/len(names)]*len(names) if names else []

        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr;gap:6px;padding:8px 12px;background:#0d1626;border-radius:8px;font-size:11px;color:#556;font-weight:700;letter-spacing:1px">
        <div>CỔ ĐÔNG</div><div>TOKEN</div><div>LIN weight</div><div>LIN %</div><div>QUAD weight</div><div>QUAD %</div><div>EQUAL %</div>
        </div>""", unsafe_allow_html=True)

        colors_list = ["#ffd700","#c0c0c0","#cd7f32","#cd7f32","#8899bb"]
        for i, name in enumerate(names):
            color = colors_list[i] if i < len(colors_list) else "#8899bb"
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr;gap:6px;padding:10px 12px;background:#0d1626;border-radius:8px;margin:3px 0;border-left:3px solid {color};font-size:13px;align-items:center">
            <div style="color:#ccd;font-weight:600">{name}</div>
            <div style="color:{color}">{fmt_num(balances[i])}</div>
            <div style="color:#4a9eff">{fmt_num(balances[i])}</div>
            <div style="color:#4a9eff;font-weight:700">{lin_pct[i]:.1f}%</div>
            <div style="color:#3adc6a">{fmt_num(quad_w[i])}</div>
            <div style="color:#3adc6a;font-weight:700">{qua_pct[i]:.1f}%</div>
            <div style="color:#e0a040;font-weight:700">{eq_pct[i]:.1f}%</div>
            </div>""", unsafe_allow_html=True)

    with tab2:
        _supply = get_total_supply()   # on-chain totalSupply (fallback 10M nếu offline)
        for c in campaigns:
            total = c["forVotes"] + c["againstVotes"] + c["abstainVotes"]
            part  = total/_supply*100 if _supply > 0 else 0
            color = "#2adc6a" if part >= c["quorumBps"] else "#dcaa2a"
            decisive = c["forVotes"] + c["againstVotes"]
            fp = c["forVotes"]/decisive*100 if decisive > 0 else 0
            _badge = status_badge(c["status"])
            st.markdown(
                f'<div class="dao-card"><div style="display:flex;justify-content:space-between;margin-bottom:8px"><b style="color:#eef">#{c["id"]} {c["title"][:40]}</b>'
                + _badge +
                f'</div><div style="font-size:12px;color:#778;margin-bottom:8px">📌 {c["proposalType"]} | Quorum: {c["quorumBps"]:.0f}% | FOR: {fp:.1f}%</div>'
                f'<div style="background:#0d1626;border-radius:6px;height:12px;overflow:hidden"><div style="width:{min(part,100):.1f}%;background:linear-gradient(90deg,{color}88,{color});height:100%;border-radius:6px"></div></div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px"><span style="color:{color}">Tham gia: {part:.1f}%</span><span style="color:#556">Quorum: {c["quorumBps"]:.0f}%</span></div></div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Hướng dẫn
# ═══════════════════════════════════════════════════════════════════════════════
elif "⚙️ Hướng dẫn" in page:
    st.markdown("# ⚙️ Hướng dẫn Sử dụng Dashboard")

    tab1, tab2, tab3 = st.tabs(["🗺️ Các trang", "🔐 Đăng nhập & Bỏ phiếu", "🔒 Commit-Reveal"])

    with tab1:
        st.markdown("""
### Dashboard gồm 5 trang — chọn ở menu bên trái:

**🏠 Tổng quan**
Xem ngay số liệu tổng hợp: số cổ đông, tổng HST, chiến dịch đang mở và số nghị quyết đã thông qua.
Bên trái là các chiến dịch đang mở với thanh biểu quyết thực tế. Bấm **Bỏ phiếu →** để chuyển thẳng sang trang bỏ phiếu cho chiến dịch đó.
Bên phải là biểu đồ phân bổ token của từng cổ đông.

**🔐 Đăng nhập ví**
Nhập địa chỉ ví và private key để xác thực. Sau khi đăng nhập sẽ thấy số dư HST, voting power và trạng thái đủ điều kiện hay không.

**🗳️ Bỏ phiếu**
Chọn chiến dịch, xem kết quả hiện tại rồi bấm FOR / AGAINST / ABSTAIN để bỏ phiếu lên blockchain. Cần đăng nhập trước.

**👥 Cổ đông**
Danh sách tất cả cổ đông với số dư, voting power và tier. Có thể lọc theo tier hoặc tìm kiếm theo tên / địa chỉ.

**📊 Phân tích**
So sánh trực quan 3 cơ chế biểu quyết và xem tỷ lệ tham gia từng chiến dịch so với ngưỡng quorum.
        """)

    with tab2:
        st.markdown("""
### Cách đăng nhập

1. Vào trang **🔐 Đăng nhập ví**
2. Nhập **Địa chỉ ví** vào ô trên
3. Nhập **Private Key** vào ô dưới
4. Bấm nút **🔐 Đăng nhập**

Đăng nhập thành công sẽ hiện thông tin ví ở sidebar và có thể bắt đầu bỏ phiếu.

---

### Cách bỏ phiếu thông thường

1. Đăng nhập ví trước
2. Vào trang **🗳️ Bỏ phiếu**
3. Chọn chiến dịch từ danh sách thả xuống
4. Xem thông tin và kết quả hiện tại của chiến dịch
5. Bấm **✅ FOR**, **❌ AGAINST** hoặc **⬜ ABSTAIN**
6. Xác nhận — transaction sẽ ghi lên blockchain ngay lập tức

> Mỗi ví chỉ bỏ phiếu được **1 lần** cho mỗi chiến dịch.
        """)

    with tab3:
        st.markdown("""
### Chiến dịch Commit-Reveal (🔒)

Đây là hình thức **bỏ phiếu kín 2 bước** — không ai biết bạn chọn gì cho đến khi kết thúc giai đoạn commit.

**Giai đoạn COMMIT** (trạng thái 🔒 COMMIT):
1. Vào trang **🗳️ Bỏ phiếu**, chọn chiến dịch Commit-Reveal
2. Chọn lựa chọn bỏ phiếu
3. Hệ thống tạo salt ngẫu nhiên — **lưu lại salt này**, sẽ cần ở bước sau
4. Bấm **📝 GỬI COMMIT**

**Giai đoạn REVEAL** (trạng thái 👁 REVEAL):
1. Quay lại chiến dịch đó
2. Chọn lại đúng lựa chọn đã commit
3. Nhập lại salt đã lưu
4. Bấm **👁 GỬI REVEAL** để công bố phiếu

> ❗ Nếu quên salt hoặc chọn sai lựa chọn → phiếu sẽ không hợp lệ.
        """)