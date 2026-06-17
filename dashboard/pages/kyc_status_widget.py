"""
dashboard/pages/kyc_status_widget.py
Widget nhỏ hiển thị KYC status trong sidebar và trang Cổ đông.
"""
import streamlit as st
from web3 import Web3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from web3_helpers import get_kyc_status, check_can_vote_full


def render_kyc_badge(id_verifier, wallet: str):
    """Badge nhỏ hiển thị trạng thái KYC — dùng trong sidebar."""
    if not wallet or id_verifier is None:
        return
    kyc = get_kyc_status(id_verifier, wallet)
    if kyc.get("error"):
        return
    if kyc["canVoteKYC"]:
        st.sidebar.success(
            f"🪪 KYC: **{kyc['levelLabel']}** ✅\n\n"
            f"Còn {kyc['daysLeft']} ngày"
        )
    elif kyc.get("isRevoked"):
        st.sidebar.error("🪪 KYC: **Đã thu hồi** ❌")
    elif kyc.get("isExpired"):
        st.sidebar.warning("🪪 KYC: **Hết hạn** ⏰")
    else:
        st.sidebar.info("🪪 KYC: **Chưa xác thực**")


def render_vote_eligibility(contracts: dict, wallet: str):
    """
    Hiển thị đầy đủ điều kiện bỏ phiếu — dùng trên trang Bỏ phiếu.
    Check 4 điều kiện: Registry, Token, Delegate, KYC.
    """
    if not wallet:
        return
    result = check_can_vote_full(contracts, wallet)

    if result["canVote"]:
        st.success("✅ Đủ điều kiện bỏ phiếu")
        return

    st.error("❌ Chưa đủ điều kiện bỏ phiếu")
    checks = [
        ("Đăng ký cổ đông",   result["inRegistry"]),
        ("Có HST token",       result["hasToken"]),
        ("Đã kích hoạt VP",    result["hasDelegated"]),
        ("KYC hợp lệ",        result["kycValid"]),
    ]
    for label, ok in checks:
        icon = "✅" if ok else "❌"
        st.write(f"{icon} {label}")

    if result["hints"]:
        with st.expander("💡 Cách khắc phục"):
            for hint in result["hints"]:
                st.write(f"→ {hint}")
