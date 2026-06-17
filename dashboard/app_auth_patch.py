"""
dashboard/app_auth_patch.py
══════════════════════════════════════════════════════════════
HƯỚNG DẪN CẬP NHẬT app.py — Thay private key bằng ký số

Đây là file mô tả đầy đủ những gì cần thêm/sửa trong app.py.
Áp dụng theo thứ tự từ trên xuống.
══════════════════════════════════════════════════════════════
"""

# ══ PHẦN 1: THAY THẾ IMPORTS Ở ĐẦU FILE ══════════════════════
IMPORTS_NEW = """
# --- Imports bảo mật (Feature 3) ---
from pages.login_page import (
    render_login_sidebar,
    is_logged_in,
    get_session_wallet,
    get_session_private_key,
    clear_private_key,
    safe_send_tx,
    require_login,
)
from auth_service import get_challenge_manager, get_session_manager
"""

# ══ PHẦN 2: XÓA ĐOẠN CŨ NHẬP PRIVATE KEY TRONG SIDEBAR ══════
# Tìm và XÓA đoạn code cũ này (hoặc comment lại):
OLD_SIDEBAR_CODE = """
# ===== XÓA ĐOẠN NÀY =====
st.sidebar.subheader("Đồng nhập ví")
wallet_addr = st.sidebar.text_input("Địa chỉ ví (0x...)")
private_key = st.sidebar.text_input("Private Key", type="password")
if st.sidebar.button("Kết nối"):
    st.session_state["wallet_address"] = wallet_addr
    st.session_state["private_key"]    = private_key
# ===== KẾT THÚC ĐOẠN XÓA =====
"""

# ══ PHẦN 3: THÊM LOGIN MỚI VÀO SIDEBAR ═══════════════════════
NEW_SIDEBAR_CODE = """
# --- Đăng nhập an toàn (thay thế nhập private key) ---
# Lưu addresses để dropdown chọn nhanh
try:
    st.session_state["contract_addresses"] = load_addresses()
except Exception:
    pass

render_login_sidebar(contracts, w3)

# Lấy thông tin từ session (thay vì từ textbox)
wallet_address = get_session_wallet()
"""

# ══ PHẦN 4: THAY THẾ MỌI CHỖ DÙNG private_key ════════════════
# Tìm tất cả chỗ dùng st.session_state["private_key"] và thay bằng:
REPLACE_PRIVATE_KEY = """
# TRƯỚC (không an toàn):
private_key = st.session_state.get("private_key")
result = build_tx(w3, fn, wallet, private_key)

# SAU (an toàn):
result = safe_send_tx(w3, fn)
# safe_send_tx() tự lấy key từ session, dùng xong xóa ngay
"""

# ══ PHẦN 5: BẢO VỆ CÁC TRANG CẦN ĐĂNG NHẬP ══════════════════
PROTECT_PAGES = """
# Trước mỗi trang cần đăng nhập, thêm check:
with tab_vote:
    if not is_logged_in():
        st.warning("🔒 Vui lòng đăng nhập để bỏ phiếu.")
    else:
        # ... nội dung trang bỏ phiếu ...
        pass

# Hoặc dùng decorator:
@require_login
def render_vote_content(contracts, w3):
    # ... logic bỏ phiếu ...
    pass
"""

# ══ PHẦN 6: XÓA PRIVATE KEY SAU MỖI TRANSACTION ══════════════
CLEAR_KEY = """
# Sau mỗi transaction quan trọng, có thể xóa key khỏi session:
# (Tùy chọn — nếu muốn user ký lại mỗi lần)
clear_private_key()
"""

if __name__ == "__main__":
    print("Xem file này để biết cách cập nhật app.py")
