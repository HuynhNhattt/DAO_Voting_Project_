"""
dashboard/app_kyc_patch.py
══════════════════════════════════════════════════════════════
HƯỚNG DẪN TÍCH HỢP KYC VÀO app.py HIỆN TẠI
Thêm đúng 4 chỗ:
══════════════════════════════════════════════════════════════
"""

# ══ CHỖ 1: Import (đầu app.py) ════════════════════════════════
IMPORT_CODE = """
from pages.kyc_page           import render_kyc_page
from pages.kyc_status_widget  import render_kyc_badge, render_vote_eligibility
from web3_helpers              import get_identity_verifier, load_addresses
"""

# ══ CHỖ 2: Load IdentityVerifier sau khi load contracts ═══════
LOAD_CODE = """
# Thêm sau dòng load contracts (get_all_contracts):
addrs      = load_addresses()
id_verifier = get_identity_verifier(w3, addrs)
contracts["id_verifier"] = id_verifier   # gắn vào contracts dict
"""

# ══ CHỖ 3: KYC badge trong sidebar ═══════════════════════════
SIDEBAR_CODE = """
# Thêm vào sidebar, sau khi hiển thị thông tin ví:
from pages.kyc_status_widget import render_kyc_badge
render_kyc_badge(id_verifier, wallet_address)
"""

# ══ CHỖ 4: Tab KYC ════════════════════════════════════════════
TAB_CODE = """
# Thêm tab "🪪 KYC" vào st.tabs([...])
# Và thêm nội dung:
with tab_kyc:
    render_kyc_page(
        contracts   = contracts,
        w3          = w3,
        wallet      = st.session_state.get("wallet_address"),
        private_key = st.session_state.get("private_key"),
        is_admin    = st.session_state.get("is_admin", False),
    )

# Trong tab Bỏ phiếu — thêm kiểm tra điều kiện đầy đủ:
from pages.kyc_status_widget import render_vote_eligibility
render_vote_eligibility(contracts, wallet_address)
"""

if __name__ == "__main__":
    print("=== HƯỚNG DẪN TÍCH HỢP KYC VÀO app.py ===\n")
    print("1. Import:\n", IMPORT_CODE)
    print("2. Load IdentityVerifier:\n", LOAD_CODE)
    print("3. Sidebar KYC badge:\n", SIDEBAR_CODE)
    print("4. Tab KYC:\n", TAB_CODE)
