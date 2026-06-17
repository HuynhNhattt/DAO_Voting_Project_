"""
dashboard/pages/login_page.py — Đăng nhập bằng ký số
"""
import streamlit as st
from web3 import Web3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from auth_service    import challenges, sessions, sign_message, sign_and_send
from web3_helpers    import get_shareholder_info


def is_logged_in() -> bool:
    return sessions().get(st.session_state.get("_token")) is not None


def get_wallet() -> str | None:
    return sessions().wallet(st.session_state.get("_token"))


def get_pk() -> str | None:
    """Private key chỉ tồn tại trong RAM session state."""
    return st.session_state.get("_pk")


def clear_pk():
    st.session_state.pop("_pk", None)


def safe_tx(w3, fn_call, show: bool = True) -> dict:
    """Gửi transaction từ session hiện tại."""
    if not is_logged_in():
        return {"success": False, "error": "Chưa đăng nhập"}
    pk = get_pk()
    if not pk:
        if show:
            st.error("Không có private key trong session. Đăng nhập lại.")
        return {"success": False, "error": "no key"}
    result = sign_and_send(w3, fn_call, get_wallet(), pk)
    if show:
        if result["success"]:
            st.success(f"✅ Thành công! Tx: `{result['txHash'][:24]}...`")
        else:
            st.error(f"❌ {result.get('error', 'Unknown error')}")
    return result


def render_login_sidebar(contracts: dict, w3):
    st.sidebar.markdown("---")
    if is_logged_in():
        _show_logged_in()
    else:
        _show_login_form(contracts)


def _show_logged_in():
    wallet = get_wallet()
    short  = f"{wallet[:8]}...{wallet[-6:]}" if wallet else "?"
    st.sidebar.success(f"🔐 **{short}**")

    token = st.session_state.get("_token")
    s     = sessions().get(token)
    if s:
        left = int((s["expires"] - __import__("time").time()) / 60)
        st.sidebar.caption(f"Session còn {left} phút")

    if st.sidebar.button("🚪 Đăng xuất"):
        sessions().destroy(token)
        for k in ["_token", "_pk", "wallet_address", "shareholder_info", "is_admin", "_challenge"]:
            st.session_state.pop(k, None)
        st.rerun()


def _show_login_form(contracts: dict):
    st.sidebar.subheader("🔑 Đăng nhập")

    # Chọn nhanh từ danh sách cổ đông demo
    addrs  = st.session_state.get("contract_addresses", {})
    sh_list = addrs.get("shareholders", [])
    wallet  = ""

    if sh_list:
        opts = ["-- chọn ví --"] + [f"{s['name']}" for s in sh_list]
        sel  = st.sidebar.selectbox("Cổ đông:", opts, key="sh_select")
        if sel != "-- chọn ví --":
            idx    = opts.index(sel) - 1
            wallet = sh_list[idx]["address"]

    wallet = st.sidebar.text_input("Hoặc nhập địa chỉ ví:", value=wallet, key="wallet_inp")

    if not wallet.startswith("0x") or len(wallet) != 42:
        return

    try:
        wallet_cs = Web3.to_checksum_address(wallet)
    except Exception:
        st.sidebar.error("Địa chỉ không hợp lệ")
        return

    # Bước 1: tạo challenge
    if st.sidebar.button("📋 Tạo challenge", key="btn_challenge"):
        ch = challenges().create(wallet_cs)
        st.session_state["_challenge"] = ch
        st.session_state["_chal_wallet"] = wallet_cs

    ch = st.session_state.get("_challenge")
    if not ch or st.session_state.get("_chal_wallet", "").lower() != wallet_cs.lower():
        return

    import time
    left = int((ch["expires"] - time.time()) / 60)
    if left <= 0:
        st.sidebar.warning("Challenge hết hạn. Tạo lại.")
        st.session_state.pop("_challenge", None)
        return

    st.sidebar.caption(f"⏱ Challenge hết hạn sau {left} phút")

    with st.sidebar.expander("📄 Message cần ký"):
        st.code(ch["message"])

    # Bước 2: ký
    with st.sidebar.expander("🔐 Ký bằng private key (demo)"):
        st.caption("Production: dùng MetaMask để ký message trên")
        pk = st.text_input("Private key:", type="password", key="pk_inp")
        if st.button("✍️ Ký & Đăng nhập", key="btn_sign") and pk:
            _do_login(wallet_cs, ch["message"], sign_message(ch["message"], pk), pk, contracts)

    with st.sidebar.expander("📝 Dán signature từ MetaMask"):
        sig = st.text_area("Signature:", key="sig_inp", height=80)
        if st.button("✅ Xác nhận", key="btn_sig") and sig:
            _do_login(wallet_cs, ch["message"], sig, None, contracts)


def _do_login(wallet: str, message: str, signature: str, pk: str | None, contracts: dict):
    result = challenges().verify(wallet, signature)
    if not result["ok"]:
        st.sidebar.error(result["msg"])
        return

    registry = contracts.get("registry")
    info     = get_shareholder_info(registry, wallet) if registry else {}
    token    = sessions().create(wallet, info)

    st.session_state["_token"]          = token
    st.session_state["wallet_address"]  = wallet
    st.session_state["shareholder_info"] = info
    st.session_state["is_admin"]        = info.get("tier", 0) >= 3
    if pk:
        st.session_state["_pk"] = pk  # RAM only, không persist

    st.session_state.pop("_challenge",    None)
    st.session_state.pop("_chal_wallet",  None)
    st.sidebar.success("✅ Đăng nhập thành công!")
    st.rerun()
