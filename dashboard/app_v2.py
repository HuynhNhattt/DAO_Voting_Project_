"""
dashboard/app_v2.py
══════════════════════════════════════════════════════════════
Dashboard hoàn chỉnh — tích hợp tất cả 3 features mới:
  Feature 1: Polygon Amoy Testnet support
  Feature 2: KYC on-chain
  Feature 3: Bảo mật xác thực ví — thay private key bằng ký số

Chạy: streamlit run dashboard/app_v2.py
══════════════════════════════════════════════════════════════
"""

import streamlit as st
import json
from pathlib import Path
import sys

# Thêm utils vào path
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))   # project_root/utils/
sys.path.insert(0, str(Path(__file__).parent / "pages"))            # dashboard/pages/
sys.path.insert(0, str(Path(__file__).parent / "utils"))            # dashboard/utils/ (fallback)

# ── Core helpers ──────────────────────────────────────────────
from web3_helpers import (
    connect_web3, load_addresses, get_contract,
    get_all_campaigns, get_campaign_data, get_vote_participation,
    get_shareholder_info, get_token_balance, get_voting_power,
    get_delegation_status, get_token_info, get_all_certificates,
    get_certificate, verify_certificate, get_kyc_status,
    get_identity_verifier, check_can_vote_full,
)
from web3_helpers_amoy import (
    connect_web3_auto, load_addresses_auto, get_network_config,
    get_explorer_url, get_tx_url, switch_network,
)

# ── Feature 3: Xác thực an toàn ───────────────────────────────
from login_page import (
    render_login_sidebar, is_logged_in,
    get_wallet, get_pk,
    clear_pk, safe_tx,
)

# ── Feature 2: KYC ────────────────────────────────────────────
from kyc_page          import render_kyc_page
from kyc_status_widget import render_kyc_badge, render_vote_eligibility

# ── Timelock ──────────────────────────────────────────────────
from timelock_page import render_timelock_page, render_timelock_demo_controls

# ── Biên bản & On/Off-chain ───────────────────────────────────
from certificate_page import render_certificate_page, render_onchain_offchain_tab

# ── Network widget ────────────────────────────────────────────
from amoy_network_widget import render_network_selector

