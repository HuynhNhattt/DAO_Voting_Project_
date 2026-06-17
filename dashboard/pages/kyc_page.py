"""
dashboard/pages/kyc_page.py
══════════════════════════════════════════════════════════════
TRANG KYC — Xác thực danh tính thực tế

2 phần:
  [1] Form người dùng: điền thông tin CCCD → chờ Admin duyệt
  [2] Panel Admin: xem danh sách pending → ký approval → user submit

Thêm vào app.py:
    from pages.kyc_page import render_kyc_page
    with tab_kyc:
        render_kyc_page(contracts, w3, wallet, private_key, is_admin)
══════════════════════════════════════════════════════════════
"""

import streamlit as st
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from kyc_service    import KYCService, KYC_LEVEL, KYC_LEVEL_LABEL, submit_kyc_onchain
from web3_helpers   import get_contract, load_addresses
from web3           import Web3


# ── KYCService singleton (trong demo dùng session_state) ──────
def _get_kyc_service(chain_id: int = 1337) -> KYCService:
    """Lấy KYCService từ session state (giữ pending requests)."""
    if "kyc_service" not in st.session_state:
        # Trong demo: dùng private key của accounts[0] làm KYC signer
        # Trong production: đọc từ biến môi trường bảo mật
        signer_key = st.session_state.get("admin_private_key", "")
        if not signer_key:
            return None
        st.session_state["kyc_service"] = KYCService(signer_key, chain_id)
    return st.session_state["kyc_service"]


def render_kyc_page(contracts: dict, w3, wallet: str = None,
                    private_key: str = None, is_admin: bool = False):
    """Trang KYC chính — phân nhánh theo vai trò."""

    st.header("🪪 Xác thực Danh tính (KYC)")
    st.caption(
        "Xác thực danh tính on-chain: Admin ký approval off-chain → "
        "người dùng submit proof lên blockchain."
    )

    # ── Giải thích flow ──────────────────────────────────────
    with st.expander("📖 Tại sao cần KYC on-chain?", expanded=False):
        st.markdown("""
        **Vấn đề hiện tại (không có KYC thật):**
        - identityHash = `keccak256("DEMO_CCCD_0_0xABC...")` — hash giả
        - Không xác minh danh tính thật → ai cũng có thể đăng ký
        - Quadratic Voting dễ bị Sybil Attack (1 người, nhiều ví)

        **Giải pháp KYC on-chain:**
        - identityHash = `keccak256(tên thật + CCCD + ngày sinh)`
        - Admin xác minh giấy tờ thật → ký approval
        - 1 CCCD chỉ đăng ký được 1 ví → chặn Sybil Attack
        - KYC hết hạn sau 1 năm (tránh CCCD hết hạn)

        **Dữ liệu on-chain vs off-chain:**
        - ON-CHAIN: `identityHash` (hash, không lộ thông tin gốc)
        - OFF-CHAIN: Tên thật, số CCCD, ảnh giấy tờ (Admin giữ)
        """)

    # ── Kiểm tra IdentityVerifier ────────────────────────────
    addrs = load_addresses()
    id_verifier = None
    if addrs.get("identityVerifier"):
        try:
            id_verifier = get_contract(w3, "IdentityVerifier", addrs["identityVerifier"])
        except Exception:
            pass

    if id_verifier is None:
        st.warning(
            "⚠️ IdentityVerifier contract chưa được deploy.\n\n"
            "Chạy lại `setup_demo.js` để deploy với KYC support."
        )

    # Phân nhánh: User form / Admin panel
    tab_user, tab_admin, tab_status = st.tabs(["📝 Đăng ký KYC", "🔑 Admin Review", "📊 Trạng thái"])

    with tab_user:
        _render_user_kyc_form(contracts, w3, wallet, private_key, id_verifier)

    with tab_admin:
        _render_admin_panel(contracts, w3, wallet, private_key, id_verifier, is_admin)

    with tab_status:
        _render_kyc_status(w3, wallet, id_verifier)


