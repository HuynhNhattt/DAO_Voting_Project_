"""
utils/on_off_chain_explainer.py
═══════════════════════════════════════════════════════════════
NHẬN XÉT THẦY #4: Giải thích On-chain / Off-chain rõ hơn
═══════════════════════════════════════════════════════════════

Module này cung cấp:
  1. Bản đồ rõ ràng: thứ gì nằm ON-CHAIN, thứ gì OFF-CHAIN
  2. Hàm kiểm tra trạng thái thực tế của hệ thống
  3. Tổng hợp dữ liệu để Dashboard hiển thị phần giải thích

── ĐỊNH NGHĨA ─────────────────────────────────────────────────

ON-CHAIN:
  Dữ liệu lưu trong smart contract trên blockchain.
  Đặc điểm:
    ✅ Bất biến — không thể sửa sau khi ghi
    ✅ Công khai — ai cũng đọc được
    ✅ Phi tập trung — không có máy chủ trung tâm
    ✅ Tự thực thi — logic chạy tự động, không cần admin
    ❌ Tốn gas (phí giao dịch) khi ghi
    ❌ Không thể lưu file lớn (hình ảnh, PDF)

OFF-CHAIN:
  Dữ liệu lưu bên ngoài blockchain (server, máy tính cá nhân).
  Đặc điểm:
    ✅ Miễn phí khi lưu (không tốn gas)
    ✅ Lưu được dữ liệu lớn (PDF, hình ảnh)
    ✅ Xử lý nhanh (không cần xác nhận block)
    ❌ Có thể bị sửa nếu không bảo vệ
    ❌ Phụ thuộc vào server/người vận hành
    → Giải pháp: dùng hash để anchor với on-chain
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from web3 import Web3
from web3_helpers import connect_web3, get_all_contracts, load_addresses


# ─── Bản đồ On-chain / Off-chain của hệ thống ─────────────────
SYSTEM_DATA_MAP = {
    "ON_CHAIN": {
        "description": "Dữ liệu lưu trên Blockchain — bất biến, công khai",
        "items": [
            {
                "what": "Số dư HST token của từng ví",
                "where": "HSTToken contract — balanceOf(address)",
                "why": "Xác định quyền sở hữu cổ phần không thể làm giả",
                "example": "0x7Cdd... có 4,500,000 HST = 45% cổ phần"
            },
            {
                "what": "Lịch sử voting power (checkpoint)",
                "where": "HSTToken contract — getPastVotes(address, block)",
                "why": "Chống thao túng: mua token sau snapshot không được tính",
                "example": "Tại block #423, ví A có 1,500,000 voting power"
            },
            {
                "what": "Thông tin danh tính cổ đông (dạng hash)",
                "where": "ShareholderRegistry contract — registry[address]",
                "why": "Bảo vệ quyền riêng tư: không lưu tên thật trực tiếp",
                "example": "identityHash = keccak256('CCCD_012345678')"
            },
            {
                "what": "Tư cách biểu quyết (canVote)",
                "where": "ShareholderRegistry contract — canVote(address)",
                "why": "Kiểm soát ai được phép bỏ phiếu (chưa bị khóa, đang active)",
                "example": "registry.canVote(0x7Cdd...) = true/false"
            },
            {
                "what": "Chiến dịch biểu quyết và tham số",
                "where": "GovernanceContract — campaigns[campaignId]",
                "why": "Quy tắc không thể bị thay đổi sau khi tạo chiến dịch",
                "example": "Campaign #1: passThreshold=50%, quorum=10%, deadline=..."
            },
            {
                "what": "Từng lá phiếu bầu",
                "where": "GovernanceContract — VoteCast event + ballots mapping",
                "why": "Mỗi phiếu được ghi vĩnh viễn, không thể xóa hay sửa",
                "example": "VoteCast: campaign=1, voter=0x7Cdd..., FOR, weight=4500000"
            },
            {
                "what": "Kết quả chiến dịch (PASS/DEFEAT)",
                "where": "GovernanceContract — campaign.status",
                "why": "Kết quả được tính và lưu tự động, không qua tay admin",
                "example": "campaign[1].status = EXECUTED (= PASS)"
            },
            {
                "what": "Biên bản chữ ký số",
                "where": "VotingCertificate contract — certificates[campaignId]",
                "why": "Chứng minh kết quả chính thức không thể làm giả sau thực tế",
                "example": "cert.certificateHash = 0xabc123... (hash toàn bộ biên bản)"
            },
        ]
    },
    "OFF_CHAIN": {
        "description": "Dữ liệu ngoài Blockchain — cần bảo vệ riêng",
        "items": [
            {
                "what": "Tên thật cổ đông",
                "where": "contract_addresses.json / Database nội bộ",
                "why": "Thông tin nhạy cảm không nên để công khai on-chain",
                "example": "'Chủ tịch HĐQT' → 0x7CdDA190... (ánh xạ tên ↔ địa chỉ ví)",
                "risk": "Có thể bị sửa → cần bảo vệ file / dùng database bảo mật"
            },
            {
                "what": "CCCD / Giấy tờ định danh gốc",
                "where": "Lưu nội bộ công ty / notary",
                "why": "Quá lớn và nhạy cảm để lưu on-chain",
                "example": "Scan CCCD → hash → lưu hash on-chain (identityHash)",
                "risk": "File gốc có thể bị thất lạc → cần backup cẩn thận"
            },
            {
                "what": "Private Key của cổ đông",
                "where": "Ví cứng (Ledger) / MetaMask / file .env",
                "why": "Private key = quyền kiểm soát ví, KHÔNG được lưu on-chain",
                "example": "GANACHE_PRIVATE_KEYS=0xabc... trong file .env",
                "risk": "⚠️ NGUY HIỂM NHẤT — lộ private key = mất toàn bộ tài sản"
            },
            {
                "what": "Dashboard Streamlit (app.py)",
                "where": "Server / máy tính chạy Streamlit",
                "why": "Giao diện người dùng, không cần lưu on-chain",
                "example": "streamlit run dashboard/app.py",
                "risk": "Server down → không xem được dashboard, NHƯNG dữ liệu on-chain vẫn còn"
            },
            {
                "what": "File biên bản PDF / JSON (do certificate_generator.py tạo)",
                "where": "dashboard/certificates/ folder",
                "why": "Format dễ đọc, in được — nội dung đã anchor bởi on-chain hash",
                "example": "certificate_campaign1_20260507.pdf",
                "risk": "File có thể bị sửa, nhưng certificateHash sẽ không khớp → dễ phát hiện"
            },
            {
                "what": "contract_addresses.json",
                "where": "dashboard/contract_addresses.json",
                "why": "Config địa chỉ contract để Dashboard kết nối",
                "example": '{"hstToken": "0xC3b0...", "governance": "0x2127..."}',
                "risk": "Nếu bị sửa địa chỉ sai → Dashboard đọc nhầm contract khác"
            },
            {
                "what": "ABI của contract",
                "where": "artifacts/contracts/*.json (do Hardhat compile)",
                "why": "ABI = 'giao thức' để Python đọc contract, không cần on-chain",
                "example": "artifacts/contracts/GovernanceContract.sol/GovernanceContract.json",
                "risk": "ABI sai → không gọi được hàm contract → lỗi runtime"
            },
        ]
    }
}


# ─── Hàm in giải thích rõ ràng ────────────────────────────────
def print_onchain_offchain_map():
    """In bản đồ on-chain / off-chain ra console — dùng để báo cáo / trình bày."""

    print("\n" + "═" * 70)
    print("  ON-CHAIN vs OFF-CHAIN — Bản đồ dữ liệu hệ thống DAO Voting")
    print("═" * 70)

    for zone, info in SYSTEM_DATA_MAP.items():
        icon = "⛓️ " if zone == "ON_CHAIN" else "💻"
        print(f"\n{icon} {zone}: {info['description']}")
        print("─" * 70)

        for item in info["items"]:
            print(f"\n  📌 {item['what']}")
            print(f"     Lưu tại  : {item['where']}")
            print(f"     Lý do    : {item['why']}")
            print(f"     Ví dụ    : {item['example']}")
            if "risk" in item:
                print(f"     ⚠️  Rủi ro : {item['risk']}")

    print("\n" + "═" * 70)
    print("  TÓM TẮT NGUYÊN TẮC:")
    print("  - Dữ liệu CẦN BẤT BIẾN + CÔNG KHAI → ON-CHAIN")
    print("  - Dữ liệu NHẠY CẢM hoặc FORMAT ĐẸP → OFF-CHAIN")
    print("  - Kết nối hai bên bằng HASH (cryptographic anchor)")
    print("═" * 70)


# ─── Hàm kiểm tra trạng thái thực tế ─────────────────────────
def check_system_health(rpc_url: str = "http://127.0.0.1:7545") -> dict:
    """
    Kiểm tra trạng thái on-chain của hệ thống.

    Returns:
        {
            "connected":     bool,
            "block_number":  int,
            "chain_id":      int,
            "contracts": {
                "hstToken":   {"address": str, "totalSupply": float},
                "registry":   {"address": str, "activeShareholders": int},
                "governance": {"address": str, "campaignCount": int},
            },
            "onchain_data_summary": str
        }
    """
    try:
        w3 = connect_web3(rpc_url)
        addrs = load_addresses()
        contracts = get_all_contracts(w3)

        total_supply = contracts["hst"].functions.totalSupply().call() / 10**18
        active_sh    = contracts["registry"].functions.activeShareholders().call()
        camp_count   = contracts["gov"].functions.campaignCounter().call()

        result = {
            "connected":    True,
            "block_number": w3.eth.block_number,
            "chain_id":     w3.eth.chain_id,
            "contracts": {
                "hstToken": {
                    "address":     addrs["hstToken"],
                    "totalSupply": total_supply,
                },
                "registry": {
                    "address":            addrs["registry"],
                    "activeShareholders": active_sh,
                },
                "governance": {
                    "address":       addrs["governance"],
                    "campaignCount": camp_count,
                },
            },
            "onchain_data_summary": (
                f"Block #{w3.eth.block_number} | "
                f"{total_supply:,.0f} HST | "
                f"{active_sh} cổ đông | "
                f"{camp_count} chiến dịch"
            )
        }
        return result

    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "onchain_data_summary": "Không kết nối được blockchain"
        }


# ─── Quick run ────────────────────────────────────────────────
if __name__ == "__main__":
    print_onchain_offchain_map()
    print("\n🔍 Kiểm tra trạng thái hệ thống...")
    health = check_system_health()
    if health["connected"]:
        print(f"  ✅ Kết nối OK: {health['onchain_data_summary']}")
    else:
        print(f"  ❌ Lỗi: {health.get('error', 'Unknown')}")
