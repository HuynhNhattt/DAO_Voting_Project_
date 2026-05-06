"""
dashboard/app.py
─────────────────
Phase 4 — Streamlit Dashboard cho DAO Voting System
Chạy: streamlit run dashboard/app.py --server.fileWatcherType none

Các fix so với phiên bản cũ:
  1. Kết nối tự động lưu trạng thái đúng — st.rerun() sau khi connect thành công
  2. Reconnect tự động nếu w3 bị mất giữa session (ví dụ Ganache restart)
  3. Demo chiến dịch hiển thị đúng khi chưa kết nối (không lấy live=[] rỗng khi đã kết nối)
  4. total_hst_supply lấy từ on-chain thay vì hardcode 10_000_000
  5. conn_checked reset đúng để auto-connect lại sau khi w3 = None
"""

import streamlit as st
import json
import math
import time
from datetime import datetime
from pathlib import Path
import sys
import os
os.environ["PYTHONUTF8"] = "1"

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DAO Voting System",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Try import web3 ──────────────────────────────────────────────────────────
try:
    _root = Path(__file__).parent
    for _candidate in [_root / "utils", _root.parent / "utils", _root]:
        if (_candidate / "web3_helpers.py").exists():
            sys.path.insert(0, str(_candidate))
            break

    from web3_helpers import (
        connect_web3, get_all_contracts,
        get_shareholder_info, get_voting_power, get_token_balance,
        get_all_campaigns, get_campaign_data, get_vote_participation,
        load_addresses,
    )
    WEB3_AVAILABLE = True
except ImportError as _e:
    WEB3_AVAILABLE = False
    _WEB3_IMPORT_ERR = str(_e)