def _render_user_kyc_form(contracts, w3, wallet, private_key, id_verifier):
    """Form người dùng điền thông tin KYC."""

    st.subheader("📝 Đăng ký xác thực danh tính")

    if not wallet:
        st.info("👆 Đăng nhập ví để đăng ký KYC.")
        return

    # Kiểm tra đã KYC chưa
    if id_verifier:
        try:
            rec = id_verifier.functions.getKYCRecord(
                Web3.to_checksum_address(wallet)
            ).call()
            if rec[6]:  # isVerified
                st.success(
                    f"✅ Ví này đã được xác thực KYC!\n\n"
                    f"Mức KYC: `{KYC_LEVEL_LABEL.get(rec[3], '?')}`  \n"
                    f"Hết hạn: `{_ts_to_str(rec[5])}`"
                )
                return
        except Exception:
            pass

    st.info(
        "**Quy trình:**\n"
        "1. Điền thông tin bên dưới\n"
        "2. Admin xác minh giấy tờ (1-2 ngày làm việc)\n"
        "3. Nhận approval → Submit lên blockchain"
    )

    with st.form("kyc_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input(
                "Họ và tên đầy đủ *",
                placeholder="NGUYEN VAN AN",
                help="Nhập chữ HOA, đúng như CCCD"
            )
            national_id = st.text_input(
                "Số CCCD / Hộ chiếu *",
                placeholder="012345678901"
            )
        with col2:
            dob = st.date_input(
                "Ngày sinh *",
                value=date(1990, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date(2006, 12, 31)
            )
            country = st.selectbox(
                "Quốc tịch",
                ["VN", "US", "SG", "JP", "KR", "Other"],
                index=0
            )

        kyc_level = st.radio(
            "Mức KYC yêu cầu",
            ["BASIC (Email + SĐT)", "STANDARD (CCCD)", "FULL (CCCD + Selfie)"],
            index=1,
            horizontal=True
        )
        level_map = {"BASIC (Email + SĐT)": 1, "STANDARD (CCCD)": 2, "FULL (CCCD + Selfie)": 3}
        selected_level = level_map[kyc_level]

        agree = st.checkbox(
            "Tôi đồng ý cho hệ thống xử lý thông tin định danh theo quy định bảo mật."
        )

        submitted = st.form_submit_button("📤 Gửi yêu cầu KYC", type="primary")

        if submitted:
            if not all([full_name, national_id, agree]):
                st.error("Vui lòng điền đầy đủ thông tin và đồng ý điều khoản.")
            else:
                kyc_svc = _get_kyc_service()
                if kyc_svc is None:
                    st.error("KYC Service chưa sẵn sàng — Admin cần đăng nhập trước.")
                else:
                    result = kyc_svc.submit_kyc_request(
                        wallet       = wallet,
                        full_name    = full_name,
                        national_id  = national_id,
                        date_of_birth= str(dob),
                        country      = country,
                        kyc_level    = selected_level,
                    )
                    st.success(
                        f"✅ Yêu cầu KYC đã được gửi!\n\n"
                        f"Request ID: `{result['requestId']}`\n\n"
                        f"Identity Hash (sẽ lưu on-chain): `{result['identityHash'][:30]}...`\n\n"
                        "Chờ Admin xác minh để nhận approval."
                    )
                    st.session_state["kyc_request_id"] = result["requestId"]

    # Nếu đã có approval → hiển thị nút Submit on-chain
    if "kyc_approval" in st.session_state and id_verifier:
        st.divider()
        st.subheader("🚀 Submit KYC lên Blockchain")
        approval = st.session_state["kyc_approval"]
        st.success("✅ Admin đã duyệt KYC của bạn!")
        st.write(f"Identity Hash: `{approval['identityHash'][:30]}...`")
        st.write(f"Mức KYC: `{KYC_LEVEL_LABEL.get(approval['level'], '?')}`")

        if st.button("⛓️ Submit KYC lên On-chain", type="primary"):
            if not private_key:
                st.error("Cần private key để ký transaction.")
            else:
                with st.spinner("Đang submit..."):
                    result = submit_kyc_onchain(w3, id_verifier, wallet, private_key, approval)
                if result.get("success"):
                    st.success(
                        f"✅ KYC đã được xác nhận on-chain!\n\n"
                        f"Tx: `{result['txHash'][:30]}...`\n"
                        f"Gas: {result.get('gasUsed', 'N/A')}"
                    )
                    del st.session_state["kyc_approval"]
                    st.balloons()
                else:
                    st.error(f"❌ Lỗi: {result.get('error')}")


def _render_admin_panel(contracts, w3, wallet, private_key, id_verifier, is_admin):
    """Admin panel để xem và duyệt KYC requests."""

    st.subheader("🔑 Admin KYC Review Panel")

    if not is_admin:
        st.warning("Chỉ Admin mới truy cập được panel này.")

        # Trong demo: cho phép nhập admin key
        with st.expander("Demo: Đăng nhập Admin"):
            admin_key = st.text_input("Admin Private Key (KYC Signer)", type="password")
            if st.button("Đăng nhập Admin") and admin_key:
                st.session_state["admin_private_key"] = admin_key
                st.session_state["is_admin"] = True
                st.rerun()
        return

    kyc_svc = _get_kyc_service()
    if kyc_svc is None:
        st.error("KYC Service chưa khởi tạo — cần admin private key.")
        return

    st.write(f"**KYC Signer:** `{kyc_svc.signer}`")

    pending = kyc_svc.get_pending_requests()

    if not pending:
        st.info("Không có yêu cầu KYC nào đang chờ duyệt.")
        return

    st.write(f"**{len(pending)} yêu cầu đang chờ:**")

    for req in pending:
        with st.expander(f"📋 {req['wallet'][:16]}... — {req.get('country', 'VN')} — Mức {req.get('kyc_level', '?')}"):
            st.write(f"Request ID: `{req['requestId']}`")
            st.write(f"Ví: `{req['wallet']}`")
            st.write(f"Identity Hash: `{req['identity_hash'][:30]}...`")
            st.write(f"Mức KYC: `{KYC_LEVEL_LABEL.get(req.get('kyc_level', 0), '?')}`")
            st.warning("⚠️ Admin cần xác minh giấy tờ thật trước khi duyệt!")

            col_approve, col_reject = st.columns(2)
            with col_approve:
                if st.button("✅ Duyệt", key=f"approve_{req['requestId']}"):
                    try:
                        approval = kyc_svc.approve_kyc(req["wallet"])
                        st.session_state["kyc_approval"] = approval
                        st.success(
                            f"✅ Đã ký approval!\n\n"
                            f"Signer: `{approval['signer'][:20]}...`\n"
                            "Người dùng có thể submit on-chain."
                        )
                        # Hiển thị dữ liệu để submit
                        with st.expander("📄 Dữ liệu submit on-chain"):
                            st.json({
                                "identityHash":   approval["identityHash"],
                                "kycHash":        approval["kycHash"],
                                "level":          approval["level"],
                                "nonce":          approval["nonce"],
                                "country":        approval["country"],
                                "adminSignature": approval["adminSignature"][:30] + "...",
                            })
                    except Exception as e:
                        st.error(str(e))

            with col_reject:
                reason = st.text_input("Lý do từ chối", key=f"reason_{req['requestId']}")
                if st.button("❌ Từ chối", key=f"reject_{req['requestId']}"):
                    if reason:
                        kyc_svc.reject_kyc(req["wallet"], reason)
                        st.warning(f"Đã từ chối KYC: {reason}")
                    else:
                        st.error("Cần nhập lý do từ chối.")


def _render_kyc_status(w3, wallet: str, id_verifier):
    """Hiển thị trạng thái KYC của ví đang đăng nhập."""

    st.subheader("📊 Trạng thái KYC")

    if not wallet:
        st.info("Đăng nhập ví để xem trạng thái KYC.")
        return

    if id_verifier is None:
        st.warning("IdentityVerifier chưa deploy.")
        return

    try:
        status = id_verifier.functions.getKYCStatus(
            Web3.to_checksum_address(wallet)
        ).call()

        is_verified, is_expired, is_revoked, level, expires_at, days_left = status

        if not is_verified and not is_revoked:
            st.info("Ví này chưa có KYC. Sử dụng tab 'Đăng ký KYC' để bắt đầu.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            if is_verified and not is_expired:
                st.metric("Trạng thái", "✅ Hợp lệ")
            elif is_expired:
                st.metric("Trạng thái", "⏰ Hết hạn")
            elif is_revoked:
                st.metric("Trạng thái", "❌ Đã thu hồi")

        with col2:
            st.metric("Mức KYC", KYC_LEVEL_LABEL.get(level, "?"))

        with col3:
            st.metric("Còn lại", f"{days_left} ngày")

        if expires_at > 0:
            st.write(f"Hết hạn: `{_ts_to_str(expires_at)}`")

        # Kiểm tra on-chain
        record = id_verifier.functions.getKYCRecord(
            Web3.to_checksum_address(wallet)
        ).call()
        id_hash = "0x" + record[1].hex() if record[1] else "N/A"
        kyc_hash = "0x" + record[2].hex() if record[2] else "N/A"

        with st.expander("🔍 Chi tiết on-chain"):
            st.write(f"Identity Hash: `{id_hash[:40]}...`")
            st.write(f"KYC Hash: `{kyc_hash[:40]}...`")
            st.write(f"Quốc tịch: `{record[8] if len(record) > 8 else 'N/A'}`")
            st.caption(
                "Identity Hash lưu on-chain nhưng không lộ thông tin cá nhân. "
                "Chỉ Admin mới biết hash này tương ứng với ai."
            )

    except Exception as e:
        st.error(f"Lỗi đọc KYC status: {e}")


def _ts_to_str(ts: int) -> str:
    """Convert Unix timestamp → chuỗi ngày giờ."""
    from datetime import datetime
    try:
        return datetime.fromtimestamp(ts).strftime("%H:%M %d/%m/%Y")
    except Exception:
        return str(ts)