from web3 import Web3

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DAO Voting System v2",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS tùy chỉnh ─────────────────────────────────────────────
st.markdown("""
<style>
.stMetric label { font-size: 0.85rem; }
.stAlert { border-radius: 8px; }
div[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# INIT: Kết nối blockchain
# ══════════════════════════════════════════════════════════════
@st.cache_resource(ttl=30)
def init_connection(network_name: str):
    """Kết nối blockchain và load contracts."""
    try:
        w3, cfg = connect_web3_auto()
        addrs   = load_addresses_auto()
        contracts = {
            "hst":      get_contract(w3, "HSTToken",            addrs["hstToken"]),
            "registry": get_contract(w3, "ShareholderRegistry", addrs["registry"]),
            "gov":      get_contract(w3, "GovernanceContract",  addrs["governance"]),
            "cert":     None,
            "id_verifier": None,
        }
        if addrs.get("votingCertificate"):
            try:
                contracts["cert"] = get_contract(w3, "VotingCertificate", addrs["votingCertificate"])
            except Exception:
                pass
        if addrs.get("identityVerifier"):
            try:
                contracts["id_verifier"] = get_contract(w3, "IdentityVerifier", addrs["identityVerifier"])
            except Exception:
                pass
        return w3, contracts, addrs, cfg, None
    except Exception as e:
        return None, None, {}, {}, str(e)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
def render_sidebar(w3, contracts, addrs):
    st.sidebar.title("🏛️ DAO Voting System")
    st.sidebar.caption("v2.0 — Blockchain Governance")

    # ── Network selector (Feature 1: Amoy) ────────────────────
    selected_network = render_network_selector()

    # ── Trạng thái kết nối ────────────────────────────────────
    st.sidebar.markdown("---")
    if w3 and w3.is_connected():
        cfg = get_network_config()
        st.sidebar.success(
            f"✅ **{cfg['name']}**\n\n"
            f"Block: #{w3.eth.block_number}"
        )
    else:
        st.sidebar.error("❌ Mất kết nối blockchain")

    # ── Feature 3: Đăng nhập an toàn ─────────────────────────
    # Lưu addresses để dropdown chọn nhanh cổ đông
    if addrs.get("shareholders"):
        st.session_state["contract_addresses"] = addrs

    render_login_sidebar(contracts, w3)

    # ── Feature 2: KYC badge ──────────────────────────────────
    wallet = get_wallet()
    if wallet and contracts.get("id_verifier"):
        render_kyc_badge(contracts["id_verifier"], wallet)

    # ── Refresh ───────────────────────────────────────────────
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        st.cache_resource.clear()
        st.rerun()

    return selected_network


# ══════════════════════════════════════════════════════════════
# TAB: TỔNG QUAN
# ══════════════════════════════════════════════════════════════
def render_overview(w3, contracts, addrs):
    st.header("🏠 Tổng quan hệ thống")

    # Metrics hàng đầu
    col1, col2, col3, col4, col5 = st.columns(5)
    try:
        hst_info    = get_token_info(contracts["hst"])
        campaigns   = get_all_campaigns(contracts["gov"])
        active_c    = [c for c in campaigns if c["status"] == "ACTIVE"]
        queued_c    = [c for c in campaigns if c["status"] == "QUEUED"]
        executed_c  = [c for c in campaigns if c["status"] == "EXECUTED"]
        active_sh   = contracts["registry"].functions.activeShareholders().call()

        with col1: st.metric("👥 Cổ đông", active_sh)
        with col2: st.metric("💎 Tổng HST", f"{hst_info.get('supplyHST', 0):,}")
        with col3: st.metric("🗳️ Đang mở", len(active_c))
        with col4: st.metric("⏳ Chờ Timelock", len(queued_c))
        with col5: st.metric("✅ Đã thực thi", len(executed_c))
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")

    st.divider()

    # Danh sách campaigns đang mở
    col_camp, col_sh = st.columns([2, 1])

    with col_camp:
        st.subheader("📋 Chiến dịch đang mở")
        try:
            active = [c for c in campaigns if c["status"] in ("ACTIVE", "COMMIT", "REVEAL")]
            if not active:
                st.info("Không có chiến dịch nào đang mở.")
            for c in active:
                status_color = {"ACTIVE": "🟢", "COMMIT": "🟡", "REVEAL": "🔵"}.get(c["status"], "⚪")
                st.write(f"{status_color} **#{c['id']} {c['title']}**")
                st.caption(f"{c['proposalType']} · {c['mechanism']} · {c['status']}")
                col_f, col_a, col_ab = st.columns(3)
                with col_f:  st.write(f"✅ FOR: {c['forVotes']:,.0f}")
                with col_a:  st.write(f"❌ AGAINST: {c['againstVotes']:,.0f}")
                with col_ab: st.write(f"⬜ ABS: {c['abstainVotes']:,.0f}")
                st.divider()
        except Exception as e:
            st.error(str(e))

    with col_sh:
        st.subheader("👥 Cổ đông")
        try:
            sh_list = addrs.get("shareholders", [])
            hst_c   = contracts["hst"]
            for s in sh_list:
                bal = get_token_balance(hst_c, s["address"])
                pct = bal / 10_000_000 * 100
                tier_labels = {0: "Nhỏ lẻ", 1: "Tổ chức", 2: "Chiến lược", 3: "Sáng lập"}
                st.write(f"**{s['name']}**")
                st.caption(f"{pct:.1f}% · {tier_labels.get(s['tier'], '?')}")

                # KYC badge nhỏ
                if contracts.get("id_verifier"):
                    kyc = get_kyc_status(contracts["id_verifier"], s["address"])
                    kyc_icon = "🪪✅" if kyc.get("canVoteKYC") else "🪪❌"
                    st.caption(kyc_icon)
                st.divider()
        except Exception as e:
            st.error(str(e))


# ══════════════════════════════════════════════════════════════
# TAB: BỎ PHIẾU
# ══════════════════════════════════════════════════════════════
def render_vote_tab(w3, contracts):
    st.header("🗳️ Bỏ phiếu")

    if not is_logged_in():
        st.warning("🔒 Vui lòng đăng nhập để bỏ phiếu.")
        return

    wallet = get_wallet()

    # ── Kiểm tra điều kiện đầy đủ (Feature 2 + 3) ────────────
    st.subheader("📋 Điều kiện tham gia")
    render_vote_eligibility(contracts, wallet)
    st.divider()

    # ── Chọn campaign ─────────────────────────────────────────
    campaigns = get_all_campaigns(contracts["gov"])
    votable   = [c for c in campaigns if c["status"] == "ACTIVE"]

    if not votable:
        st.info("Không có chiến dịch nào đang nhận phiếu.")
        return

    options  = {f"#{c['id']} {c['title']}": c for c in votable}
    selected = st.selectbox("Chọn chiến dịch:", list(options.keys()))
    camp     = options[selected]

    # Hiển thị chi tiết campaign
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Loại:** {camp['proposalType']}")
        st.write(f"**Cơ chế:** {camp['mechanism']}")
        st.write(f"**Ngưỡng thông qua:** {camp['passThreshold']:.0f}%")
    with col2:
        st.write(f"**Quorum:** {camp['quorumBps']:.0f}%")
        st.write(f"**Snapshot block:** #{camp['snapshotBlock']}")

    # Kết quả tạm thời
    part = get_vote_participation(contracts["gov"], contracts["hst"], camp["id"])
    if part:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("FOR",     f"{part.get('forVotes', 0):,.0f}")
        with c2: st.metric("AGAINST", f"{part.get('againstVotes', 0):,.0f}")
        with c3: st.metric("ABSTAIN", f"{part.get('abstainVotes', 0):,.0f}")
        with c4: st.metric("Tham gia", f"{part.get('participationPct', 0):.1f}%")

    # ── Bỏ phiếu ─────────────────────────────────────────────
    st.divider()
    already_voted = False
    try:
        already_voted = contracts["gov"].functions.hasVoted(
            camp["id"], Web3.to_checksum_address(wallet)
        ).call()
    except Exception:
        pass

    if already_voted:
        ballot = None
        try:
            raw    = contracts["gov"].functions.getBallot(
                camp["id"], Web3.to_checksum_address(wallet)
            ).call()
            option_labels = ["✅ TÁN THÀNH (FOR)", "❌ PHẢN ĐỐI (AGAINST)", "⬜ BỎ TRẮNG (ABSTAIN)"]
            ballot = option_labels[raw[0]] if raw else "?"
        except Exception:
            pass
        st.success(f"✅ Bạn đã bỏ phiếu: **{ballot}**")
        return

    col_for, col_against, col_abs = st.columns(3)
    with col_for:
        if st.button("✅ TÁN THÀNH", type="primary", key="btn_for"):
            _cast_vote(w3, contracts, camp["id"], 0)
    with col_against:
        if st.button("❌ PHẢN ĐỐI", key="btn_against"):
            _cast_vote(w3, contracts, camp["id"], 1)
    with col_abs:
        if st.button("⬜ BỎ TRẮNG", key="btn_abstain"):
            _cast_vote(w3, contracts, camp["id"], 2)


def _cast_vote(w3, contracts, campaign_id: int, option: int):
    """Bỏ phiếu — dùng safe_send_tx (Feature 3)."""
    wallet = get_wallet()
    if not wallet:
        st.error("Chưa đăng nhập")
        return

    with st.spinner("Đang bỏ phiếu..."):
        fn     = contracts["gov"].functions.castVote(campaign_id, option)
        result = safe_tx(w3, fn)

    if result.get("success"):
        explorer = get_tx_url(result["txHash"])
        if explorer:
            st.success(f"✅ Bỏ phiếu thành công! [Xem trên Explorer]({explorer})")
        st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB: CỔ ĐÔNG
# ══════════════════════════════════════════════════════════════
def render_shareholders_tab(w3, contracts, addrs):
    st.header("👥 Danh sách cổ đông")

    shareholders = addrs.get("shareholders", [])
    if not shareholders:
        st.info("Chưa có dữ liệu cổ đông.")
        return

    wallet_me = get_wallet()

    for s in shareholders:
        addr    = s["address"]
        bal     = get_token_balance(contracts["hst"], addr)
        vp      = get_voting_power(contracts["hst"], addr)
        ds      = get_delegation_status(contracts["hst"], addr)
        pct     = bal / 10_000_000 * 100
        is_me   = bool(wallet_me and addr.lower() == wallet_me.lower())

        header = f"{'👤 ' if is_me else ''}{s['name']} — {pct:.1f}%"
        with st.expander(header, expanded=is_me):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("HST Token", f"{bal:,.0f}")
                st.metric("Voting Power", f"{vp:,.0f}")
            with c2:
                tier_l = {0:"Nhỏ lẻ",1:"Tổ chức",2:"Chiến lược",3:"Sáng lập"}
                st.write(f"**Tier:** {tier_l.get(s['tier'], '?')}")
                st.write(f"**Địa chỉ:** `{addr[:16]}...`")
                st.caption(ds.get("hint", ""))
            with c3:
                # KYC status (Feature 2)
                if contracts.get("id_verifier"):
                    kyc = get_kyc_status(contracts["id_verifier"], addr)
                    if kyc.get("canVoteKYC"):
                        st.success(f"🪪 KYC: {kyc['levelLabel']} ✅\nCòn {kyc['daysLeft']} ngày")
                    elif kyc.get("error"):
                        st.caption("🪪 KYC: N/A")
                    else:
                        st.warning("🪪 KYC: Chưa xác thực")

            # Link explorer (Feature 1: Amoy)
            explorer = get_explorer_url(addr)
            if explorer:
                st.markdown(f"[🔗 Xem trên Polygonscan]({explorer})")

            # Self-delegate nếu chưa (chỉ hiển thị cho chính mình)
            if is_me and not ds.get("isDelegated") and is_logged_in():
                if st.button("⚡ Kích hoạt Voting Power", key=f"delegate_{addr}"):
                    fn = contracts["hst"].functions.delegate(
                        Web3.to_checksum_address(addr)
                    )
                    safe_tx(w3, fn)
                    st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB: PHÂN TÍCH
# ══════════════════════════════════════════════════════════════
def render_analysis_tab(contracts, addrs):
    st.header("📊 Phân tích biểu quyết")

    campaigns = get_all_campaigns(contracts["gov"])
    if not campaigns:
        st.info("Chưa có chiến dịch nào.")
        return

    # Chọn campaign phân tích
    done = [c for c in campaigns if c["status"] in ("EXECUTED","DEFEATED","QUEUED","EXECUTABLE")]
    if not done:
        st.info("Chưa có chiến dịch nào kết thúc.")
        return

    options  = {f"#{c['id']} {c['title']} ({c['status']})": c for c in done}
    selected = st.selectbox("Chọn chiến dịch:", list(options.keys()))
    camp     = options[selected]

    part = get_vote_participation(contracts["gov"], contracts["hst"], camp["id"])
    if not part:
        st.warning("Chưa có dữ liệu.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Kết quả bỏ phiếu")
        st.metric("✅ FOR",       f"{part.get('forVotes',0):,.2f} HST",  f"{part.get('forPct',0):.1f}%")
        st.metric("❌ AGAINST",   f"{part.get('againstVotes',0):,.2f} HST")
        st.metric("⬜ ABSTAIN",   f"{part.get('abstainVotes',0):,.2f} HST")
        st.metric("👥 Tham gia",  f"{part.get('participationPct',0):.1f}%",
                  f"{'✅' if part.get('quorumMet') else '❌'} Quorum {camp['quorumBps']:.0f}%")
    with col2:
        st.subheader("So sánh 3 cơ chế")
        st.write("**Kịch bản ID-103 (Quadratic bảo vệ thiểu số):**")
        data = {
            "Cổ đông": ["Chủ tịch\n(45%)", "Quỹ PT\n(25%)", "CĐ A\n(15%)", "CĐ B\n(10%)", "CĐ C\n(5%)"],
            "Linear %": [45.0, 25.0, 15.0, 10.0, 5.0],
            "Quadratic %": [35.0, 26.2, 20.3, 16.5, 11.7],
            "Equal %": [20.0, 20.0, 20.0, 20.0, 20.0],
        }
        import pandas as pd
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        st.caption("Quadratic giảm ưu thế cổ đông lớn, bảo vệ tiếng nói thiểu số.")


# ══════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════
def main():
    # ── Kết nối ───────────────────────────────────────────────
    active_net = st.session_state.get("active_network", "ganache")
    w3, contracts, addrs, cfg, err = init_connection(active_net)

    # ── Sidebar ───────────────────────────────────────────────
    selected_net = render_sidebar(w3, contracts, addrs)
    if selected_net != active_net:
        st.session_state["active_network"] = selected_net
        st.cache_resource.clear()
        st.rerun()

    # ── Lỗi kết nối ───────────────────────────────────────────
    if err or not w3:
        st.error(f"❌ Không thể kết nối blockchain: {err or 'Unknown error'}")
        st.info(
            "**Ganache:** Đảm bảo Ganache đang chạy trên port 7545\n\n"
            "**Amoy:** Kiểm tra kết nối internet và RPC URL"
        )
        return

    # ── Header ────────────────────────────────────────────────
    st.title("🏛️ DAO Voting System")
    net_name = cfg.get("name", "Unknown")
    block    = w3.eth.block_number
    st.caption(f"Mạng: **{net_name}** · Block: #{block} · v2.0")

    if cfg.get("explorer"):
        st.caption(f"[🔗 Polygonscan Amoy]({cfg['explorer']})")

    # ── Tabs ──────────────────────────────────────────────────
    tabs = st.tabs([
        "🏠 Tổng quan",
        "🗳️ Bỏ phiếu",
        "👥 Cổ đông",
        "📊 Phân tích",
        "📄 Biên bản",
        "⏳ Timelock",
        "🪪 KYC",
        "⛓️ On/Off-chain",
    ])

    tab_home, tab_vote, tab_sh, tab_analysis, tab_cert, tab_tl, tab_kyc, tab_info = tabs

    with tab_home:
        render_overview(w3, contracts, addrs)

    with tab_vote:
        render_vote_tab(w3, contracts)

    with tab_sh:
        render_shareholders_tab(w3, contracts, addrs)

    with tab_analysis:
        render_analysis_tab(contracts, addrs)

    with tab_cert:
        render_certificate_page(contracts, w3)

    with tab_tl:
        wallet = get_wallet()
        pk     = get_pk()
        render_timelock_page(contracts, w3, wallet, pk)
        # Fast-forward controls cho Ganache
        if cfg.get("name") == "Ganache Local" and is_logged_in():
            st.divider()
            render_timelock_demo_controls(contracts, w3, wallet, pk)

    with tab_kyc:
        render_kyc_page(
            contracts = contracts,
            w3        = w3,
            wallet    = get_wallet(),
            private_key = get_pk(),
            is_admin  = st.session_state.get("is_admin", False),
        )

    with tab_info:
        render_onchain_offchain_tab()


if __name__ == "__main__":
    main()