# ─── CSS Styling ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b27 !important; border-right: 1px solid #2a2f3e; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #1a1f2e; border-radius: 6px; }
::-webkit-scrollbar-thumb { background: #3a4a6a; border-radius: 6px; border: 2px solid #1a1f2e; }
::-webkit-scrollbar-thumb:hover { background: #4a7afa; }

div[data-testid="stButton"] > button[kind="secondary"] {
    margin-top: -4px !important;
    border-radius: 0 0 12px 12px !important;
    border: 1px solid #2a3a5e !important;
    border-top: none !important;
    background: #1a2236 !important;
    color: #4a9eff !important;
    font-size: 12px !important;
    padding: 4px 12px !important;
    height: auto !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #1e2d4a !important;
    border-color: #4a7afa !important;
    color: #6ab4ff !important;
}

.dao-card {
    background: linear-gradient(135deg, #1a1f2e 0%, #1e2535 100%);
    border: 1px solid #2a3a5e;
    border-radius: 12px;
    padding: 20px;
    margin: 8px 0;
}
.dao-card:hover { border-color: #4a7afa; }

.badge-active   { background:#0d3b1a; color:#2ddc64; border:1px solid #2ddc64; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-draft    { background:#2a2d1a; color:#e0c040; border:1px solid #e0c040; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-executed { background:#1a2d4a; color:#4a9eff; border:1px solid #4a9eff; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-defeated { background:#3b0d0d; color:#ff4a4a; border:1px solid #ff4a4a; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-other    { background:#2a2a3a; color:#aaaacc; border:1px solid #aaaacc; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }

.vote-bar-wrap  { background:#1a1f2e; border-radius:8px; height:22px; overflow:hidden; display:flex; }
.vote-bar-for   { background:linear-gradient(90deg,#1a7a3a,#2ddc64); height:100%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:white; }
.vote-bar-ag    { background:linear-gradient(90deg,#7a1a1a,#dc2d2d); height:100%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:white; }
.vote-bar-abs   { background:#2a2d40; height:100%; }

.section-header {
    font-size:18px; font-weight:700; color:#4a9eff;
    border-bottom: 1px solid #2a3a5e; padding-bottom:8px; margin: 20px 0 12px 0;
}

.alert-warn { background:#2a2010; border:1px solid #e0a020; border-radius:8px; padding:12px 16px; color:#e0c060; font-size:13px; }
.alert-ok   { background:#0d2a1a; border:1px solid #2ddc64; border-radius:8px; padding:12px 16px; color:#4dfc84; font-size:13px; }
.alert-err  { background:#2a0d0d; border:1px solid #dc2d2d; border-radius:8px; padding:12px 16px; color:#fc4d4d; font-size:13px; }

.timeline-item { display:flex; gap:12px; margin:8px 0; }
.timeline-dot  { width:10px; height:10px; border-radius:50%; background:#4a9eff; margin-top:5px; flex-shrink:0; }
.timeline-text { color:#ccd; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Defaults ────────────────────────────────────────────────────
_SS_DEFAULTS = {
    "w3":                None,
    "contracts":         None,
    "conn_error":        None,
    # conn_checked: True sau khi đã thử kết nối lần đầu
    # Reset về False khi w3 bị mất để trigger reconnect ở lần reload tiếp theo
    "conn_checked":      False,
    "live_shareholders": None,
    "live_campaigns":    None,
    "goto_campaign_page": False,
    "selected_campaign": None,
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Connection Helper ────────────────────────────────────────────────────────
def do_connect(rpc_url: str):
    """Thử kết nối và lưu vào session_state. Trả về (success, error_msg)."""
    if not WEB3_AVAILABLE:
        msg = "⚠️ Thư viện web3 chưa cài: pip install -r requirements.txt"
        st.session_state["conn_error"] = msg
        st.session_state["w3"] = None
        st.session_state["contracts"] = None
        return False, msg
    try:
        w3 = connect_web3(rpc_url)
        contracts = get_all_contracts(w3)
        st.session_state["w3"] = w3
        st.session_state["contracts"] = contracts
        st.session_state["conn_error"] = None
        st.session_state["conn_checked"] = True
        _refresh_live_data()
        return True, None
    except FileNotFoundError:
        msg = "📄 Chưa deploy contract. Chạy: npx hardhat run scripts/setup_demo.js --network ganache"
        st.session_state["conn_error"] = msg
        st.session_state["w3"] = None
        st.session_state["contracts"] = None
        st.session_state["conn_checked"] = True
        return False, msg
    except ConnectionError:
        msg = f"❌ Không kết nối được Ganache tại {rpc_url}. Hãy mở Ganache và thử lại."
        st.session_state["conn_error"] = msg
        st.session_state["w3"] = None
        st.session_state["contracts"] = None
        st.session_state["conn_checked"] = True
        return False, msg
    except Exception as e:
        msg = f"Lỗi kết nối: {e}"
        st.session_state["conn_error"] = msg
        st.session_state["w3"] = None
        st.session_state["contracts"] = None
        st.session_state["conn_checked"] = True
        return False, msg


def _refresh_live_data():
    """Load shareholders & campaigns từ on-chain, lưu vào session."""
    contracts = st.session_state.get("contracts")
    if not contracts:
        return

    # Load shareholders
    try:
        addrs = load_addresses()
        shareholders_list = []
        for sh in addrs.get("shareholders", []):
            wallet = sh["address"]
            hst_bal = get_token_balance(contracts["hst"], wallet)
            vp      = get_voting_power(contracts["hst"], wallet)
            info    = get_shareholder_info(contracts["registry"], wallet)
            tier    = info["tier"] if info else sh.get("tier", 0)
            active  = info["isActive"] if info else False
            shareholders_list.append({
                "name":    sh["name"],
                "address": wallet,
                "hst":     hst_bal,
                "vp":      vp,
                "tier":    tier,
                "active":  active,
            })
        st.session_state["live_shareholders"] = shareholders_list
    except Exception:
        st.session_state["live_shareholders"] = None

    # Load campaigns
    try:
        camps = get_all_campaigns(contracts["gov"])
        st.session_state["live_campaigns"] = camps  # có thể là []
    except Exception:
        st.session_state["live_campaigns"] = None


def is_connected() -> bool:
    """Kiểm tra kết nối còn sống không — thử ping nếu w3 tồn tại."""
    w3 = st.session_state.get("w3")
    if w3 is None:
        return False
    try:
        _ = w3.eth.block_number   # ping nhẹ
        return True
    except Exception:
        # Mất kết nối — reset state để auto-reconnect lần sau
        st.session_state["w3"] = None
        st.session_state["contracts"] = None
        st.session_state["conn_checked"] = False   # trigger auto-connect lại
        return False


def get_total_supply_onchain() -> float:
    """Lấy totalSupply HST thực tế từ on-chain nếu đã kết nối."""
    if is_connected():
        try:
            return st.session_state["contracts"]["hst"].functions.totalSupply().call() / 10**18
        except Exception:
            pass
    return sum(s["hst"] for s in DEMO_SHAREHOLDERS)


# ─── Auto-connect lần đầu ─────────────────────────────────────────────────────
# Chỉ thử 1 lần per session.  Nếu conn_checked=False (chưa thử hoặc đã mất kết
# nối) → thử lại.  Sau khi thành công → st.rerun() để toàn bộ UI nhận trạng
# thái connected ngay lập tức thay vì chờ interaction tiếp theo.
if not st.session_state["conn_checked"] and WEB3_AVAILABLE:
    _rpc = st.session_state.get("rpc_input", "http://127.0.0.1:7545")
    ok, _ = do_connect(_rpc)
    # conn_checked đã được set True bên trong do_connect
    if ok:
        st.rerun()


# ─── Demo Data ────────────────────────────────────────────────────────────────
DEMO_SHAREHOLDERS = [
    {"name": "Chủ tịch HĐQT",       "address": "0x7CdDA1906f74bC60489c88014E59D43c5aE1E090", "hst": 4_500_000, "vp": 4_500_000, "tier": 3, "active": True},
    {"name": "Quỹ phát triển",       "address": "0xF154cdf664a7503dc99F583F3938Ae1025DB5700", "hst": 2_500_000, "vp": 2_500_000, "tier": 2, "active": True},
    {"name": "Cổ đông A (Tổ chức)", "address": "0x925A4276bb6dc38f343986545Ff93173205c51B5", "hst": 1_500_000, "vp": 1_500_000, "tier": 1, "active": True},
    {"name": "Cổ đông B (Tổ chức)", "address": "0xFd0Cc892A5c8F13f82234f1d19DCA19fe7Dcd59a", "hst": 1_000_000, "vp": 1_000_000, "tier": 1, "active": True},
    {"name": "Cổ đông C (Nhỏ lẻ)",  "address": "0x78f45F34CdB10fF819C1706228012B50DbD91985", "hst":   500_000, "vp":   500_000, "tier": 0, "active": True},
]

DEMO_CAMPAIGNS = [
    {
        "id": 101, "title": "Phê duyệt ngân sách R&D 2025",
        "description": "Phân bổ 2 tỷ VNĐ cho nghiên cứu và phát triển sản phẩm mới Q1-Q2 2025.",
        "proposalType": "Routine", "mechanism": "Linear", "status": "EXECUTED",
        "forVotes": 3_500_000, "againstVotes": 1_500_000, "abstainVotes": 500_000,
        "passThreshold": 50.0, "quorumBps": 10.0, "isCommitReveal": False,
    },
    {
        "id": 102, "title": "Chia cổ tức 15% năm 2024",
        "description": "Đề xuất chia cổ tức 15% trên mệnh giá cổ phần cho toàn bộ cổ đông hiện hữu.",
        "proposalType": "Major", "mechanism": "Linear", "status": "EXECUTED",
        "forVotes": 7_000_000, "againstVotes": 2_000_000, "abstainVotes": 1_000_000,
        "passThreshold": 66.0, "quorumBps": 20.0, "isCommitReveal": False,
    },
    {
        "id": 103, "title": "Bầu CEO mới — So sánh Linear vs Quadratic",
        "description": "Bầu chọn CEO nhiệm kỳ 2025-2028. Kịch bản so sánh 2 cơ chế biểu quyết.",
        "proposalType": "Major", "mechanism": "Quadratic", "status": "ACTIVE",
        "forVotes": 2_236, "againstVotes": 1_000, "abstainVotes": 200,
        "passThreshold": 66.0, "quorumBps": 20.0, "isCommitReveal": False,
    },
    {
        "id": 104, "title": "Sáp nhập M&A — TechCorp Ltd",
        "description": "Thương vụ M&A chiến lược với TechCorp Ltd, định giá 150 tỷ VNĐ.",
        "proposalType": "M&A", "mechanism": "Linear", "status": "COMMIT",
        "forVotes": 0, "againstVotes": 0, "abstainVotes": 0,
        "passThreshold": 75.0, "quorumBps": 30.0, "isCommitReveal": True,
    },
]

# ─── Helper Functions ─────────────────────────────────────────────────────────
def fmt_num(n): return f"{n:,.0f}"
def fmt_hst(n): return f"{n:,.0f} HST"

def tier_label(t):
    labels = {3: "🥇 Sáng lập", 2: "🥈 Chiến lược", 1: "🥉 Tổ chức", 0: "🔵 Nhỏ lẻ"}
    return labels.get(t, "Unknown")

def status_badge(s):
    if s == "ACTIVE":  return '<span class="badge-active">● ACTIVE</span>'
    if s == "EXECUTED": return '<span class="badge-executed">✓ EXECUTED</span>'
    if s == "DEFEATED": return '<span class="badge-defeated">✗ DEFEATED</span>'
    if s == "DRAFT":   return '<span class="badge-draft">○ DRAFT</span>'
    if s == "COMMIT":  return '<span class="badge-other">🔒 COMMIT</span>'
    if s == "REVEAL":  return '<span class="badge-other">👁 REVEAL</span>'
    return f'<span class="badge-other">{s}</span>'

def vote_bar(for_v, against_v, abstain_v):
    total = for_v + against_v + abstain_v
    if total == 0:
        return '<div class="vote-bar-wrap"><div style="width:100%;background:#2a2f3e;height:100%"></div></div>'
    fp = for_v / total * 100
    ap = against_v / total * 100
    return f"""
    <div class="vote-bar-wrap">
        <div class="vote-bar-for"  style="width:{fp:.1f}%">{fp:.0f}%</div>
        <div class="vote-bar-ag"   style="width:{ap:.1f}%">{ap:.0f}%</div>
        <div class="vote-bar-abs"  style="width:{100-fp-ap:.1f}%"></div>
    </div>"""


def get_shareholders():
    """Trả về (data, is_live). Live nếu kết nối VÀ có dữ liệu."""
    if is_connected():
        live = st.session_state.get("live_shareholders")
        if live is not None:
            return live, True
    return DEMO_SHAREHOLDERS, False


def get_campaigns():
    """
    Trả về (data, is_live).
    - Nếu đã kết nối VÀ live_campaigns không phải None → trả về live (dù rỗng [])
    - Nếu chưa kết nối HOẶC live_campaigns là None → trả về DEMO
    BUG FIX: trước đây khi kết nối thành công nhưng chưa có campaign,
    live=[] làm UI bỏ trống mà không fallback sang demo.
    Bây giờ: is_live=True khi kết nối dù rỗng — UI sẽ hiển thị hướng dẫn riêng.
    """
    if is_connected():
        live = st.session_state.get("live_campaigns")
        if live is not None:
            return live, True
    return DEMO_CAMPAIGNS, False


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏛️ DAO Voting System")
    st.markdown("**Blockchain Governance Platform**")
    st.markdown("---")

    _default_page_idx = 0
    if st.session_state.get("goto_campaign_page"):
        _default_page_idx = 2
        st.session_state["goto_campaign_page"] = False

    page = st.radio(
        "Điều hướng",
        ["🏠 Tổng quan", "👥 Cổ đông", "🗳️ Chiến dịch", "📊 Phân tích", "⚙️ Hướng dẫn"],
        index=_default_page_idx,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**⚙️ Kết nối**")

    rpc_url = st.text_input("RPC URL", value="http://127.0.0.1:7545", key="rpc_input")

    col_btn, col_ind = st.columns([3, 1])
    with col_btn:
        connect_btn = st.button("🔌 Kết nối Ganache", use_container_width=True)
    with col_ind:
        _dot_color = "#2ddc64" if is_connected() else "#e0a020"
        st.markdown(
            f'<div style="margin-top:8px"><span style="display:inline-block;'
            f'width:10px;height:10px;border-radius:50%;background:{_dot_color};'
            f'box-shadow:0 0 6px {_dot_color}"></span></div>',
            unsafe_allow_html=True,
        )

    # FIX: nút kết nối có st.rerun() sau khi thành công
    if connect_btn:
        with st.spinner("Đang kết nối..."):
            ok_conn, err = do_connect(rpc_url)
        if ok_conn:
            st.success("✅ Kết nối thành công!")
            time.sleep(0.4)
            st.rerun()   # ← FIX: reload để toàn bộ UI nhận trạng thái mới
        else:
            st.error(f"❌ {err}")

    if is_connected():
        if st.button("🔄 Refresh dữ liệu", use_container_width=True):
            _refresh_live_data()
            st.success("✅ Đã cập nhật!")
            st.rerun()

    st.markdown("---")
    if is_connected():
        w3 = st.session_state["w3"]
        try:
            block = w3.eth.block_number
            chain = w3.eth.chain_id
            st.markdown(f"""
            <div style="background:#0d2a1a;border:1px solid #2ddc64;border-radius:8px;padding:10px;font-size:12px;color:#4dfc84">
            ✅ <b>Đã kết nối Ganache</b><br>
            Block: #{block} | Chain: {chain}
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            # Ganache tắt giữa chừng — reset
            st.session_state["w3"] = None
            st.session_state["contracts"] = None
            st.session_state["conn_checked"] = False
    else:
        err = st.session_state.get("conn_error")
        if err:
            st.markdown(f"""
            <div style="background:#2a1a0d;border:1px solid #e0a020;border-radius:8px;padding:10px;font-size:11px;color:#e0c060">
            ⚠️ Demo mode<br><small>{str(err)[:90]}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#2a2030;border:1px solid #556;border-radius:8px;padding:10px;font-size:12px;color:#aaa">
            🔌 Chưa kết nối<br><small>Nhấn "Kết nối Ganache"</small>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<small style='color:#556'>v2.1.0 • Hardhat + Web3.py + Streamlit</small>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Tổng quan
# ═══════════════════════════════════════════════════════════════════════════════
if "🏠 Tổng quan" in page:
    st.markdown("# 🏛️ DAO Voting System")
    st.markdown("**Hệ thống Biểu quyết Cổ đông trên Blockchain — Demo v2.1.0**")

    if is_connected():
        w3 = st.session_state["w3"]
        try:
            st.markdown(
                f'<div class="alert-ok">✅ Kết nối Ganache | Block #{w3.eth.block_number} | ChainID: {w3.eth.chain_id} | <b>Dữ liệu thực on-chain</b></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass
    else:
        err = st.session_state.get("conn_error") or "Chưa kết nối Ganache."
        st.markdown(
            f'<div class="alert-warn">🔌 {err}<br><small>Hiển thị dữ liệu demo. Nhấn "Kết nối Ganache" ở sidebar.</small></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    shareholders, sh_live = get_shareholders()
    campaigns, camp_live  = get_campaigns()

    # KPI
    active_camp   = sum(1 for c in campaigns if c["status"] in ("ACTIVE", "COMMIT", "REVEAL"))
    executed_camp = sum(1 for c in campaigns if c["status"] == "EXECUTED")

    card_style  = "background:linear-gradient(135deg,#1a2744,#1e3058);border:1px solid #2a4a8a;border-radius:10px;padding:0 16px;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100px;"
    label_style = "font-size:11px;color:#8899bb;text-transform:uppercase;letter-spacing:1px;line-height:1.3;height:32px;display:flex;align-items:flex-end;justify-content:center;margin-bottom:6px;"
    value_style = "font-size:28px;font-weight:700;color:#4a9eff;line-height:1;"

    # FIX: lấy tổng cung thực từ on-chain
    total_hst = get_total_supply_onchain() if is_connected() else sum(s["hst"] for s in shareholders)
    total_hst_label = f"{total_hst/1_000_000:.0f}M" if total_hst >= 1_000_000 else fmt_num(total_hst)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Tổng cổ đông</div><div style="{value_style}">{len(shareholders)}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Tổng cung HST</div><div style="{value_style}">{total_hst_label}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Chiến dịch mở</div><div style="{value_style}">{active_camp}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Nghị quyết<br>thông qua</div><div style="{value_style}">{executed_camp}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="section-header">📋 Chiến dịch gần đây</div>', unsafe_allow_html=True)

        # Hiển thị demo label khi chưa có live campaign
        display_campaigns = campaigns
        if camp_live and len(campaigns) == 0:
            st.markdown("""
            <div class="dao-card" style="text-align:center;color:#778;padding:40px">
                <div style="font-size:40px;margin-bottom:12px">🗳️</div>
                <div style="font-size:16px;margin-bottom:8px">Chưa có chiến dịch trên chain</div>
                <div style="font-size:13px">Chạy:
                <code style="background:#1a1f2e;padding:4px 8px;border-radius:4px">
                npx hardhat run scripts/setup_campaign.js --network ganache
                </code></div>
            </div>
            """, unsafe_allow_html=True)
            display_campaigns = []

        for c in display_campaigns[:4]:
            total  = c["forVotes"] + c["againstVotes"] + c["abstainVotes"]
            _bar   = vote_bar(c["forVotes"], c["againstVotes"], c["abstainVotes"]) if total > 0 else '<div style="color:#556;font-size:12px">Chưa có phiếu</div>'
            _badge = status_badge(c["status"])
            _cr    = '&nbsp;|&nbsp; 🔒 Commit-Reveal' if c.get("isCommitReveal") else ""
            camp_key = f"#{c['id']} — {c['title']}"

            st.markdown(
                '<div class="dao-card" style="padding-bottom:10px">'
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<b style="color:#eef">#{c["id"]} — {c["title"]}</b>'
                + _badge +
                '</div>'
                f'<div style="font-size:12px;color:#778;margin-bottom:8px">📌 {c["proposalType"]} &nbsp;|&nbsp; ⚙️ {c["mechanism"]}' + _cr + '</div>'
                + _bar +
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Xem chi tiết →", key=f"goto_{c['id']}", use_container_width=True):
                st.session_state["selected_campaign"] = camp_key
                st.session_state["goto_campaign_page"] = True
                st.rerun()

    with col_right:
        st.markdown('<div class="section-header">👥 Phân bổ Token</div>', unsafe_allow_html=True)
        total_sh_hst = sum(s["hst"] for s in shareholders)
        for s in shareholders:
            pct = s["hst"] / total_sh_hst * 100 if total_sh_hst > 0 else 0
            tier_colors = {3: "#ffd700", 2: "#c0c0c0", 1: "#cd7f32", 0: "#8899bb"}
            color = tier_colors.get(s["tier"], "#aaa")
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin:6px 0;padding:8px 12px;background:#1a1f2e;border-radius:8px;border-left:3px solid {color}">
                <div style="flex:1">
                    <div style="font-size:13px;color:#ccd;font-weight:600">{s['name']}</div>
                    <div style="font-size:11px;color:#778">{tier_label(s['tier'])}</div>
                </div>
                <div style="text-align:right">
                    <div style="color:{color};font-weight:700;font-size:13px">{pct:.1f}%</div>
                    <div style="font-size:11px;color:#778">{fmt_num(s['hst'])} HST</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        _src_note = " (on-chain)" if sh_live else " (demo)"
        st.markdown(f"""
        <div style="margin-top:12px;padding:12px;background:#1a1f2e;border-radius:8px;border:1px solid #2a3a5e">
            <div style="font-size:12px;color:#778;margin-bottom:8px">Phân bổ theo Tier{_src_note}</div>
            <div style="display:flex;gap:16px;flex-wrap:wrap">
                <div style="color:#ffd700;font-size:12px">🥇 Sáng lập: 45%</div>
                <div style="color:#c0c0c0;font-size:12px">🥈 Chiến lược: 25%</div>
                <div style="color:#cd7f32;font-size:12px">🥉 Tổ chức: 25%</div>
                <div style="color:#8899bb;font-size:12px">🔵 Nhỏ lẻ: 5%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Cổ đông
# ═══════════════════════════════════════════════════════════════════════════════
elif "👥 Cổ đông" in page:
    st.markdown("# 👥 Danh sách Cổ đông")

    shareholders, sh_live = get_shareholders()

    if sh_live:
        st.markdown('<div class="alert-ok">✅ Dữ liệu on-chain từ Ganache</div>', unsafe_allow_html=True)
    else:
        err = st.session_state.get("conn_error") or "Chưa kết nối"
        st.markdown(f'<div class="alert-warn">🔌 {err} — Hiển thị dữ liệu demo</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Tìm kiếm (tên hoặc địa chỉ)", "")
    with col2:
        tier_filter = st.selectbox("Lọc theo Tier", ["Tất cả", "🥇 Sáng lập (Tier 3)", "🥈 Chiến lược (Tier 2)", "🥉 Tổ chức (Tier 1)", "🔵 Nhỏ lẻ (Tier 0)"])

    tier_map = {"🥇 Sáng lập (Tier 3)": 3, "🥈 Chiến lược (Tier 2)": 2, "🥉 Tổ chức (Tier 1)": 1, "🔵 Nhỏ lẻ (Tier 0)": 0}
    filtered = shareholders
    if search:
        filtered = [s for s in filtered if search.lower() in s["name"].lower() or search.lower() in s["address"].lower()]
    if tier_filter != "Tất cả":
        filtered = [s for s in filtered if s["tier"] == tier_map[tier_filter]]

    st.markdown("""
    <div style="display:grid;grid-template-columns:2fr 2.5fr 1.5fr 1.5fr 1fr 1fr;gap:8px;padding:8px 12px;background:#1a2030;border-radius:8px;margin-top:12px;font-size:11px;color:#778;font-weight:700;letter-spacing:1px">
        <div>TÊN</div><div>ĐỊA CHỈ VÍ</div><div>SỐ DƯ HST</div><div>VOTING POWER</div><div>TIER</div><div>TRẠNG THÁI</div>
    </div>
    """, unsafe_allow_html=True)

    tier_colors = {3: "#ffd700", 2: "#c0c0c0", 1: "#cd7f32", 0: "#8899bb"}
    for s in filtered:
        color = tier_colors.get(s["tier"], "#aaa")
        status_html = '<span style="color:#2ddc64">● Hoạt động</span>' if s.get("active", True) else '<span style="color:#dc2d2d">✕ Đã khóa</span>'
        vp = s.get("vp", s["hst"])
        short_addr = s["address"][:10] + "..." + s["address"][-6:]
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:2fr 2.5fr 1.5fr 1.5fr 1fr 1fr;gap:8px;padding:12px;background:#1a1f2e;border-radius:8px;margin:4px 0;border:1px solid #2a2f3e;font-size:13px;align-items:center">
            <div style="color:#ccd;font-weight:600">{s['name']}</div>
            <div style="color:#778;font-family:monospace;font-size:11px">{short_addr}</div>
            <div style="color:{color};font-weight:700">{fmt_num(s['hst'])}</div>
            <div style="color:#4a9eff">{fmt_num(vp)}</div>
            <div style="color:{color}">{tier_label(s['tier'])}</div>
            <div>{status_html}</div>
        </div>
        """, unsafe_allow_html=True)

    if not filtered:
        st.info("Không tìm thấy cổ đông phù hợp.")

    # Tra cứu cá nhân
    st.markdown("---")
    st.markdown('<div class="section-header">🔍 Tra cứu Cổ đông</div>', unsafe_allow_html=True)
    wallet_input = st.text_input("Nhập địa chỉ ví (0x...)", placeholder="0x1234...abcd")
    if wallet_input:
        if is_connected():
            contracts = st.session_state["contracts"]
            info = get_shareholder_info(contracts["registry"], wallet_input)
            if info:
                vp  = get_voting_power(contracts["hst"], wallet_input)
                bal = get_token_balance(contracts["hst"], wallet_input)
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Số dư HST", fmt_hst(bal))
                with col2: st.metric("Voting Power", fmt_hst(vp))
                with col3: st.metric("Tier", tier_label(info["tier"]))
                st.json(info)
            else:
                st.markdown('<div class="alert-err">❌ Địa chỉ chưa đăng ký trong Registry</div>', unsafe_allow_html=True)
        else:
            st.info("Kết nối Ganache để tra cứu dữ liệu thực.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Chiến dịch
# ═══════════════════════════════════════════════════════════════════════════════
elif "🗳️ Chiến dịch" in page:
    st.markdown("# 🗳️ Chiến dịch Biểu quyết")

    campaigns, camp_live = get_campaigns()

    if camp_live:
        st.markdown('<div class="alert-ok">✅ Dữ liệu on-chain từ Ganache</div>', unsafe_allow_html=True)
    else:
        err = st.session_state.get("conn_error") or "Chưa kết nối"
        st.markdown(f'<div class="alert-warn">🔌 {err} — Hiển thị dữ liệu demo</div>', unsafe_allow_html=True)

    # FIX: Khi đã kết nối nhưng chưa có campaign → hướng dẫn + cho xem demo riêng
    if camp_live and len(campaigns) == 0:
        st.markdown("""
        <div class="dao-card" style="text-align:center;color:#778;padding:60px 40px">
            <div style="font-size:48px;margin-bottom:16px">🗳️</div>
            <div style="font-size:18px;color:#ccd;margin-bottom:12px">Chưa có chiến dịch nào trên blockchain</div>
            <div style="font-size:14px;margin-bottom:20px">
                Contracts đã deploy thành công nhưng chưa có campaign được tạo.<br>
                Chạy lệnh sau để tạo 4 chiến dịch demo:
            </div>
            <div style="background:#1a1f2e;padding:16px;border-radius:8px;font-family:monospace;font-size:13px;color:#4a9eff;text-align:left;display:inline-block">
                npx hardhat run scripts/setup_campaign.js --network ganache
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 👀 Xem trước dữ liệu Demo")
        st.markdown("*Dữ liệu bên dưới là demo để minh hoạ giao diện:*")
        campaigns = DEMO_CAMPAIGNS   # fallback cho phần selectbox bên dưới

    # Campaign selector
    if not campaigns:
        st.info("Không có dữ liệu chiến dịch.")
        st.stop()

    campaign_options = {f"#{c['id']} — {c['title']}": c for c in campaigns}
    option_list = list(campaign_options.keys())
    _preselect  = st.session_state.pop("selected_campaign", None)
    _default_idx = option_list.index(_preselect) if _preselect and _preselect in option_list else 0
    selected_key = st.selectbox("Chọn chiến dịch", option_list, index=_default_idx)
    c = campaign_options[selected_key]

    st.markdown("---")

    col_info, col_status = st.columns([3, 1])
    with col_info:
        st.markdown(f"## #{c['id']} — {c['title']}")
        st.markdown(f"*{c['description']}*")
    with col_status:
        _cr_div = '<div style="margin-top:4px">🔒 Commit-Reveal</div>' if c.get("isCommitReveal") else ""
        st.markdown(
            '<div style="text-align:center;padding:20px;background:#1a1f2e;border-radius:12px;margin-top:10px">'
            + status_badge(c["status"]) +
            f'<div style="margin-top:10px;font-size:12px;color:#778">'
            f'<div>📌 {c["proposalType"]}</div>'
            f'<div style="margin-top:4px">⚙️ {c["mechanism"]}</div>'
            + _cr_div +
            '</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    for_v = c["forVotes"]
    ag_v  = c["againstVotes"]
    abs_v = c["abstainVotes"]
    total = for_v + ag_v + abs_v

    # FIX: lấy total supply thực từ on-chain
    total_hst_supply = get_total_supply_onchain()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ FOR", fmt_hst(for_v), f"{for_v/total*100:.1f}%" if total > 0 else "0%")
    with col2:
        st.metric("❌ AGAINST", fmt_hst(ag_v), f"{ag_v/total*100:.1f}%" if total > 0 else "0%")
    with col3:
        st.metric("⬜ ABSTAIN", fmt_hst(abs_v), f"{abs_v/total*100:.1f}%" if total > 0 else "0%")
    with col4:
        part_pct = total / total_hst_supply * 100 if total_hst_supply > 0 else 0
        st.metric("📊 Tham gia", f"{part_pct:.1f}%", f"Ngưỡng: {c['quorumBps']:.0f}%")

    st.markdown("**Kết quả biểu quyết:**")
    st.markdown(vote_bar(for_v, ag_v, abs_v), unsafe_allow_html=True)
    st.markdown(f"""
    <div style="display:flex;gap:20px;margin-top:6px;font-size:12px;color:#778">
        <span style="color:#2ddc64">■ FOR</span>
        <span style="color:#dc2d2d">■ AGAINST</span>
        <span style="color:#445">■ ABSTAIN</span>
        <span style="margin-left:auto">Ngưỡng thông qua: <b style="color:#4a9eff">{c['passThreshold']:.0f}%</b></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    if total > 0:
        decisive = for_v + ag_v
        pass_pct = for_v / decisive * 100 if decisive > 0 else 0
        quorum_ok = part_pct >= c["quorumBps"]
        pass_ok   = pass_pct >= c["passThreshold"]
        if quorum_ok and pass_ok:
            st.markdown(f'<div class="alert-ok">✅ Dự thảo ĐẠT — FOR: {pass_pct:.1f}% ≥ {c["passThreshold"]:.0f}% | Quorum: {part_pct:.1f}% ≥ {c["quorumBps"]:.0f}%</div>', unsafe_allow_html=True)
        elif not quorum_ok:
            st.markdown(f'<div class="alert-warn">⚠️ CHƯA ĐỦ quorum — Tham gia: {part_pct:.1f}% < {c["quorumBps"]:.0f}%</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-err">❌ Dự thảo KHÔNG ĐẠT — FOR: {pass_pct:.1f}% < {c["passThreshold"]:.0f}%</div>', unsafe_allow_html=True)
    else:
        if c.get("isCommitReveal"):
            st.markdown('<div class="alert-warn">🔒 Đang trong giai đoạn Commit-Reveal — phiếu chưa được công khai</div>', unsafe_allow_html=True)
        else:
            st.info("Chưa có phiếu nào được cast")

    if c.get("isCommitReveal"):
        st.markdown("---")
        st.markdown('<div class="section-header">🔒 Quy trình Commit-Reveal (Bỏ phiếu kín)</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="dao-card">
            <b style="color:#4a9eff">Giai đoạn 1: COMMIT</b><br><br>
            <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-text">Tạo <code>hash = keccak256(vote || salt || address)</code></div></div>
            <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-text">Submit <b>hash</b> lên blockchain (không lộ phiếu)</div></div>
            <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-text">Deadline: 7 ngày sau khi mở</div></div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="dao-card">
            <b style="color:#2ddc64">Giai đoạn 2: REVEAL</b><br><br>
            <div class="timeline-item"><div class="timeline-dot" style="background:#2ddc64"></div><div class="timeline-text">Public <code>vote + salt</code> gốc</div></div>
            <div class="timeline-item"><div class="timeline-dot" style="background:#2ddc64"></div><div class="timeline-text">Contract verify hash → ghi nhận phiếu</div></div>
            <div class="timeline-item"><div class="timeline-dot" style="background:#2ddc64"></div><div class="timeline-text">Deadline: 3 ngày sau commit</div></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("**🔧 Công cụ tạo Commit Hash (Demo)**")
        col1, col2, col3 = st.columns(3)
        with col1: vote_choice = st.selectbox("Phiếu", ["FOR (0)", "AGAINST (1)", "ABSTAIN (2)"])
        with col2: salt_val = st.text_input("Salt (bí mật)", value="my_secret_salt_123")
        with col3: st.text_input("Hash demo", value=f"0x{hash(vote_choice+salt_val) & 0xFFFFFFFFFFFFFFFF:016x}...", disabled=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Phân tích
# ═══════════════════════════════════════════════════════════════════════════════
elif "📊 Phân tích" in page:
    st.markdown("# 📊 Phân tích & So sánh Cơ chế")

    tab1, tab2, tab3 = st.tabs(["⚖️ Linear vs Quadratic vs Equal", "📈 Tỷ lệ tham gia", "🔬 Kịch bản ID-103"])

    with tab1:
        st.markdown("### So sánh Voting Weight — 3 Cơ chế")
        shareholders, sh_live = get_shareholders()
        shareholders_data = {s["name"]: int(s["hst"]) for s in shareholders}

        names    = list(shareholders_data.keys())
        balances = list(shareholders_data.values())
        quadratic_w = [int(math.sqrt(b)) for b in balances]
        total_lin = sum(balances)
        total_qua = sum(quadratic_w)
        lin_pct = [b / total_lin * 100 for b in balances] if total_lin > 0 else [0]*len(balances)
        qua_pct = [b / total_qua * 100 for b in quadratic_w] if total_qua > 0 else [0]*len(balances)
        eq_pct  = [100 / len(names)] * len(names) if names else []

        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr;gap:6px;padding:8px 12px;background:#1a2030;border-radius:8px;font-size:11px;color:#778;font-weight:700;">
            <div>CỔ ĐÔNG</div><div>TOKEN</div><div>LIN weight</div><div>LIN %</div><div>QUAD weight</div><div>QUAD %</div><div>EQUAL %</div>
        </div>
        """, unsafe_allow_html=True)

        tier_colors_list = ["#ffd700","#c0c0c0","#cd7f32","#cd7f32","#8899bb"]
        for i, name in enumerate(names):
            color = tier_colors_list[i] if i < len(tier_colors_list) else "#8899bb"
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr;gap:6px;padding:10px 12px;background:#1a1f2e;border-radius:8px;margin:3px 0;border-left:3px solid {color};font-size:13px;align-items:center">
                <div style="color:#ccd;font-weight:600">{name}</div>
                <div style="color:{color}">{fmt_num(balances[i])}</div>
                <div style="color:#4a9eff">{fmt_num(balances[i])}</div>
                <div style="color:#4a9eff;font-weight:700">{lin_pct[i]:.1f}%</div>
                <div style="color:#2ddc64">{fmt_num(quadratic_w[i])}</div>
                <div style="color:#2ddc64;font-weight:700">{qua_pct[i]:.1f}%</div>
                <div style="color:#e0a040;font-weight:700">{eq_pct[i]:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        **🔑 Nhận xét:**
        - **Linear**: Cổ đông lớn (45% token) giữ 45% voting power → ưu thế tuyệt đối
        - **Quadratic**: √token → giảm mạnh khoảng cách quyền lực giữa cổ đông lớn và nhỏ
        - **Equal**: Mỗi cổ đông 1 phiếu → hoàn toàn dân chủ, phù hợp bầu nhân sự
        """)

    with tab2:
        st.markdown("### Tỷ lệ tham gia theo Chiến dịch")
        campaigns, _ = get_campaigns()
        campaign_display = campaigns if campaigns else DEMO_CAMPAIGNS

        # FIX: lấy total supply thực từ on-chain
        _supply = get_total_supply_onchain()

        for c in campaign_display:
            total = c["forVotes"] + c["againstVotes"] + c["abstainVotes"]
            part  = total / _supply * 100 if _supply > 0 else 0
            quorum_ok = part >= c["quorumBps"]
            bar_pct   = min(part, 100)
            color     = "#2ddc64" if quorum_ok else "#e0a020"
            _quorum_label = f'<span style="color:{color}">{"✅ Quorum đạt" if quorum_ok and total > 0 else ("⚠️ Chưa đủ quorum" if not quorum_ok else "Chưa có phiếu")}</span>'
            decisive = c["forVotes"] + c["againstVotes"]
            for_pct  = c["forVotes"] / decisive * 100 if decisive > 0 else 0

            st.markdown(
                '<div class="dao-card" style="margin:8px 0">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
                f'<b style="color:#eef">#{c["id"]} {c["title"][:40]}</b>'
                + status_badge(c["status"]) +
                '</div>'
                f'<div style="display:flex;gap:16px;font-size:12px;color:#778;margin-bottom:8px">'
                f'<span>📌 {c["proposalType"]}</span>'
                f'<span>Quorum: {c["quorumBps"]:.0f}%</span>'
                f'<span>FOR: {for_pct:.1f}%</span></div>'
                f'<div style="background:#1a1f2e;border-radius:6px;height:14px;overflow:hidden">'
                f'<div style="width:{bar_pct}%;background:linear-gradient(90deg,{color}88,{color});height:100%;border-radius:6px"></div></div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px">'
                f'<span style="color:{color}">Tham gia: {part:.1f}%</span>'
                + _quorum_label +
                '</div></div>',
                unsafe_allow_html=True,
            )

    with tab3:
        st.markdown("### 🔬 ID-103: Linear vs Quadratic — CEO Election")
        st.markdown("*Kịch bản: Chủ tịch HĐQT bỏ FOR, các cổ đông nhỏ hơn bỏ AGAINST*")

        votes = {
            "Chủ tịch HĐQT":       ("FOR",     4_500_000),
            "Quỹ phát triển":      ("AGAINST",  2_500_000),
            "Cổ đông A (Tổ chức)": ("AGAINST",  1_500_000),
            "Cổ đông B (Tổ chức)": ("AGAINST",  1_000_000),
            "Cổ đông C (Nhỏ lẻ)":  ("FOR",        500_000),
        }
        lin_for = sum(b for v, b in votes.values() if v == "FOR")
        lin_ag  = sum(b for v, b in votes.values() if v == "AGAINST")
        qua_for = sum(int(math.sqrt(b)) for v, b in votes.values() if v == "FOR")
        qua_ag  = sum(int(math.sqrt(b)) for v, b in votes.values() if v == "AGAINST")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Linear:**")
            lin_total = lin_for + lin_ag
            st.markdown(vote_bar(lin_for, lin_ag, 0), unsafe_allow_html=True)
            lin_pass = lin_for / lin_total * 100 if lin_total > 0 else 0
            result = "✅ ĐẠT" if lin_pass >= 66 else "❌ KHÔNG ĐẠT"
            st.markdown(f"FOR: {lin_pass:.1f}% — **{result}** (ngưỡng 66%)")
        with col2:
            st.markdown("**Quadratic:**")
            qua_total = qua_for + qua_ag
            st.markdown(vote_bar(qua_for, qua_ag, 0), unsafe_allow_html=True)
            qua_pass = qua_for / qua_total * 100 if qua_total > 0 else 0
            result = "✅ ĐẠT" if qua_pass >= 66 else "❌ KHÔNG ĐẠT"
            st.markdown(f"FOR: {qua_pass:.1f}% — **{result}** (ngưỡng 66%)")

        st.info("💡 Kết quả khác nhau giữa 2 cơ chế — Quadratic bảo vệ quyền lợi cổ đông nhỏ hơn.")

        # Bảng chi tiết
        st.markdown("---")
        st.markdown("**Chi tiết từng cổ đông:**")
        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;gap:6px;padding:8px 12px;background:#1a2030;border-radius:8px;font-size:11px;color:#778;font-weight:700;">
            <div>CỔ ĐÔNG</div><div>PHIẾU</div><div>TOKEN</div><div>WEIGHT Linear</div><div>WEIGHT Quadratic</div>
        </div>
        """, unsafe_allow_html=True)
        for name, (vote_v, bal) in votes.items():
            v_color = "#2ddc64" if vote_v == "FOR" else "#dc4a4a"
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;gap:6px;padding:10px 12px;background:#1a1f2e;border-radius:8px;margin:3px 0;font-size:13px;align-items:center">
                <div style="color:#ccd">{name}</div>
                <div style="color:{v_color};font-weight:700">{vote_v}</div>
                <div style="color:#aaa">{fmt_num(bal)}</div>
                <div style="color:#4a9eff">{fmt_num(bal)}</div>
                <div style="color:#2ddc64">{fmt_num(int(math.sqrt(bal)))}</div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Hướng dẫn
# ═══════════════════════════════════════════════════════════════════════════════
elif "⚙️ Hướng dẫn" in page:
    st.markdown("# ⚙️ Hướng dẫn Deploy & Sử dụng")

    tab1, tab2, tab3 = st.tabs(["🚀 Cách Deploy", "🎮 Cách Tương tác", "📐 Kiến trúc"])

    with tab1:
        st.markdown("""
        ## 🚀 Các bước Deploy từ đầu

        ### 1. Cài đặt môi trường
        ```bash
        npm install
        pip install -r requirements.txt
        ```

        ### 2. Mở Ganache
        ```
        Ganache UI: port 7545, Chain ID 1337
        ```

        ### 3. Compile Contracts
        ```bash
        npx hardhat compile
        ```

        ### 4. Chạy Unit Tests
        ```bash
        npx hardhat test
        ```

        ### 5. Deploy lên Ganache
        ```bash
        npx hardhat run scripts/setup_demo.js --network ganache
        ```

        ### 6. Tạo chiến dịch demo
        ```bash
        npx hardhat run scripts/setup_campaign.js --network ganache
        ```

        ### 7. Chạy Dashboard
        ```bash
        $env:PYTHONUTF8=1
        streamlit run dashboard/app.py --server.fileWatcherType none
        ```
        """)

    with tab2:
        st.markdown("""
        ## 🎮 Cách Tương tác

        ### Qua Hardhat Console
        ```javascript
        npx hardhat console --network ganache

        const gov = await ethers.getContractAt("GovernanceContract", "0x...")
        // Tạo campaign: title, description, proposalType(0-2), mechanism(0-2), commitReveal
        await gov.createCampaign("Tiêu đề", "Mô tả", 0, 0, false)
        // Bỏ phiếu: campaignId, option(0=FOR, 1=AGAINST, 2=ABSTAIN)
        await gov.connect(signer).castVote(1, 0)
        ```

        ### Qua Python Web3
        ```python
        from utils.web3_helpers import connect_web3, get_all_contracts
        w3 = connect_web3()
        contracts = get_all_contracts(w3)
        campaigns = get_all_campaigns(contracts["gov"])
        ```

        ### Commit-Reveal (bỏ phiếu kín)
        ```javascript
        const salt = ethers.randomBytes(32)
        const hash = ethers.keccak256(
            ethers.solidityPacked(["uint8","bytes32","address"], [voteOption, salt, voterAddr])
        )
        await gov.connect(voter).commitVote(campaignId, hash)
        // Sau khi transitionToReveal():
        await gov.connect(voter).revealVote(campaignId, voteOption, salt)
        ```
        """)

    with tab3:
        st.markdown("""
        ## 📐 Kiến trúc Hệ thống
        ```
        Streamlit Dashboard (app.py)
               ↕ web3.py
        utils/web3_helpers.py
               ↕ JSON-RPC
        Ganache (EVM)
          ├── HSTToken (ERC20Votes)
          ├── ShareholderRegistry
          ├── GovernanceContract
          └── HSTTimelockController
        ```

        ### Luồng Biểu quyết
        1. Admin deploy + đăng ký cổ đông (setup_demo.js)
        2. Cổ đông self-delegate để activate voting power
        3. Campaign Manager tạo chiến dịch (setup_campaign.js)
        4. Cổ đông bỏ phiếu trong thời hạn
        5. finalizeCampaign() sau deadline → EXECUTED hoặc DEFEATED
        6. Timelock thực thi nghị quyết đã pass
        """)

        st.markdown("### 🗳️ Các loại chiến dịch")
        data = [
            {"Loại": "Routine", "Ngưỡng": "> 50%", "Quorum": "10%", "Thời gian": "7 ngày",  "Ví dụ": "Ngân sách, dự án nhỏ"},
            {"Loại": "Major",   "Ngưỡng": "> 66%", "Quorum": "20%", "Thời gian": "14 ngày", "Ví dụ": "Cổ tức, bầu nhân sự"},
            {"Loại": "M&A",     "Ngưỡng": "> 75%", "Quorum": "30%", "Thời gian": "21 ngày", "Ví dụ": "Sáp nhập, bán công ty"},
        ]
        for d in data:
            color = {"Routine": "#4a9eff", "Major": "#e0a020", "M&A": "#dc4a4a"}[d["Loại"]]
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 2fr;gap:8px;padding:10px 14px;background:#1a1f2e;border-radius:8px;margin:4px 0;border-left:3px solid {color}">
                <div style="color:{color};font-weight:700">{d["Loại"]}</div>
                <div style="color:#eef">{d["Ngưỡng"]}</div>
                <div style="color:#eef">{d["Quorum"]}</div>
                <div style="color:#eef">{d["Thời gian"]}</div>
                <div style="color:#778">{d["Ví dụ"]}</div>
            </div>
            """, unsafe_allow_html=True)