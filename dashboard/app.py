"""
dashboard/app.py
─────────────────
Phase 4 — Streamlit Dashboard cho DAO Voting System
Chạy: streamlit run dashboard/app.py
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
    sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
    from web3_helpers import (
        connect_web3, get_all_contracts,
        get_shareholder_info, get_voting_power, get_token_balance,
        get_all_campaigns, get_campaign_data, get_vote_participation,
        load_addresses,
    )
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

# ─── CSS Styling ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b27 !important; border-right: 1px solid #2a2f3e; }

/* Scrollbar lớn hơn, dễ kéo */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #1a1f2e; border-radius: 6px; }
::-webkit-scrollbar-thumb { background: #3a4a6a; border-radius: 6px; border: 2px solid #1a1f2e; }
::-webkit-scrollbar-thumb:hover { background: #4a7afa; }

/* Nút Xem chi tiết — sát card, nhỏ gọn */
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
    line-height: 1.6 !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #1e2d4a !important;
    border-color: #4a7afa !important;
    color: #6ab4ff !important;
}

/* Cards */
.dao-card {
    background: linear-gradient(135deg, #1a1f2e 0%, #1e2535 100%);
    border: 1px solid #2a3a5e;
    border-radius: 12px;
    padding: 20px;
    margin: 8px 0;
    transition: border-color 0.2s;
}
.dao-card:hover { border-color: #4a7afa; }

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1a2744 0%, #1e3058 100%);
    border: 1px solid #2a4a8a;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    height: 110px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.metric-value { font-size: 28px; font-weight: 700; color: #4a9eff; margin: 4px 0; }
.metric-label { font-size: 12px; color: #8899bb; text-transform: uppercase; letter-spacing: 1px; line-height: 1.3; }

/* Status badges */
.badge-active   { background:#0d3b1a; color:#2ddc64; border:1px solid #2ddc64; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-draft    { background:#2a2d1a; color:#e0c040; border:1px solid #e0c040; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-executed { background:#1a2d4a; color:#4a9eff; border:1px solid #4a9eff; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-defeated { background:#3b0d0d; color:#ff4a4a; border:1px solid #ff4a4a; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-other    { background:#2a2a3a; color:#aaaacc; border:1px solid #aaaacc; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }

/* Progress bar */
.vote-bar-wrap  { background:#1a1f2e; border-radius:8px; height:22px; overflow:hidden; display:flex; }
.vote-bar-for   { background:linear-gradient(90deg,#1a7a3a,#2ddc64); height:100%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:white; }
.vote-bar-ag    { background:linear-gradient(90deg,#7a1a1a,#dc2d2d); height:100%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:white; }
.vote-bar-abs   { background:#2a2d40; height:100%; }

/* Tier badges */
.tier-3 { color:#ffd700; font-weight:700; }
.tier-2 { color:#c0c0c0; font-weight:700; }
.tier-1 { color:#cd7f32; font-weight:700; }
.tier-0 { color:#aaaacc; }

/* Section headers */
.section-header {
    font-size:18px; font-weight:700; color:#4a9eff;
    border-bottom: 1px solid #2a3a5e; padding-bottom:8px; margin: 20px 0 12px 0;
}

/* Timeline */
.timeline-item { display:flex; gap:12px; margin:8px 0; }
.timeline-dot  { width:10px; height:10px; border-radius:50%; background:#4a9eff; margin-top:5px; flex-shrink:0; }
.timeline-text { color:#ccd; font-size:13px; }

/* Alert */
.alert-warn { background:#2a2010; border:1px solid #e0a020; border-radius:8px; padding:12px 16px; color:#e0c060; font-size:13px; }
.alert-ok   { background:#0d2a1a; border:1px solid #2ddc64; border-radius:8px; padding:12px 16px; color:#4dfc84; font-size:13px; }
.alert-err  { background:#2a0d0d; border:1px solid #dc2d2d; border-radius:8px; padding:12px 16px; color:#fc4d4d; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar Navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏛️ DAO Voting System")
    st.markdown("**Blockchain Governance Platform**")
    st.markdown("---")

    # Handle redirect from "Xem chi tiết" button on Tổng quan
    _default_page_idx = 0
    if st.session_state.get("goto_campaign_page"):
        _default_page_idx = 2
        st.session_state["goto_campaign_page"] = False

    page = st.radio(
        "Điều hướng",
        ["🏠 Tổng quan", "👥 Cổ đông", "🗳️ Chiến dịch", "📊 Phân tích", "⚙️ Hướng dẫn"],
        index=_default_page_idx,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Connection settings
    st.markdown("**⚙️ Kết nối**")
    rpc_url = st.text_input("RPC URL", value="http://127.0.0.1:7545", key="rpc")

    if st.button("🔌 Kết nối Ganache", use_container_width=True):
        st.session_state["connect_attempt"] = True

    st.markdown("---")
    st.markdown("<small style='color:#556'>v2.1.0 • Hardhat + Web3.py + Streamlit</small>", unsafe_allow_html=True)


# ─── Connection State ─────────────────────────────────────────────────────────
def try_connect():
    if not WEB3_AVAILABLE:
        return None, None, "⚠️ web3 chưa cài: pip install web3"
    try:
        w3 = connect_web3(st.session_state.get("rpc", "http://127.0.0.1:7545"))
        contracts = get_all_contracts(w3)
        return w3, contracts, None
    except FileNotFoundError:
        return None, None, "📄 Chưa deploy contract. Chạy: npx hardhat run scripts/setup_demo.js"
    except ConnectionError as e:
        return None, None, str(e)
    except Exception as e:
        return None, None, f"Lỗi: {e}"


# ─── Demo Data (khi chưa kết nối) ────────────────────────────────────────────
DEMO_SHAREHOLDERS = [
    {"name": "Chủ tịch HĐQT",      "address": "0xAcc0...0001", "hst": 4_500_000, "vp": 4_500_000, "tier": 3, "active": True},
    {"name": "Quỹ phát triển",      "address": "0xAcc0...0002", "hst": 2_500_000, "vp": 2_500_000, "tier": 2, "active": True},
    {"name": "Cổ đông A (Tổ chức)","address": "0xAcc0...0003", "hst": 1_500_000, "vp": 1_500_000, "tier": 1, "active": True},
    {"name": "Cổ đông B (Tổ chức)","address": "0xAcc0...0004", "hst": 1_000_000, "vp": 1_000_000, "tier": 1, "active": True},
    {"name": "Cổ đông C (Nhỏ lẻ)", "address": "0xAcc0...0005", "hst":   500_000, "vp":   500_000, "tier": 0, "active": True},
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
        "forVotes": 2_236,  "againstVotes": 1_000, "abstainVotes": 200,
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
    labels = {3:"🥇 Sáng lập", 2:"🥈 Chiến lược", 1:"🥉 Tổ chức", 0:"🔵 Nhỏ lẻ"}
    return labels.get(t, "Unknown")

def status_badge(s):
    if s == "ACTIVE":  return '<span class="badge-active">● ACTIVE</span>'
    if s == "EXECUTED":return '<span class="badge-executed">✓ EXECUTED</span>'
    if s == "DEFEATED":return '<span class="badge-defeated">✗ DEFEATED</span>'
    if s == "DRAFT":   return '<span class="badge-draft">○ DRAFT</span>'
    if s == "COMMIT":  return '<span class="badge-other">🔒 COMMIT</span>'
    if s == "REVEAL":  return '<span class="badge-other">👁 REVEAL</span>'
    return f'<span class="badge-other">{s}</span>'

def vote_bar(for_v, against_v, abstain_v):
    total = for_v + against_v + abstain_v
    if total == 0: return '<div class="vote-bar-wrap"><div style="width:100%;background:#2a2f3e"></div></div>'
    fp = for_v / total * 100
    ap = against_v / total * 100
    sp = abstain_v / total * 100
    return f"""
    <div class="vote-bar-wrap">
        <div class="vote-bar-for"  style="width:{fp:.1f}%">{fp:.0f}%</div>
        <div class="vote-bar-ag"   style="width:{ap:.1f}%">{ap:.0f}%</div>
        <div class="vote-bar-abs"  style="width:{sp:.1f}%"></div>
    </div>"""

def calc_quadratic(balances):
    """Tính voting power theo Quadratic"""
    return {k: int(math.sqrt(v)) for k, v in balances.items()}


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Tổng quan
# ═══════════════════════════════════════════════════════════════════════════════
if "🏠 Tổng quan" in page:
    st.markdown("# 🏛️ DAO Voting System")
    st.markdown("**Hệ thống Biểu quyết Cổ đông trên Blockchain — Demo v2.1.0**")

    # Connection status
    w3, contracts, err = try_connect()
    if err:
        st.markdown(f'<div class="alert-warn">🔌 {err}<br><small>Đang hiển thị dữ liệu demo.</small></div>', unsafe_allow_html=True)
        is_live = False
    else:
        st.markdown(f'<div class="alert-ok">✅ Kết nối Ganache thành công | Block #{w3.eth.block_number} | ChainID: {w3.eth.chain_id}</div>', unsafe_allow_html=True)
        is_live = True

    st.markdown("---")

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    shareholders = DEMO_SHAREHOLDERS
    campaigns    = DEMO_CAMPAIGNS

    if is_live:
        try:
            from web3_helpers import get_all_campaigns
            campaigns = get_all_campaigns(contracts["gov"])
        except: pass

    active_camp  = sum(1 for c in campaigns if c["status"] in ("ACTIVE","COMMIT","REVEAL"))
    executed_camp= sum(1 for c in campaigns if c["status"] == "EXECUTED")

    card_style = "background:linear-gradient(135deg,#1a2744,#1e3058);border:1px solid #2a4a8a;border-radius:10px;padding:0 16px;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100px;box-sizing:border-box;"
    label_style = "font-size:11px;color:#8899bb;text-transform:uppercase;letter-spacing:1px;line-height:1.3;height:32px;display:flex;align-items:flex-end;justify-content:center;margin-bottom:6px;"
    value_style = "font-size:28px;font-weight:700;color:#4a9eff;line-height:1;height:34px;display:flex;align-items:center;justify-content:center;"
    with col1:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Tổng cổ đông</div><div style="{value_style}">{len(shareholders)}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Tổng cung HST</div><div style="{value_style}">10M</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Chiến dịch mở</div><div style="{value_style}">{active_camp}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div style="{card_style}"><div style="{label_style}">Nghị quyết<br>thông qua</div><div style="{value_style}">{executed_camp}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="section-header">📋 Chiến dịch gần đây</div>', unsafe_allow_html=True)
        for c in campaigns[:4]:
            total = c["forVotes"] + c["againstVotes"] + c["abstainVotes"]
            campaign_key = f"#{c['id']} — {c['title']}"
            _bar_html = vote_bar(c['forVotes'], c['againstVotes'], c['abstainVotes']) if total > 0 else '<div style="color:#556;font-size:12px">Chưa có phiếu</div>'
            _badge_html = status_badge(c['status'])
            _commit_html = '&nbsp;|&nbsp; 🔒 Commit-Reveal' if c.get('isCommitReveal') else ''
            st.markdown(
                '<div class="dao-card" style="padding-bottom:10px">'
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<b style="color:#eef">#{c["id"]} — {c["title"]}</b>'
                + _badge_html +
                '</div>'
                f'<div style="font-size:12px;color:#778;margin-bottom:8px">📌 {c["proposalType"]} &nbsp;|&nbsp; ⚙️ {c["mechanism"]}' + _commit_html + '</div>'
                + _bar_html +
                '</div>',
                unsafe_allow_html=True
            )
            if st.button("Xem chi tiết →", key=f"goto_{c['id']}", use_container_width=True):
                st.session_state["selected_campaign"] = campaign_key
                st.session_state["goto_campaign_page"] = True
                st.rerun()

    with col_right:
        st.markdown('<div class="section-header">👥 Phân bổ Token</div>', unsafe_allow_html=True)
        total_hst = sum(s["hst"] for s in shareholders)
        for s in shareholders:
            pct = s["hst"] / total_hst * 100 if total_hst > 0 else 0
            tier_colors = {3:"#ffd700", 2:"#c0c0c0", 1:"#cd7f32", 0:"#8899bb"}
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

        # Pie-like summary
        st.markdown(f"""
        <div style="margin-top:12px;padding:12px;background:#1a1f2e;border-radius:8px;border:1px solid #2a3a5e">
            <div style="font-size:12px;color:#778;margin-bottom:8px">Phân bổ theo Tier</div>
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

    w3, contracts, err = try_connect()
    is_live = not bool(err)
    if err:
        st.markdown(f'<div class="alert-warn">🔌 {err}</div>', unsafe_allow_html=True)

    shareholders = DEMO_SHAREHOLDERS

    # Filters
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Tìm kiếm cổ đông (tên hoặc địa chỉ)", "")
    with col2:
        tier_filter = st.selectbox("Lọc theo Tier", ["Tất cả", "🥇 Sáng lập (Tier 3)", "🥈 Chiến lược (Tier 2)", "🥉 Tổ chức (Tier 1)", "🔵 Nhỏ lẻ (Tier 0)"])

    # Filter
    tier_map = {"🥇 Sáng lập (Tier 3)": 3, "🥈 Chiến lược (Tier 2)": 2, "🥉 Tổ chức (Tier 1)": 1, "🔵 Nhỏ lẻ (Tier 0)": 0}
    filtered = shareholders
    if search:
        filtered = [s for s in filtered if search.lower() in s["name"].lower() or search.lower() in s["address"].lower()]
    if tier_filter != "Tất cả":
        t = tier_map[tier_filter]
        filtered = [s for s in filtered if s["tier"] == t]

    # Table header
    st.markdown("""
    <div style="display:grid;grid-template-columns:2fr 2.5fr 1.5fr 1.5fr 1fr 1fr;gap:8px;padding:8px 12px;background:#1a2030;border-radius:8px;margin-top:12px;font-size:11px;color:#778;font-weight:700;letter-spacing:1px">
        <div>TÊN</div><div>ĐỊA CHỈ VÍ</div><div>SỐ DƯ HST</div><div>VOTING POWER</div><div>TIER</div><div>TRẠNG THÁI</div>
    </div>
    """, unsafe_allow_html=True)

    total_hst = sum(s["hst"] for s in shareholders)
    tier_colors = {3:"#ffd700", 2:"#c0c0c0", 1:"#cd7f32", 0:"#8899bb"}

    for s in filtered:
        color = tier_colors.get(s["tier"], "#aaa")
        status_html = '<span style="color:#2ddc64">● Hoạt động</span>' if s["active"] else '<span style="color:#dc2d2d">✕ Đã khóa</span>'
        vp = s.get("vp", s["hst"])
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:2fr 2.5fr 1.5fr 1.5fr 1fr 1fr;gap:8px;padding:12px;background:#1a1f2e;border-radius:8px;margin:4px 0;border:1px solid #2a2f3e;font-size:13px;align-items:center">
            <div style="color:#ccd;font-weight:600">{s['name']}</div>
            <div style="color:#778;font-family:monospace;font-size:11px">{s['address']}</div>
            <div style="color:{color};font-weight:700">{fmt_num(s['hst'])}</div>
            <div style="color:#4a9eff">{fmt_num(vp)}</div>
            <div style="color:{color}">{tier_label(s['tier'])}</div>
            <div>{status_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # Lookup individual
    st.markdown("---")
    st.markdown('<div class="section-header">🔍 Tra cứu Cổ đông</div>', unsafe_allow_html=True)
    wallet_input = st.text_input("Nhập địa chỉ ví (0x...)", placeholder="0x1234...abcd")
    if wallet_input and is_live:
        info = get_shareholder_info(contracts["registry"], wallet_input)
        if info:
            vp = get_voting_power(contracts["hst"], wallet_input)
            bal = get_token_balance(contracts["hst"], wallet_input)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Số dư HST", fmt_hst(bal))
            with col2: st.metric("Voting Power", fmt_hst(vp))
            with col3: st.metric("Tier", tier_label(info["tier"]))
            st.json(info)
        else:
            st.markdown('<div class="alert-err">❌ Địa chỉ chưa đăng ký trong Registry</div>', unsafe_allow_html=True)
    elif wallet_input:
        st.info("Kết nối Ganache để tra cứu dữ liệu thực")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Chiến dịch
# ═══════════════════════════════════════════════════════════════════════════════
elif "🗳️ Chiến dịch" in page:
    st.markdown("# 🗳️ Chiến dịch Biểu quyết")

    w3, contracts, err = try_connect()
    is_live = not bool(err)
    if err:
        st.markdown(f'<div class="alert-warn">🔌 {err}</div>', unsafe_allow_html=True)

    campaigns = DEMO_CAMPAIGNS
    if is_live:
        try:
            live_campaigns = get_all_campaigns(contracts["gov"])
            if live_campaigns: campaigns = live_campaigns
        except: pass

    # Campaign selector — hỗ trợ điều hướng từ trang Tổng quan
    campaign_options = {f"#{c['id']} — {c['title']}": c for c in campaigns}
    option_list = list(campaign_options.keys())
    _preselect = st.session_state.pop("selected_campaign", None)
    _default_idx = option_list.index(_preselect) if _preselect and _preselect in option_list else 0
    selected_key = st.selectbox("Chọn chiến dịch", option_list, index=_default_idx)
    c = campaign_options[selected_key]

    st.markdown("---")

    # Header
    col_info, col_status = st.columns([3, 1])
    with col_info:
        st.markdown(f"## #{c['id']} — {c['title']}")
        st.markdown(f"*{c['description']}*")
    with col_status:
        _commit_div = '<div style="margin-top:4px">🔒 Commit-Reveal</div>' if c.get('isCommitReveal') else ''
        _status_badge = status_badge(c['status'])
        st.markdown(
            '<div style="text-align:center;padding:20px;background:#1a1f2e;border-radius:12px;margin-top:10px">'
            + _status_badge +
            f'<div style="margin-top:10px;font-size:12px;color:#778">'
            f'<div>📌 {c["proposalType"]}</div>'
            f'<div style="margin-top:4px">⚙️ {c["mechanism"]}</div>'
            + _commit_div +
            '</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Vote metrics
    for_v = c["forVotes"]
    ag_v  = c["againstVotes"]
    abs_v = c["abstainVotes"]
    total = for_v + ag_v + abs_v
    total_hst = 10_000_000

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ FOR", fmt_hst(for_v), f"{for_v/total*100:.1f}%" if total > 0 else "0%")
    with col2:
        st.metric("❌ AGAINST", fmt_hst(ag_v), f"{ag_v/total*100:.1f}%" if total > 0 else "0%")
    with col3:
        st.metric("⬜ ABSTAIN", fmt_hst(abs_v), f"{abs_v/total*100:.1f}%" if total > 0 else "0%")
    with col4:
        part_pct = total / total_hst * 100 if total_hst > 0 else 0
        st.metric("📊 Tham gia", f"{part_pct:.1f}%", f"Ngưỡng: {c['quorumBps']:.0f}%")

    # Vote bar
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

    # Pass/Fail indicator
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

    # Commit-Reveal explanation
    if c.get("isCommitReveal"):
        st.markdown("---")
        st.markdown('<div class="section-header">🔒 Quy trình Commit-Reveal (Bỏ phiếu kín)</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="dao-card">
            <b style="color:#4a9eff">Giai đoạn 1: COMMIT</b><br><br>
            <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-text">Cổ đông tạo <code>hash = keccak256(vote || salt)</code></div></div>
            <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-text">Submit <b>hash</b> lên blockchain (không lộ phiếu)</div></div>
            <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-text">Deadline: 7 ngày sau khi mở</div></div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="dao-card">
            <b style="color:#2ddc64">Giai đoạn 2: REVEAL</b><br><br>
            <div class="timeline-item"><div class="timeline-dot" style="background:#2ddc64"></div><div class="timeline-text">Cổ đông public <code>vote + salt</code> gốc</div></div>
            <div class="timeline-item"><div class="timeline-dot" style="background:#2ddc64"></div><div class="timeline-text">Contract verify hash → ghi nhận phiếu</div></div>
            <div class="timeline-item"><div class="timeline-dot" style="background:#2ddc64"></div><div class="timeline-text">Deadline: 3 ngày sau commit</div></div>
            </div>
            """, unsafe_allow_html=True)

        # Hash generator
        st.markdown("**🔧 Công cụ tạo Commit Hash (Demo)**")
        col1, col2, col3 = st.columns(3)
        with col1: vote_choice = st.selectbox("Phiếu", ["FOR (0)", "AGAINST (1)", "ABSTAIN (2)"])
        with col2: salt_val = st.text_input("Salt (bí mật)", value="my_secret_salt_123")
        with col3: st.text_input("Kết quả hash (demo)", value=f"0x{hash(vote_choice+salt_val) & 0xFFFFFFFFFFFFFFFF:016x}...", disabled=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Phân tích
# ═══════════════════════════════════════════════════════════════════════════════
elif "📊 Phân tích" in page:
    st.markdown("# 📊 Phân tích & So sánh Cơ chế")

    tab1, tab2, tab3 = st.tabs(["⚖️ Linear vs Quadratic vs Equal", "📈 Tỷ lệ tham gia", "🔬 Kịch bản ID-103"])

    with tab1:
        st.markdown("### So sánh Voting Weight — 3 Cơ chế")
        st.markdown("*Với cùng phân bổ token, 3 cơ chế cho kết quả quyền lực rất khác nhau.*")

        shareholders_data = {
            "Chủ tịch HĐQT":       4_500_000,
            "Quỹ phát triển":      2_500_000,
            "Cổ đông A (Tổ chức)": 1_500_000,
            "Cổ đông B (Tổ chức)": 1_000_000,
            "Cổ đông C (Nhỏ lẻ)":    500_000,
        }

        names    = list(shareholders_data.keys())
        balances = list(shareholders_data.values())
        quadratic_w = [int(math.sqrt(b)) for b in balances]
        equal_w     = [1 for _ in balances]

        total_lin = sum(balances)
        total_qua = sum(quadratic_w)
        total_eq  = sum(equal_w)

        lin_pct = [b / total_lin * 100 for b in balances]
        qua_pct = [b / total_qua * 100 for b in quadratic_w]
        eq_pct  = [1 / len(names) * 100 for _ in names]

        # Table
        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr;gap:6px;padding:8px 12px;background:#1a2030;border-radius:8px;font-size:11px;color:#778;font-weight:700;letter-spacing:0.5px">
            <div>CỔ ĐÔNG</div><div>TOKEN</div><div>LIN weight</div><div>LIN %</div><div>QUAD weight</div><div>QUAD %</div><div>EQUAL %</div>
        </div>
        """, unsafe_allow_html=True)

        tier_colors = ["#ffd700","#c0c0c0","#cd7f32","#cd7f32","#8899bb"]
        for i, name in enumerate(names):
            color = tier_colors[i]
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
        - **Quadratic**: √token → giảm mạnh khoảng cách, Chủ tịch chỉ còn 31.8% power
        - **Equal**: Mỗi cổ đông 1 phiếu → hoàn toàn dân chủ, phù hợp bầu nhân sự
        """)

    with tab2:
        st.markdown("### Tỷ lệ tham gia theo Chiến dịch")
        campaign_data = [
            {"id": "ID-101 R&D Budget",    "status": "EXECUTED", "participation": 55.0, "for_pct": 70.0, "type": "Routine", "quorum": 10},
            {"id": "ID-102 Cổ tức 15%",    "status": "EXECUTED", "participation": 100.0,"for_pct": 70.0, "type": "Major",   "quorum": 20},
            {"id": "ID-103 CEO Election",  "status": "ACTIVE",   "participation": 37.4, "for_pct": 69.1, "type": "Major",   "quorum": 20},
            {"id": "ID-104 M&A TechCorp",  "status": "COMMIT",   "participation": 0.0,  "for_pct": 0.0,  "type": "M&A",    "quorum": 30},
        ]

        for cd in campaign_data:
            quorum_ok = cd["participation"] >= cd["quorum"]
            bar_pct = min(cd["participation"], 100)
            color = "#2ddc64" if quorum_ok else "#e0a020"
            _quorum_icon = '✅' if quorum_ok else '⚠️'
            if quorum_ok and cd["participation"] > 0:
                _quorum_label = '<span style="color:#2ddc64">Quorum đạt</span>'
            elif not quorum_ok:
                _quorum_label = '<span style="color:#e0a020">Chưa đủ quorum</span>'
            else:
                _quorum_label = '<span style="color:#778">Chưa có phiếu</span>'
            _sbadge = status_badge(cd['status'])
            st.markdown(
                '<div class="dao-card" style="margin:8px 0">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
                f'<b style="color:#eef">{cd["id"]}</b>'
                '<span>' + _sbadge + '</span>'
                '</div>'
                f'<div style="display:flex;gap:16px;font-size:12px;color:#778;margin-bottom:8px">'
                f'<span>📌 {cd["type"]}</span>'
                f'<span>Quorum yêu cầu: {cd["quorum"]}%</span>'
                f'<span>FOR: {cd["for_pct"]:.1f}%</span></div>'
                f'<div style="background:#1a1f2e;border-radius:6px;height:14px;overflow:hidden">'
                f'<div style="width:{bar_pct}%;background:linear-gradient(90deg,{color}88,{color});height:100%;border-radius:6px"></div></div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px">'
                f'<span style="color:{color}">{_quorum_icon} Tham gia: {cd["participation"]:.1f}%</span>'
                + _quorum_label +
                '</div></div>',
                unsafe_allow_html=True
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

        lin_for  = sum(b for v, b in votes.values() if v == "FOR")
        lin_ag   = sum(b for v, b in votes.values() if v == "AGAINST")
        qua_for  = sum(int(math.sqrt(b)) for v, b in votes.values() if v == "FOR")
        qua_ag   = sum(int(math.sqrt(b)) for v, b in votes.values() if v == "AGAINST")

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
        # Clone project
        git clone <repo>
        cd dao-voting-system

        # Cài JavaScript dependencies
        npm install

        # Cài Python dependencies
        pip install -r requirements.txt
        # (web3, streamlit, python-dotenv)
        ```

        ### 2. Mở Ganache
        ```
        • Ganache UI: Tạo workspace mới, port 7545, Chain ID 1337
        • Hoặc CLI:  npx ganache --port 7545 --chainId 1337 --accounts 10
        ```

        ### 3. Compile Contracts
        ```bash
        npx hardhat compile
        # → artifacts/ được tạo ra
        ```

        ### 4. Chạy Unit Tests
        ```bash
        npx hardhat test
        # → 4 kịch bản trong Governance.test.js
        # → Unit tests HSTToken.test.js
        ```

        ### 5. Deploy lên Ganache
        ```bash
        npx hardhat run scripts/setup_demo.js --network ganache
        # → Deploy: HSTToken, ShareholderRegistry, GovernanceContract, TimelockController
        # → Đăng ký 5 cổ đông demo
        # → Lưu địa chỉ vào dashboard/contract_addresses.json
        ```

        ### 6. Chạy Dashboard
        ```bash
        $env:PYTHONUTF8=1
        streamlit run dashboard/app.py --server.fileWatcherType none
        # → Mở http://localhost:8501
        # → Click "Kết nối Ganache" trong sidebar
        ```
        """)

    with tab2:
        st.markdown("""
        ## 🎮 Cách Tương tác với Hệ thống

        ### Qua Dashboard (Streamlit)
        | Trang | Chức năng |
        |-------|-----------|
        | 🏠 Tổng quan | Xem KPI, danh sách chiến dịch, phân bổ token |
        | 👥 Cổ đông | Xem danh sách, lọc theo Tier, tra cứu địa chỉ |
        | 🗳️ Chiến dịch | Xem chi tiết, kết quả, thông tin Commit-Reveal |
        | 📊 Phân tích | So sánh 3 cơ chế, biểu đồ tham gia |

        ### Qua Hardhat Console (trực tiếp)
        ```javascript
        npx hardhat console --network ganache

        // Lấy contract instance
        const hst = await ethers.getContractAt("HSTToken", "0x...")
        const gov = await ethers.getContractAt("GovernanceContract", "0x...")

        // Tạo chiến dịch
        await gov.createCampaign(
            "Tiêu đề", "Mô tả", 0, 0  // ROUTINE + LINEAR
        )

        // Cast vote
        await gov.connect(signer).castVote(campaignId, 0)  // 0 = FOR

        // Commit-Reveal: commit
        const salt = ethers.randomBytes(32)
        const hash = ethers.solidityPackedKeccak256(["uint8","bytes32"], [0, salt])
        await gov.connect(signer).commitVote(campaignId, hash)

        // Reveal
        await gov.connect(signer).revealVote(campaignId, 0, salt)
        ```

        ### Qua Python Web3
        ```python
        from utils.web3_helpers import connect_web3, get_all_contracts

        w3 = connect_web3()
        contracts = get_all_contracts(w3)

        # Đọc dữ liệu
        from utils.web3_helpers import get_all_campaigns
        campaigns = get_all_campaigns(contracts["gov"])
        ```
        """)

    with tab3:
        st.markdown("## 📐 Kiến trúc Hệ thống")
        st.markdown("""
        ```
        ┌─────────────────────────────────────────────────────────────┐
        │                     FRONTEND LAYER                          │
        │              Streamlit Dashboard (app.py)                    │
        └──────────────────────┬──────────────────────────────────────┘
                               │ web3.py
        ┌──────────────────────▼──────────────────────────────────────┐
        │                    PYTHON LAYER                             │
        │              utils/web3_helpers.py                          │
        │         (connect, read contracts, format data)              │
        └──────────────────────┬──────────────────────────────────────┘
                               │ JSON-RPC
        ┌──────────────────────▼──────────────────────────────────────┐
        │               BLOCKCHAIN LAYER (Ganache)                    │
        │                                                             │
        │  ┌──────────────┐  ┌──────────────────┐  ┌─────────────┐  │
        │  │  HSTToken    │  │ ShareholderReg.  │  │ Governance  │  │
        │  │  ERC20Votes  │←─│ KYC + Tier Mgmt  │←─│ Voting Core │  │
        │  └──────────────┘  └──────────────────┘  └──────┬──────┘  │
        │                                                   │         │
        │                                          ┌────────▼──────┐ │
        │                                          │   Timelock    │ │
        │                                          │ (delay exec.) │ │
        │                                          └───────────────┘ │
        └─────────────────────────────────────────────────────────────┘
        ```

        ### Luồng Biểu quyết
        1. **Admin** deploy + đăng ký cổ đông → Registry mint HST
        2. **Cổ đông** self-delegate để activate voting power
        3. **Campaign Manager** tạo chiến dịch (Routine/Major/M&A)
        4. **Cổ đông** bỏ phiếu trong thời hạn (Linear/Quadratic/Equal)
        5. **Anyone** gọi `finalizeCampaign()` sau deadline
        6. **Timelock** trì hoãn thực thi thêm N giây (bảo mật)
        """)

        st.markdown("---")
        st.markdown("### 🗳️ Các loại chiến dịch")
        data = [
            {"Loại": "Routine", "Ngưỡng": "> 50%", "Quorum": "10%", "Thời gian": "7 ngày",  "Ví dụ": "Ngân sách, dự án nhỏ"},
            {"Loại": "Major",   "Ngưỡng": "> 66%", "Quorum": "20%", "Thời gian": "14 ngày", "Ví dụ": "Cổ tức, bầu nhân sự"},
            {"Loại": "M&A",     "Ngưỡng": "> 75%", "Quorum": "30%", "Thời gian": "21 ngày", "Ví dụ": "Sáp nhập, bán công ty"},
        ]
        for d in data:
            color = {"Routine":"#4a9eff","Major":"#e0a020","M&A":"#dc4a4a"}[d["Loại"]]
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 2fr;gap:8px;padding:10px 14px;background:#1a1f2e;border-radius:8px;margin:4px 0;border-left:3px solid {color}">
                <div style="color:{color};font-weight:700">{d["Loại"]}</div>
                <div style="color:#eef">{d["Ngưỡng"]}</div>
                <div style="color:#eef">{d["Quorum"]}</div>
                <div style="color:#eef">{d["Thời gian"]}</div>
                <div style="color:#778">{d["Ví dụ"]}</div>
            </div>
            """, unsafe_allow_html=True)