"""
dashboard/app_additions.py
══════════════════════════════════════════════════════════════
Các hàm BỔ SUNG cho app.py hiện có.
Nhận xét thầy #1, #2, #3, #4.

CÁCH TÍCH HỢP VÀO app.py CÓ SẴN:
  Thêm vào cuối file app.py:
    from app_additions import (
        render_token_info_tab,
        render_certificate_tab,
        render_onchain_offchain_tab,
        render_vote_with_signature,
    )
  Sau đó thêm các tab mới vào sidebar navigation.
══════════════════════════════════════════════════════════════
"""

import streamlit as st
import json
from datetime import datetime
from pathlib  import Path

# ─── Import helpers ───────────────────────────────────────────
from web3_helpers import (
    get_token_info,
    get_delegation_status,
    get_certificate_data,
    verify_certificate,
    get_all_certificates,
    get_all_campaigns,
    generate_login_challenge,
    sign_challenge,
    verify_wallet_login,
    preview_campaign_result,
    build_and_send_tx,
)


# ══════════════════════════════════════════════════════════════
# NHẬN XÉT THẦY #1 — Tab: Vai trò & Chức năng Token
# ══════════════════════════════════════════════════════════════

def render_token_info_tab(w3, contracts):
    """
    Tab hiển thị rõ vai trò và chức năng của HST Token.
    Tích hợp vào app.py phần sidebar "🪙 Token HST".
    """
    st.header("🪙 Vai trò & Chức năng của HST Token")

    # ── Thông tin cơ bản (ON-CHAIN) ───────────────────────────
    token_info = get_token_info(contracts["hst"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Tên Token",      token_info["name"])
    col2.metric("Ký hiệu",        token_info["symbol"])
    col3.metric("Tổng cung",      f"{token_info['totalSupply']:,.0f} HST")

    st.caption(f"🔗 ON-CHAIN | Owner (Registry): `{token_info['owner']}`")

    # ── 3 Vai trò chính ───────────────────────────────────────
    st.subheader("3 Vai trò chính của HST Token")

    with st.expander("① Chứng nhận sở hữu cổ phần", expanded=True):
        st.markdown("""
**1 HST = 1 đơn vị cổ phần** trong công ty.

| Cổ đông | Số HST | Tỷ lệ | Tier |
|---------|--------|-------|------|
| Chủ tịch HĐQT | 4,500,000 | 45% | Sáng lập (≥30%) |
| Quỹ phát triển | 2,500,000 | 25% | Chiến lược (≥10%) |
| Cổ đông A | 1,500,000 | 15% | Tổ chức (≥1%) |
| Cổ đông B | 1,000,000 | 10% | Tổ chức (≥1%) |
| Cổ đông C | 500,000 | 5% | Nhỏ lẻ (<1%) |

🔗 **ON-CHAIN**: `HSTToken.balanceOf(address)` — không thể làm giả
        """)

    with st.expander("② Quyền biểu quyết (Voting Power)"):
        st.markdown("""
Token **phải được kích hoạt** qua `delegate()` mới có voting power.

**3 cơ chế tính trọng số:**

| Cơ chế | Công thức | Tỷ lệ quyền lực | Dùng khi nào |
|--------|-----------|-----------------|--------------|
| **LINEAR** | weight = HST | 45%:5% = 9:1 | Quyết định tài chính |
| **QUADRATIC** | weight = √HST | √4.5M:√0.5M ≈ 3:1 | Bầu nhân sự |
| **EQUAL** | weight = 1 | 1:1 | Bầu Ban kiểm soát |

🔗 **ON-CHAIN**: `HSTToken.getPastVotes(voter, snapshotBlock)`
        """)

    with st.expander("③ Xác định Tier cổ đông (Tư cách biểu quyết)"):
        st.markdown("""
`ShareholderRegistry` dùng số dư HST để phân loại:

| Tier | Tên | Ngưỡng sở hữu |
|------|-----|---------------|
| 3 | Sáng lập | ≥ 30% (≥ 3,000,000 HST) |
| 2 | Chiến lược | ≥ 10% (≥ 1,000,000 HST) |
| 1 | Tổ chức | ≥ 1% (≥ 100,000 HST) |
| 0 | Nhỏ lẻ | < 1% |

🔗 **ON-CHAIN**: `ShareholderRegistry.canVote(address)`
        """)

    # ── Kiểm tra trạng thái delegation của ví đang đăng nhập ──
    if st.session_state.get("wallet"):
        wallet = st.session_state["wallet"]
        st.subheader("Trạng thái Voting Power của bạn")
        status = get_delegation_status(contracts["hst"], wallet)

        col1, col2 = st.columns(2)
        col1.metric("Số dư HST",      f"{status['balance']:,.0f}")
        col2.metric("Voting Power",   f"{status['votingPower']:,.0f}")

        if not status["isDelegated"]:
            st.warning(status["hint"])
            if st.button("⚡ Kích hoạt Voting Power (Delegate)"):
                st.info("Gọi delegate() từ Dashboard → xem hướng dẫn trong tab Bỏ phiếu")
        else:
            st.success("✅ Voting Power đã được kích hoạt")


# ══════════════════════════════════════════════════════════════
# NHẬN XÉT THẦY #2 — Quy trình nghiệp vụ + ánh xạ thực tế
# ══════════════════════════════════════════════════════════════

def render_business_process_tab(w3, contracts):
    """
    Tab minh họa quy trình nghiệp vụ biểu quyết và ánh xạ thực tế.
    """
    st.header("📋 Quy trình Nghiệp vụ Biểu quyết")

    st.markdown("""
### Ánh xạ: ĐHCĐ Truyền thống → Blockchain

| Truyền thống | Blockchain (Contract này) |
|---|---|
| Ban tổ chức chuẩn bị tờ phiếu | `createCampaign()` — tạo campaign |
| Chốt danh sách cổ đông | `snapshotBlock = block.number` |
| Phát phiếu tại hội trường | `castVote()` — cổ đông bỏ phiếu |
| Nhân viên kiểm tra CMND | `registry.canVote()` — xác thực on-chain |
| Đếm phiếu thủ công | `_recordVote()` — tự động cộng dồn |
| Công bố kết quả | `finalizeCampaign()` — tính & lưu kết quả |
| Thư ký ký biên bản | `VotingCertificate.issueCertificate()` |
    """)

    st.subheader("Chứng minh thực tế — Kịch bản ID-101")

    tab1, tab2, tab3 = st.tabs(["① Tạo chiến dịch", "② Bỏ phiếu", "③ Kết quả"])

    with tab1:
        st.markdown("""
**`createCampaign("Phê duyệt ngân sách R&D 2025", ...)`**

```
snapshotBlock = 423  ← Chốt danh sách tại block này
votingDeadline = 7 ngày từ lúc tạo
passThreshold = 50%   (ROUTINE)
quorumBps = 10%       (phải có ≥ 10% tổng cung tham gia)
```

🔗 **ON-CHAIN**: Toàn bộ tham số được lưu bất biến.
Sau khi tạo, không ai (kể cả Admin) có thể sửa ngưỡng biểu quyết.
        """)

    with tab2:
        camps = get_all_campaigns(contracts["gov"])
        if camps:
            active = [c for c in camps if c["status"] == "ACTIVE"]
            if active:
                camp = st.selectbox(
                    "Chọn chiến dịch để xem dữ liệu thực:",
                    active,
                    format_func=lambda c: f"#{c['id']} {c['title']}"
                )
                preview = preview_campaign_result(contracts["gov"], camp["id"])
                if preview:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Tỷ lệ tham gia", f"{preview['participationBps']:.1f}%")
                    col2.metric("Tỷ lệ FOR",       f"{preview['forBps']:.1f}%")
                    col3.metric("Kết quả dự kiến",
                        "✅ PASS" if preview["wouldPass"] else "❌ DEFEAT")

                    st.caption(f"🔗 ON-CHAIN data realtime | Quorum đạt: {'✅' if preview['quorumMet'] else '❌'}")
            else:
                st.info("Không có chiến dịch ACTIVE nào hiện tại.")

    with tab3:
        st.markdown("""
**`finalizeCampaign(1)` — Ai cũng có thể gọi sau khi hết hạn**

```
totalVoted = FOR + AGAINST + ABSTAIN
participationBps = totalVoted / totalSupply = 85%  ✅ > 10% quorum
decisiveVotes = FOR + AGAINST
forBps = FOR / decisiveVotes = 84.2%  ✅ > 50% threshold
→ CampaignStatus = EXECUTED (PASS)
→ VotingCertificate.issueCertificate() được gọi tự động
```

🔗 Kết quả được ghi ON-CHAIN, kèm biên bản có hash.
        """)


# ══════════════════════════════════════════════════════════════
# NHẬN XÉT THẦY #3 — Tab: Biên bản chữ ký số
# ══════════════════════════════════════════════════════════════

def render_certificate_tab(w3, contracts):
    """
    Tab hiển thị biên bản chữ ký số sau khi chiến dịch finalize.
    Tích hợp vào app.py phần sidebar "📜 Biên bản".
    """
    st.header("📜 Biên bản Biểu quyết — Chữ ký số On-chain")

    st.info(
        "Sau khi chiến dịch kết thúc, hệ thống tự động tạo biên bản "
        "có chữ ký số lưu vĩnh viễn trên blockchain. "
        "Không thể làm giả hay chỉnh sửa."
    )

    if "certificate" not in contracts:
        st.warning("⚠️ VotingCertificate contract chưa được deploy. Chạy lại setup_demo.js.")
        return

    cert_contract = contracts["certificate"]

    # ── Danh sách tất cả biên bản ─────────────────────────────
    all_certs = get_all_certificates(cert_contract)

    if not all_certs:
        st.info("Chưa có biên bản nào. Finalize một chiến dịch để tạo biên bản.")
        return

    st.success(f"✅ Có **{len(all_certs)}** biên bản on-chain")

    # ── Chọn biên bản xem ─────────────────────────────────────
    selected = st.selectbox(
        "Chọn biên bản:",
        all_certs,
        format_func=lambda c: f"#{c['campaignId']} — {c['campaignTitle']} [{c['result']}]"
    )

    if not selected:
        return

    # ── Hiển thị biên bản ─────────────────────────────────────
    st.divider()
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"#{selected['campaignId']} — {selected['campaignTitle']}")

        result_color = "green" if selected["passed"] else "red"
        st.markdown(
            f"**Kết quả: :{result_color}[{selected['result']}]**"
        )

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("✅ Tán thành",    f"{selected['forVotes']:,.0f} HST")
        col_b.metric("❌ Phản đối",     f"{selected['againstVotes']:,.0f} HST")
        col_c.metric("⬜ Trắng",        f"{selected['abstainVotes']:,.0f} HST")

        col_d, col_e, col_f = st.columns(3)
        col_d.metric("Tỷ lệ FOR",       f"{selected['forBps']:.1f}%")
        col_e.metric("Tỷ lệ tham gia",  f"{selected['participationBps']:.1f}%")
        col_f.metric("Cổ đông đã vote", f"{selected['totalParticipants']} người")

        st.markdown("**Thông tin kỹ thuật:**")
        st.markdown(f"""
- Loại đề xuất : `{['Routine','Major','M&A'][selected['proposalType']]}`
- Cơ chế phiếu: `{['Linear','Quadratic','Equal'][selected['mechanism']]}`
- Block snapshot: `#{selected['snapshotBlock']}`
- Ngưỡng thông qua: `{selected['passThreshold']:.0f}%`
- Quorum yêu cầu: `{selected['quorumBps']:.0f}%`
        """)

    with col2:
        st.markdown("**🔐 Chữ ký số On-chain**")
        st.markdown(f"Người ký: `{selected['finalizedBy'][:10]}...`")
        st.markdown(f"Thời gian: `{selected['finalizedAtStr']}`")
        st.code(selected["certificateHash"][:20] + "...", language="text")
        st.caption("Certificate Hash (đầy đủ ở dưới)")

    # ── Hash đầy đủ ───────────────────────────────────────────
    with st.expander("🔍 Certificate Hash đầy đủ (On-chain)"):
        st.code(selected["certificateHash"], language="text")
        st.caption(
            "Hash này lưu vĩnh viễn trên blockchain. "
            "Dùng để xác minh biên bản chưa bị chỉnh sửa."
        )

    # ── Verify tính toàn vẹn ──────────────────────────────────
    st.subheader("🛡️ Xác minh tính toàn vẹn")
    if st.button("🔍 Verify biên bản on-chain"):
        with st.spinner("Đang verify..."):
            result = verify_certificate(cert_contract, selected["campaignId"])
        if result["isValid"]:
            st.success(result["status"])
        else:
            st.error(result["status"])
        col1, col2 = st.columns(2)
        col1.text_input("Hash đang lưu:",    result.get("storedHash",   ""), disabled=True)
        col2.text_input("Hash tính lại:",    result.get("computedHash", ""), disabled=True)

    # ── Xuất biên bản ─────────────────────────────────────────
    st.subheader("📥 Xuất biên bản")
    if st.button("📄 Tạo biên bản text"):
        try:
            from certificate_generator import (
                generate_certificate_text,
                verify_certificate_integrity,
            )
            verification = {
                "message":      result.get("status", ""),
                "storedHash":   result.get("storedHash", ""),
                "computedHash": result.get("computedHash", ""),
            }
            cert_text = generate_certificate_text(selected, verification)
            st.download_button(
                "⬇️ Tải biên bản (.txt)",
                data=cert_text.encode("utf-8"),
                file_name=f"bienban_campaign{selected['campaignId']}.txt",
                mime="text/plain",
            )
            with st.expander("Xem trước biên bản"):
                st.text(cert_text)
        except ImportError:
            # Fallback nếu chưa có module
            lines = [
                f"BIÊN BẢN BIỂU QUYẾT CỔ ĐÔNG",
                f"Campaign #{selected['campaignId']}: {selected['campaignTitle']}",
                f"Kết quả: {selected['result']}",
                f"FOR: {selected['forVotes']:,.0f} HST ({selected['forBps']:.1f}%)",
                f"AGAINST: {selected['againstVotes']:,.0f} HST",
                f"ABSTAIN: {selected['abstainVotes']:,.0f} HST",
                f"Người ký: {selected['finalizedBy']}",
                f"Thời gian: {selected['finalizedAtStr']}",
                f"Certificate Hash: {selected['certificateHash']}",
            ]
            cert_text = "\n".join(lines)
            st.download_button(
                "⬇️ Tải biên bản (.txt)",
                data=cert_text.encode("utf-8"),
                file_name=f"bienban_campaign{selected['campaignId']}.txt",
                mime="text/plain",
            )


# ══════════════════════════════════════════════════════════════
# NHẬN XÉT THẦY #4 — Tab: On-chain vs Off-chain
# ══════════════════════════════════════════════════════════════

def render_onchain_offchain_tab(w3, contracts, addrs):
    """
    Tab giải thích rõ On-chain vs Off-chain trong hệ thống.
    Tích hợp vào app.py phần sidebar "📚 Kiến trúc".
    """
    st.header("⛓️ On-chain vs Off-chain — Phân vùng dữ liệu")

    st.markdown("""
> **Nguyên tắc thiết kế:** Dữ liệu cần *bất biến + công khai* → ON-CHAIN.
> Dữ liệu *nhạy cảm hoặc format đẹp* → OFF-CHAIN, anchor bằng hash.
    """)

    tab_on, tab_off, tab_flow = st.tabs([
        "⛓️ ON-CHAIN (Blockchain)",
        "💻 OFF-CHAIN (Server/App)",
        "🔗 Luồng dữ liệu"
    ])

    with tab_on:
        st.subheader("Dữ liệu ON-CHAIN — Bất biến, Công khai")
        st.caption("Lưu trong smart contract trên Ganache / Polygon Amoy")

        onchain_items = [
            {
                "icon": "🪙",
                "what": "Số dư HST Token",
                "where": "HSTToken.balanceOf()",
                "why": "Xác định quyền sở hữu cổ phần không thể làm giả",
                "live": True,
            },
            {
                "icon": "⚡",
                "what": "Lịch sử Voting Power (Checkpoint)",
                "where": "HSTToken.getPastVotes(voter, block)",
                "why": "Chống thao túng: mua token sau snapshot không được tính",
                "live": True,
            },
            {
                "icon": "🏛️",
                "what": "Tư cách cổ đông & Tier",
                "where": "ShareholderRegistry.canVote()",
                "why": "Kiểm soát ai được bỏ phiếu — không qua tay admin",
                "live": True,
            },
            {
                "icon": "🗳️",
                "what": "Từng lá phiếu bầu",
                "where": "GovernanceContract — VoteCast event",
                "why": "Mỗi phiếu ghi vĩnh viễn, không thể xóa hay sửa",
                "live": True,
            },
            {
                "icon": "📊",
                "what": "Kết quả chiến dịch (PASS/DEFEAT)",
                "where": "GovernanceContract.campaign.status",
                "why": "Tính tự động, không qua tay ban tổ chức",
                "live": True,
            },
            {
                "icon": "📜",
                "what": "Biên bản chữ ký số",
                "where": "VotingCertificate.certificates[id]",
                "why": "Certificate hash chứng minh kết quả không thể làm giả",
                "live": True,
            },
        ]

        for item in onchain_items:
            with st.expander(f"{item['icon']} **{item['what']}**"):
                st.markdown(f"**Lưu tại:** `{item['where']}`")
                st.markdown(f"**Lý do:** {item['why']}")
                if item["live"]:
                    st.caption("🔗 Có thể xem trực tiếp trên Ganache hoặc Polygonscan")

        # Live data từ blockchain
        st.divider()
        st.subheader("📡 Dữ liệu ON-CHAIN Realtime")
        try:
            block = w3.eth.block_number
            supply = contracts["hst"].functions.totalSupply().call() / 10**18
            n_camp = contracts["gov"].functions.campaignCounter().call()
            active_sh = contracts["registry"].functions.activeShareholders().call()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Block hiện tại", f"#{block}")
            col2.metric("Tổng cung HST",  f"{supply:,.0f}")
            col3.metric("Cổ đông",        active_sh)
            col4.metric("Chiến dịch",     n_camp)
            st.caption(f"ChainID: {w3.eth.chain_id} | RPC: {addrs.get('network','?')}")
        except Exception as e:
            st.error(f"Không đọc được dữ liệu: {e}")

    with tab_off:
        st.subheader("Dữ liệu OFF-CHAIN — Cần bảo vệ riêng")
        st.caption("Lưu trên máy tính / server — có thể bị sửa → dùng hash để anchor")

        offchain_items = [
            {
                "icon": "👤",
                "what": "Tên thật cổ đông",
                "where": "contract_addresses.json",
                "risk": "Có thể bị sửa → cần backup và bảo vệ file",
                "anchor": "Ánh xạ tên ↔ địa chỉ ví lưu riêng",
            },
            {
                "icon": "🪪",
                "what": "CCCD / Giấy tờ định danh gốc",
                "where": "Lưu nội bộ công ty",
                "risk": "File gốc có thể thất lạc",
                "anchor": "Hash của CCCD lưu ON-CHAIN (identityHash)",
            },
            {
                "icon": "🔑",
                "what": "Private Key cổ đông",
                "where": "File .env / MetaMask / Ví cứng",
                "risk": "⚠️ NGUY HIỂM — lộ key = mất toàn bộ tài sản",
                "anchor": "Không bao giờ gửi lên server — chỉ ký local",
            },
            {
                "icon": "🖥️",
                "what": "Dashboard Streamlit (app.py)",
                "where": "Server chạy Streamlit",
                "risk": "Server down → không xem được UI, nhưng dữ liệu on-chain vẫn còn",
                "anchor": "Chỉ là giao diện đọc dữ liệu — không lưu dữ liệu",
            },
            {
                "icon": "📄",
                "what": "File biên bản PDF / TXT",
                "where": "dashboard/certificates/",
                "risk": "File có thể bị sửa",
                "anchor": "certificateHash on-chain dùng để verify",
            },
            {
                "icon": "⚙️",
                "what": "contract_addresses.json",
                "where": "dashboard/contract_addresses.json",
                "risk": "Sửa sai địa chỉ → Dashboard đọc nhầm contract",
                "anchor": "Tạo tự động bởi setup_demo.js sau mỗi lần deploy",
            },
        ]

        for item in offchain_items:
            with st.expander(f"{item['icon']} **{item['what']}**"):
                st.markdown(f"**Lưu tại:** {item['where']}")
                st.warning(f"⚠️ Rủi ro: {item['risk']}")
                st.info(f"🔗 Anchor: {item['anchor']}")

    with tab_flow:
        st.subheader("Luồng dữ liệu End-to-End")
        st.markdown("""
```
CỔ ĐÔNG (OFF-CHAIN)          DASHBOARD (OFF-CHAIN)       BLOCKCHAIN (ON-CHAIN)
─────────────────────         ─────────────────────       ─────────────────────
                              
1. Chọn ví từ danh sách  →   Tạo challenge message   →   (không lên chain)
2. Ký challenge bằng key →   recover_signer()          →   registry.canVote() ✅
3. Chọn FOR/AGAINST/ABSTAIN→  build_and_send_tx()     →   castVote() → VoteCast event
4. Xem kết quả realtime  ←   get_campaign_data()      ←   campaigns[id].forVotes
5. Xem biên bản          ←   get_certificate_data()   ←   VotingCertificate.getCert()
6. Tải file biên bản     ←   generate_certificate_text←   (đọc hash từ on-chain)
```

**Nguyên tắc:**
- Mũi tên `→` : ghi dữ liệu lên blockchain (tốn gas, bất biến)
- Mũi tên `←` : đọc dữ liệu từ blockchain (miễn phí, view call)
- Bước 1-2 xảy ra hoàn toàn OFF-CHAIN (không tốn gas)
        """)


# ══════════════════════════════════════════════════════════════
# BẢO MẬT — Đăng nhập bằng chữ ký số (thay private key)
# ══════════════════════════════════════════════════════════════

def render_secure_login(w3, contracts, addrs):
    """
    Widget đăng nhập an toàn — không nhập private key trực tiếp.

    Thay thế phần đăng nhập cũ trong app.py.
    Dùng Sign Message pattern: cổ đông ký challenge, server verify.
    """
    st.subheader("🔐 Đăng nhập Ví Cổ đông")

    # Danh sách cổ đông từ config (OFF-CHAIN)
    shareholders = addrs.get("shareholders", [])
    if not shareholders:
        st.error("Không có danh sách cổ đông. Chạy setup_demo.js trước.")
        return

    # Bước 1: Chọn ví (không cần nhập địa chỉ thủ công)
    wallet_options = {
        f"{sh['name']} ({sh['address'][:8]}...)": sh["address"]
        for sh in shareholders
    }
    selected_name = st.selectbox("Chọn ví cổ đông:", list(wallet_options.keys()))
    wallet_addr   = wallet_options[selected_name]

    st.info(
        f"📍 Địa chỉ ví: `{wallet_addr}`\n\n"
        "Nhập private key để ký xác thực (không lưu lại, chỉ ký local)."
    )

    # Bước 2: Nhập private key để ký (chỉ trong môi trường Ganache/test)
    private_key = st.text_input(
        "Private Key (chỉ dùng cho Ganache — không dùng key thật):",
        type="password",
        help="Key chỉ được dùng để tạo chữ ký, không gửi lên server hay blockchain"
    )

    if st.button("🔏 Ký xác thực & Đăng nhập"):
        if not private_key:
            st.warning("Vui lòng nhập private key.")
            return

        with st.spinner("Đang xác thực..."):
            # Tạo challenge (OFF-CHAIN)
            challenge = generate_login_challenge(wallet_addr)

            # Ký challenge (OFF-CHAIN — private key không rời máy)
            try:
                signature = sign_challenge(challenge, private_key)
            except Exception as e:
                st.error(f"Lỗi ký: {e}")
                return

            # Verify chữ ký + kiểm tra tư cách on-chain
            result = verify_wallet_login(
                wallet_addr, challenge, signature,
                contracts["registry"]
            )

        if result["success"]:
            # Lưu vào session state
            st.session_state["wallet"]         = result["wallet"]
            st.session_state["wallet_name"]    = selected_name
            st.session_state["is_shareholder"] = result["is_shareholder"]
            st.session_state["can_vote"]       = result["can_vote"]
            st.session_state["tier"]           = result.get("tier", 0)
            st.session_state["private_key"]    = private_key  # chỉ lưu trong session RAM

            tier_labels = ["Nhỏ lẻ","Tổ chức","Chiến lược","Sáng lập"]
            tier_idx    = result.get("tier", 0)
            st.success(
                f"✅ Đăng nhập thành công!\n\n"
                f"**{selected_name}** | "
                f"Tier: {tier_labels[tier_idx]} | "
                f"Quyền vote: {'✅' if result['can_vote'] else '❌'}"
            )
            st.caption(
                "🔐 Xác thực: Chữ ký ECDSA verified (OFF-CHAIN) + "
                "canVote() confirmed (ON-CHAIN)"
            )
            st.rerun()
        else:
            st.error(f"❌ Đăng nhập thất bại: {result.get('error', 'Unknown')}")
