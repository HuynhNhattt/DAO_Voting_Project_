"""
dashboard/app_timelock_patch.py
══════════════════════════════════════════════════════════════
HƯỚNG DẪN TÍCH HỢP TIMELOCK VÀO app.py HIỆN TẠI

Thêm đúng 3 chỗ sau vào app.py:
══════════════════════════════════════════════════════════════
"""

# ══ CHỖ 1: Import (thêm vào đầu app.py cùng các import khác) ══
IMPORT_CODE = """
from pages.timelock_page import render_timelock_page, render_timelock_demo_controls
"""

# ══ CHỖ 2: Thêm tab "⏳ Timelock" vào danh sách tabs ══════════
# Tìm dòng có st.tabs([...]) trong app.py và thêm "⏳ Timelock"
# Ví dụ:
TABS_CODE = """
tab_home, tab_vote, tab_shareholders, tab_analysis, tab_cert, tab_timelock, tab_info, tab_guide = st.tabs([
    "🏠 Tổng quan",
    "🗳️ Bỏ phiếu",
    "👥 Cổ đông",
    "📊 Phân tích",
    "📄 Biên bản",
    "⏳ Timelock",      # ← THÊM TAB NÀY
    "⛓️ On/Off-chain",
    "📖 Hướng dẫn",
])
"""

# ══ CHỖ 3: Nội dung tab Timelock ══════════════════════════════
TAB_CONTENT_CODE = """
with tab_timelock:
    render_timelock_page(
        contracts=contracts,
        w3=w3,
        wallet=st.session_state.get("wallet_address"),
        private_key=st.session_state.get("private_key"),
    )

    # Demo controls chỉ hiển thị trên Ganache
    if st.session_state.get("network", "ganache") == "ganache":
        st.divider()
        render_timelock_demo_controls(
            contracts=contracts,
            w3=w3,
            wallet=st.session_state.get("wallet_address"),
            private_key=st.session_state.get("private_key"),
        )
"""

# ══ CHỖ 4: Cập nhật web3_helpers.py để đọc status mới ════════
# Thêm 2 status mới vào STATUS_LABELS trong hàm get_campaign_data()
STATUS_UPDATE = """
# Trong web3_helpers.py, hàm get_campaign_data(), thay:
STATUS_LABELS = [
    "DRAFT", "ACTIVE", "COMMIT", "REVEAL",
    "TALLYING", "EXECUTED", "DEFEATED", "CANCELLED"
]

# Thành:
STATUS_LABELS = [
    "DRAFT", "ACTIVE", "COMMIT", "REVEAL",
    "TALLYING", "EXECUTED", "DEFEATED", "CANCELLED",
    "QUEUED",       # ← MỚI — đã thông qua, đang chờ Timelock
    "EXECUTABLE",   # ← MỚI — delay xong, sẵn sàng execute
]
"""

if __name__ == "__main__":
    print("=== HƯỚNG DẪN TÍCH HỢP TIMELOCK ===\n")
    print("1. Import:")
    print(IMPORT_CODE)
    print("2. Tabs:")
    print(TABS_CODE)
    print("3. Tab content:")
    print(TAB_CONTENT_CODE)
    print("4. Update STATUS_LABELS:")
    print(STATUS_UPDATE)
