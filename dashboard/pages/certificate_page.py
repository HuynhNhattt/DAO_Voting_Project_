"""
dashboard/pages/certificate_page.py
════════════════════════════════════════════════════════════════
TRANG BIÊN BẢN CHỮ KÝ SỐ
Nhận xét thầy #3: Biên bản chữ ký số sau khi finalize
Nhận xét thầy #4: Giải thích On-chain / Off-chain

Cách dùng — thêm vào app.py:
    from pages.certificate_page import render_certificate_page, render_onchain_offchain_tab
    # Trong phần tabs của app.py:
    with tab_cert:
        render_certificate_page(contracts, w3)
    with tab_info:
        render_onchain_offchain_tab()
════════════════════════════════════════════════════════════════
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path

# Import helpers
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from web3_helpers import (
    get_all_campaigns, get_certificate, verify_certificate,
    get_all_certificates
)


# ─── Trang Biên bản (Nhận xét thầy #3) ───────────────────────
def render_certificate_page(contracts: dict, w3):
    """
    Hiển thị trang Biên bản chữ ký số.
    Đọc dữ liệu từ VotingCertificate contract (ON-CHAIN).
    """
    st.header("📄 Biên bản Chữ ký số")
    st.caption("Biên bản được tạo tự động on-chain sau khi finalize — không thể làm giả")

    cert_contract = contracts.get("cert")

    if cert_contract is None:
        st.warning(
            "⚠️ VotingCertificate contract chưa được tích hợp.\n\n"
            "Chạy lại `setup_demo.js` để deploy contract mới."
        )
        return

    # ── Danh sách tất cả biên bản ────────────────────────────
    all_certs = get_all_certificates(cert_contract)

    if not all_certs:
        st.info(
            "Chưa có biên bản nào.\n\n"
            "Biên bản được tạo tự động sau khi gọi `finalizeCampaign()`."
        )

        # Gợi ý finalize
        gov = contracts.get("gov")
        if gov:
            campaigns = get_all_campaigns(gov)
            finalized_able = [
                c for c in campaigns
                if c["status"] in ("ACTIVE", "REVEAL")
            ]
            if finalized_able:
                st.write("**Chiến dịch có thể finalize:**")
                for c in finalized_able:
                    st.write(f"- #{c['id']} {c['title']} ({c['status']})")
        return

    # ── Tổng quan ────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    passed_count = sum(1 for c in all_certs if c["passed"])
    with col1:
        st.metric("Tổng biên bản", len(all_certs))
    with col2:
        st.metric("✅ Thông qua", passed_count)
    with col3:
        st.metric("❌ Không đạt", len(all_certs) - passed_count)

    st.divider()

    # ── Chọn biên bản để xem ─────────────────────────────────
    cert_options = {
        f"#{c['campaignId']} — {c['campaignTitle']} ({c['result']})": c
        for c in all_certs
    }
    selected_key = st.selectbox("Chọn chiến dịch để xem biên bản:", list(cert_options.keys()))
    cert = cert_options[selected_key]

    # ── Hiển thị biên bản chi tiết ───────────────────────────
    _render_certificate_detail(cert, cert_contract)


def _render_certificate_detail(cert: dict, cert_contract):
    """Hiển thị chi tiết một biên bản."""
    finalized_dt = datetime.fromtimestamp(cert["finalizedAt"])

    # ── Header kết quả ───────────────────────────────────────
    if cert["passed"]:
        st.success(f"## ✅ THÔNG QUA (PASS) — #{cert['campaignId']} {cert['campaignTitle']}")
    else:
        st.error(f"## ❌ KHÔNG ĐẠT (DEFEAT) — #{cert['campaignId']} {cert['campaignTitle']}")

    # ── Thông tin cơ bản ─────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Thông tin chiến dịch:**")
        st.write(f"- Loại đề xuất: `{cert['proposalType']}`")
        st.write(f"- Cơ chế tính phiếu: `{cert['mechanism']}`")
        st.write(f"- Block snapshot: `#{cert['snapshotBlock']}`")
        st.write(f"- Thời điểm ký: `{finalized_dt.strftime('%H:%M:%S %d/%m/%Y')}`")
        st.write(f"- Người ký (ví): `{cert['finalizedBy'][:20]}...`")
    with col2:
        st.write("**Ngưỡng xét kết quả:**")
        st.write(f"- Quorum yêu cầu: `{cert['quorumPct']:.0f}%`")
        st.write(f"- Quorum thực tế: `{cert['participationPct']:.1f}%` "
                 + ("✅" if cert["participationPct"] >= cert["quorumPct"] else "❌"))
        st.write(f"- Ngưỡng thông qua: `{cert['passThreshold']:.0f}%`")
        st.write(f"- Tỷ lệ FOR: `{cert['forPct']:.1f}%` "
                 + ("✅" if cert["passed"] else "❌"))

    # ── Biểu đồ phiếu bầu ───────────────────────────────────
    st.write("**Kết quả bỏ phiếu:**")
    total_decisive = cert["forVotes"] + cert["againstVotes"]
    col_f, col_a, col_abs = st.columns(3)
    with col_f:
        st.metric("✅ Tán thành (FOR)",
                  f"{cert['forVotes']:,.0f} HST",
                  f"{cert['forPct']:.1f}%")
    with col_a:
        st.metric("❌ Phản đối (AGAINST)",
                  f"{cert['againstVotes']:,.0f} HST")
    with col_abs:
        st.metric("⬜ Bỏ trắng (ABSTAIN)",
                  f"{cert['abstainVotes']:,.0f} HST")

    st.metric("👥 Số cổ đông tham gia", f"{cert['totalParticipants']} người")

    # ── Chữ ký số (ON-CHAIN) ─────────────────────────────────
    st.divider()
    st.write("**🔐 Chữ ký số (ON-CHAIN — bất biến):**")

    with st.expander("Xem Certificate Hash và xác minh tính toàn vẹn"):
        st.code(cert["certificateHash"], language="text")

        # Verify on-chain
        if st.button("🔍 Xác minh hash trên blockchain", key=f"verify_{cert['campaignId']}"):
            with st.spinner("Đang kiểm tra..."):
                result = verify_certificate(cert_contract, cert["campaignId"])
            if result["isValid"]:
                st.success(result["message"])
                st.write(f"Hash lưu   : `{result['storedHash'][:40]}...`")
                st.write(f"Hash tính lại: `{result['computedHash'][:40]}...`")
            else:
                st.error(result["message"])

        st.caption(
            "💡 **Cách xác minh thủ công:**\n"
            "1. Mở Ganache → Contracts → VotingCertificate\n"
            f"2. Gọi `getCertificate({cert['campaignId']})`\n"
            "3. So sánh certificateHash với giá trị trên\n"
            "4. Nếu khớp → biên bản chưa bị sửa ✅"
        )

    # ── Export biên bản ──────────────────────────────────────
    st.write("**📥 Xuất biên bản:**")
    col_json, col_text = st.columns(2)

    cert_json = json.dumps(cert, indent=2, ensure_ascii=False)
    with col_json:
        st.download_button(
            label="⬇️ Tải JSON",
            data=cert_json,
            file_name=f"certificate_campaign{cert['campaignId']}.json",
            mime="application/json",
        )

    # Tạo text biên bản
    cert_text = _build_certificate_text(cert)
    with col_text:
        st.download_button(
            label="⬇️ Tải TXT (In được)",
            data=cert_text,
            file_name=f"certificate_campaign{cert['campaignId']}.txt",
            mime="text/plain",
        )

    # Preview biên bản text
    with st.expander("👁️ Preview biên bản text"):
        st.text(cert_text)


def _build_certificate_text(cert: dict) -> str:
    """Tạo nội dung biên bản dạng text có thể in."""
    dt = datetime.fromtimestamp(cert["finalizedAt"])
    result_str = "✅ THÔNG QUA (PASS)" if cert["passed"] else "❌ KHÔNG ĐẠT (DEFEAT)"

    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║         BIÊN BẢN KẾT QUẢ BIỂU QUYẾT CỔ ĐÔNG                ║",
        "║       (Biên bản điện tử lưu trên Blockchain)                 ║",
        "╚══════════════════════════════════════════════════════════════╝",
        "",
        f"  Chiến dịch   : #{cert['campaignId']} — {cert['campaignTitle']}",
        f"  Loại đề xuất : {cert['proposalType']}",
        f"  Cơ chế phiếu : {cert['mechanism']}",
        f"  Block snapshot: #{cert['snapshotBlock']}",
        "",
        "── KẾT QUẢ ─────────────────────────────────────────────────────",
        f"  Kết quả      : {result_str}",
        f"  Tán thành    : {cert['forVotes']:>15,.2f} HST  ({cert['forPct']:.1f}%)",
        f"  Phản đối     : {cert['againstVotes']:>15,.2f} HST",
        f"  Bỏ trắng     : {cert['abstainVotes']:>15,.2f} HST",
        f"  Tham gia     : {cert['participationPct']:.1f}% (yêu cầu: {cert['quorumPct']:.0f}%)",
        f"  Số cổ đông   : {cert['totalParticipants']} người",
        "",
        "── CHỮ KÝ SỐ (ON-CHAIN) ─────────────────────────────────────────",
        f"  Người ký     : {cert['finalizedBy']}",
        f"  Thời điểm    : {dt.strftime('%H:%M:%S %d/%m/%Y')}",
        f"  Certificate Hash:",
        f"    {cert['certificateHash']}",
        "",
        "── XÁC MINH ─────────────────────────────────────────────────────",
        "  Bất kỳ ai cũng có thể xác minh biên bản này trên blockchain.",
        "  Hash trên là bằng chứng không thể làm giả.",
        "",
        "═" * 66,
        "  Tài liệu được tạo tự động từ dữ liệu on-chain.",
        "  Nội dung được bảo đảm bởi công nghệ Blockchain (Ethereum/Polygon).",
        "═" * 66,
    ]
    return "\n".join(lines)


# ─── Tab On-chain / Off-chain (Nhận xét thầy #4) ─────────────
def render_onchain_offchain_tab():
    """
    Tab giải thích rõ on-chain vs off-chain.
    Thêm vào sidebar hoặc tab Hướng dẫn trong app.py.
    """
    st.header("⛓️ On-chain vs Off-chain")
    st.caption("Giải thích rõ dữ liệu nào nằm trên blockchain, dữ liệu nào ở ngoài")

    # ── Định nghĩa ────────────────────────────────────────────
    col_on, col_off = st.columns(2)

    with col_on:
        st.subheader("⛓️ ON-CHAIN")
        st.success(
            "**Lưu trên Blockchain**\n\n"
            "✅ Bất biến — không thể sửa\n"
            "✅ Công khai — ai cũng đọc được\n"
            "✅ Phi tập trung — không server trung tâm\n"
            "✅ Tự thực thi — logic chạy tự động\n\n"
            "❌ Tốn gas (phí giao dịch)\n"
            "❌ Không lưu file lớn"
        )

    with col_off:
        st.subheader("💻 OFF-CHAIN")
        st.info(
            "**Lưu ngoài Blockchain**\n\n"
            "✅ Miễn phí khi lưu\n"
            "✅ Lưu file lớn (PDF, ảnh)\n"
            "✅ Xử lý nhanh\n\n"
            "❌ Có thể bị sửa\n"
            "❌ Phụ thuộc server\n\n"
            "→ Giải pháp: dùng **hash** để anchor với on-chain"
        )

    st.divider()

    # ── Bản đồ chi tiết ──────────────────────────────────────
    st.subheader("📍 Bản đồ dữ liệu hệ thống")

    on_chain_items = [
        ("Số dư HST token",        "HSTToken.balanceOf()",        "Xác định quyền sở hữu — không thể làm giả"),
        ("Lịch sử voting power",   "HSTToken.getPastVotes()",     "Chống thao túng: mua token sau snapshot không tính"),
        ("Tư cách cổ đông (hash)", "ShareholderRegistry.registry[]","Hash CCCD — bảo vệ quyền riêng tư, vẫn verify được"),
        ("Chiến dịch biểu quyết",  "GovernanceContract.campaigns[]","Quy tắc không thể thay đổi sau khi tạo"),
        ("Từng lá phiếu",          "GovernanceContract (VoteCast event)","Mỗi phiếu = 1 tx không thể xóa"),
        ("Kết quả (PASS/DEFEAT)",  "GovernanceContract.status",   "Tính tự động — không qua admin"),
        ("Biên bản chữ ký số",     "VotingCertificate.certificates[]","Hash toàn bộ biên bản — verify được"),
    ]

    off_chain_items = [
        ("Tên thật cổ đông",       "contract_addresses.json",     "⚠️ Nhạy cảm — cần bảo vệ riêng"),
        ("CCCD / giấy tờ gốc",     "Lưu nội bộ công ty",          "⚠️ Quá lớn và nhạy cảm để lưu on-chain"),
        ("Private key",            "file .env / ví cứng",         "⚠️ NGUY HIỂM — lộ = mất toàn bộ tài sản"),
        ("Dashboard Streamlit",    "Server chạy app.py",          "Server down → không xem được, nhưng data on-chain vẫn còn"),
        ("File biên bản PDF/JSON", "dashboard/certificates/",     "Có thể bị sửa, nhưng hash sẽ không khớp → dễ phát hiện"),
        ("ABI contract",           "artifacts/contracts/*.json",  "Giao thức gọi hàm — do Hardhat compile ra"),
        ("contract_addresses.json","dashboard/",                  "Config địa chỉ — nếu bị sửa sai → không connect được"),
    ]

    # Bảng ON-CHAIN
    st.write("**⛓️ Dữ liệu ON-CHAIN:**")
    for what, where, why in on_chain_items:
        with st.expander(f"✅ {what}"):
            st.write(f"**Lưu tại:** `{where}`")
            st.write(f"**Tại sao:** {why}")

    st.divider()

    # Bảng OFF-CHAIN
    st.write("**💻 Dữ liệu OFF-CHAIN:**")
    for what, where, why in off_chain_items:
        with st.expander(f"📄 {what}"):
            st.write(f"**Lưu tại:** `{where}`")
            st.write(f"**Ghi chú:** {why}")

    st.divider()

    # ── Nguyên tắc kết nối ───────────────────────────────────
    st.subheader("🔗 Cách On-chain và Off-chain kết nối")
    st.markdown("""
    ```
    OFF-CHAIN                    ON-CHAIN
    ─────────                    ────────
    Tên: "Nguyễn Văn A"  ──→    Địa chỉ ví: 0x7Cdd...
    CCCD: 012345678       ──→    identityHash: keccak256(CCCD)
    File biên bản (PDF)   ──→    certificateHash: keccak256(data)
    Private key           ──→    Chữ ký ECDSA trên transaction
    ```
    **Nguyên tắc:** Thông tin nhạy cảm/lớn lưu off-chain,
    **hash** của nó lưu on-chain → có thể verify mà không lộ dữ liệu gốc.
    """)

    # ── Ví dụ thực tế ────────────────────────────────────────
    st.subheader("🏢 Ánh xạ với quy trình ĐHCĐ truyền thống")
    mapping = {
        "Ban tổ chức phát hành tờ phiếu":    "createCampaign() — ON-CHAIN",
        "Chốt danh sách cổ đông":            "snapshotBlock = block.number — ON-CHAIN",
        "Cổ đông bỏ phiếu (đánh dấu, ký)":  "castVote() + ECDSA signature — ON-CHAIN",
        "Nhân viên kiểm tra CMND":           "registry.canVote() — ON-CHAIN",
        "Thu phiếu, đếm thủ công":           "_recordVote() tự động — ON-CHAIN",
        "Công bố kết quả":                   "finalizeCampaign() — ON-CHAIN",
        "Thư ký ký biên bản":                "VotingCertificate.issueCertificate() — ON-CHAIN",
        "In biên bản giấy, lưu hồ sơ":      "certificate_generator.py — OFF-CHAIN",
    }
    for traditional, blockchain in mapping.items():
        col_t, col_b = st.columns([1, 1])
        with col_t:
            st.write(f"📋 {traditional}")
        with col_b:
            if "ON-CHAIN" in blockchain:
                st.success(f"⛓️ {blockchain}")
            else:
                st.info(f"💻 {blockchain}")
