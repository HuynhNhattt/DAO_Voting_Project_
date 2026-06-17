"""
utils/certificate_generator.py
═══════════════════════════════════════════════════════════════
NHẬN XÉT THẦY #3: Biên bản chữ ký số sau khi finalize
NHẬN XÉT THẦY #4: Giải thích On-chain / Off-chain rõ hơn
═══════════════════════════════════════════════════════════════

Module này xử lý phần OFF-CHAIN của biên bản biểu quyết:
  - Đọc Certificate từ VotingCertificate contract (ON-CHAIN)
  - Tạo file JSON / text biên bản dễ đọc (OFF-CHAIN)
  - Verify tính toàn vẹn bằng cách so sánh hash (ON-CHAIN ↔ OFF-CHAIN)

── ON-CHAIN vs OFF-CHAIN (Nhận xét thầy #4) ──────────────────

ON-CHAIN (Blockchain — Ganache/Polygon):
  ✅ VotingCertificate contract lưu:
     - certificateHash   : hash toàn bộ dữ liệu biên bản
     - finalizedBy       : địa chỉ ví người ký
     - finalizedAt       : Unix timestamp lúc ký
     - forVotes / againstVotes / abstainVotes
     - passed (PASS/DEFEAT)
  ✅ GovernanceContract lưu:
     - Từng lá phiếu (VoteCast events)
     - Kết quả campaign (CampaignFinalized event)
  → Ai cũng có thể đọc, không ai có thể sửa

OFF-CHAIN (Máy tính / Server):
  📄 File biên bản JSON (module này tạo ra)
  📄 File biên bản text (in được, dễ đọc)
  🌐 Dashboard Streamlit (app.py)
  🔧 web3_helpers.py (kết nối blockchain)
  📁 contract_addresses.json (config địa chỉ)
  → Có thể bị sửa NHƯNG dễ phát hiện nếu hash không khớp

── CÁCH XÁC MINH TÍNH XÁC THỰC ──────────────────────────────
  1. Lấy certificateHash từ VotingCertificate contract
  2. Tính lại hash từ dữ liệu biên bản local
  3. So sánh → Khớp = biên bản hợp lệ, chưa bị chỉnh sửa
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing  import Optional

from web3 import Web3

# Import helpers đã có sẵn
from web3_helpers import connect_web3, get_contract, load_addresses


# ─── Paths ────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
CERT_DIR     = ROOT / "dashboard" / "certificates"
CERT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Label helpers ────────────────────────────────────────────
PROPOSAL_TYPE_LABEL = {0: "ROUTINE (Thường lệ)", 1: "MAJOR (Quan trọng)", 2: "M&A (Sáp nhập)"}
MECHANISM_LABEL     = {0: "LINEAR (Tuyến tính)", 1: "QUADRATIC (Căn bậc 2)", 2: "EQUAL (Đồng đều)"}
TIER_LABEL          = {0: "Nhỏ lẻ", 1: "Tổ chức", 2: "Chiến lược", 3: "Sáng lập"}


# ─── Đọc Certificate từ ON-CHAIN ──────────────────────────────
def fetch_certificate_onchain(w3: Web3, cert_contract, campaign_id: int) -> Optional[dict]:
    """
    Đọc biên bản từ VotingCertificate contract (ON-CHAIN).

    Đây là dữ liệu BẤT BIẾN — không ai có thể sửa sau khi
    issueCertificate() đã được gọi trên blockchain.

    Returns:
        dict chứa toàn bộ thông tin biên bản, hoặc None nếu chưa có.
    """
    try:
        has_cert = cert_contract.functions.hasCertificate(campaign_id).call()
        if not has_cert:
            return None

        raw = cert_contract.functions.getCertificate(campaign_id).call()

        # Raw tuple từ contract: (campaignId, title, passed, forVotes,
        # againstVotes, abstainVotes, totalParticipants, quorumBps,
        # participationBps, passThreshold, forBps, proposalType,
        # mechanism, finalizedBy, finalizedAt, snapshotBlock,
        # certificateHash, exists)
        return {
            "campaignId":        raw[0],
            "campaignTitle":     raw[1],
            "passed":            raw[2],
            "forVotes":          raw[3] / 10**18,
            "againstVotes":      raw[4] / 10**18,
            "abstainVotes":      raw[5] / 10**18,
            "totalParticipants": raw[6],
            "quorumBps":         raw[7] / 100,       # → %
            "participationBps":  raw[8] / 100,        # → %
            "passThreshold":     raw[9] / 100,        # → %
            "forBps":            raw[10] / 100,       # → %
            "proposalType":      raw[11],
            "mechanism":         raw[12],
            "finalizedBy":       raw[13],
            "finalizedAt":       raw[14],
            "snapshotBlock":     raw[15],
            "certificateHash":   "0x" + raw[16].hex(),
        }
    except Exception as e:
        print(f"⚠️  Lỗi đọc certificate: {e}")
        return None


# ─── Verify tính toàn vẹn (ON-CHAIN ↔ OFF-CHAIN) ─────────────
def verify_certificate_integrity(w3: Web3, cert_contract, campaign_id: int) -> dict:
    """
    Xác minh biên bản chưa bị chỉnh sửa.

    Cách hoạt động:
      - Gọi verifyCertificate() trên contract
      - Contract tính lại hash từ dữ liệu đang lưu
      - So sánh với certificateHash đã lưu ban đầu
      - Nếu khớp → biên bản toàn vẹn

    Returns:
        {
            "isValid":      bool,
            "storedHash":   str,
            "computedHash": str,
            "message":      str
        }
    """
    try:
        result = cert_contract.functions.verifyCertificate(campaign_id).call()
        is_valid     = result[0]
        stored_hash  = "0x" + result[1].hex()
        computed_hash = "0x" + result[2].hex()

        return {
            "isValid":      is_valid,
            "storedHash":   stored_hash,
            "computedHash": computed_hash,
            "message": (
                "✅ Biên bản hợp lệ — dữ liệu chưa bị chỉnh sửa"
                if is_valid else
                "❌ CẢNH BÁO: Hash không khớp — biên bản có thể đã bị sửa!"
            )
        }
    except Exception as e:
        return {
            "isValid": False,
            "storedHash": "",
            "computedHash": "",
            "message": f"Lỗi xác minh: {e}"
        }


# ─── Tạo biên bản text (OFF-CHAIN) ────────────────────────────
def generate_certificate_text(cert_data: dict, verification: dict) -> str:
    """
    Tạo nội dung biên bản dạng text dễ đọc (OFF-CHAIN document).

    Đây là phần OFF-CHAIN: file này có thể bị sửa, NHƯNG
    certificateHash ở cuối có thể dùng để verify với on-chain.
    """
    finalized_dt = datetime.fromtimestamp(cert_data["finalizedAt"])
    result_str   = "✅ THÔNG QUA (PASS)" if cert_data["passed"] else "❌ KHÔNG ĐẠT (DEFEAT)"
    type_str     = PROPOSAL_TYPE_LABEL.get(cert_data["proposalType"], "?")
    mech_str     = MECHANISM_LABEL.get(cert_data["mechanism"], "?")

    total_decisive = cert_data["forVotes"] + cert_data["againstVotes"]
    total_votes    = total_decisive + cert_data["abstainVotes"]

    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║          BIÊN BẢN KẾT QUẢ BIỂU QUYẾT CỔ ĐÔNG               ║",
        "║         (Digital Certificate — Lưu trên Blockchain)          ║",
        "╚══════════════════════════════════════════════════════════════╝",
        "",
        f"  Chiến dịch  : #{cert_data['campaignId']} — {cert_data['campaignTitle']}",
        f"  Loại đề xuất: {type_str}",
        f"  Cơ chế phiếu: {mech_str}",
        f"  Block chụp  : #{cert_data['snapshotBlock']} (snapshot cổ đông)",
        "",
        "── KẾT QUẢ BIỂU QUYẾT ────────────────────────────────────────",
        f"  Kết quả     : {result_str}",
        f"  Tán thành   : {cert_data['forVotes']:>15,.2f} HST  ({cert_data['forBps']:.1f}%)",
        f"  Phản đối    : {cert_data['againstVotes']:>15,.2f} HST",
        f"  Bỏ phiếu trắng: {cert_data['abstainVotes']:>12,.2f} HST",
        f"  Tổng tham gia: {total_votes:>14,.2f} HST",
        f"  Số cổ đông   : {cert_data['totalParticipants']} người",
        "",
        "── NGƯỠNG XÉT KẾT QUẢ ─────────────────────────────────────────",
        f"  Quorum yêu cầu  : {cert_data['quorumBps']:.0f}%  |  Thực tế: {cert_data['participationBps']:.1f}%  "
        + ("✅" if cert_data['participationBps'] >= cert_data['quorumBps'] else "❌"),
        f"  Ngưỡng thông qua: {cert_data['passThreshold']:.0f}%  |  Thực tế: {cert_data['forBps']:.1f}%  "
        + ("✅" if cert_data['passed'] else "❌"),
        "",
        "── THÔNG TIN CHỮ KÝ SỐ (ON-CHAIN) ──────────────────────────────",
        f"  Người ký (ví) : {cert_data['finalizedBy']}",
        f"  Thời điểm ký  : {finalized_dt.strftime('%H:%M:%S %d/%m/%Y')}",
        f"  Certificate Hash (ON-CHAIN):",
        f"    {cert_data['certificateHash']}",
        "",
        "── XÁC MINH TÍNH TOÀN VẸN ───────────────────────────────────────",
        f"  {verification['message']}",
        f"  Hash đang lưu : {verification.get('storedHash', 'N/A')}",
        f"  Hash tính lại : {verification.get('computedHash', 'N/A')}",
        "",
        "── HƯỚNG DẪN XÁC MINH ───────────────────────────────────────────",
        "  Bất kỳ ai cũng có thể xác minh biên bản này:",
        "  1. Mở Ganache → xem contract VotingCertificate",
        f"  2. Gọi getCertificate({cert_data['campaignId']}) → lấy certificateHash",
        "  3. So sánh với hash ở trên → nếu khớp: biên bản hợp lệ",
        "  (Sau khi deploy lên Polygon: xem trên polygonscan.com/amoy)",
        "",
        "═" * 66,
        "  Tài liệu này được tạo tự động từ dữ liệu on-chain.",
        "  Nội dung biên bản được bảo đảm bởi công nghệ Blockchain.",
        "═" * 66,
    ]
    return "\n".join(lines)


# ─── Export biên bản ra file ───────────────────────────────────
def export_certificate(
    cert_data: dict,
    verification: dict,
    fmt: str = "both"          # "json", "text", hoặc "both"
) -> dict[str, Path]:
    """
    Lưu biên bản ra file (OFF-CHAIN document).

    Returns:
        {"json": Path, "text": Path}  — đường dẫn các file đã tạo
    """
    campaign_id = cert_data["campaignId"]
    timestamp   = datetime.fromtimestamp(cert_data["finalizedAt"]).strftime("%Y%m%d_%H%M%S")
    base_name   = f"certificate_campaign{campaign_id}_{timestamp}"
    created     = {}

    if fmt in ("json", "both"):
        json_path = CERT_DIR / f"{base_name}.json"
        export_data = {
            **cert_data,
            "verification": verification,
            "generatedAt":  datetime.now().isoformat(),
            "note": (
                "File này là bản OFF-CHAIN để đọc dễ dàng. "
                "Dữ liệu gốc được lưu trên blockchain tại "
                "VotingCertificate contract. "
                "Dùng certificateHash để verify tính xác thực."
            )
        }
        json_path.write_text(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        created["json"] = json_path

    if fmt in ("text", "both"):
        text_path = CERT_DIR / f"{base_name}.txt"
        text_path.write_text(
            generate_certificate_text(cert_data, verification),
            encoding="utf-8"
        )
        created["text"] = text_path

    return created


# ─── Hàm tiện ích tổng hợp ────────────────────────────────────
def fetch_and_export_certificate(
    campaign_id: int,
    rpc_url: str = "http://127.0.0.1:7545",
    fmt: str = "both"
) -> Optional[dict]:
    """
    Pipeline đầy đủ: Đọc từ blockchain → Verify → Export file.

    Args:
        campaign_id: ID chiến dịch cần lấy biên bản
        rpc_url:     URL kết nối blockchain (Ganache hoặc Amoy)
        fmt:         Định dạng xuất ("json", "text", "both")

    Returns:
        {
            "cert_data":    dict,    # Dữ liệu biên bản từ on-chain
            "verification": dict,   # Kết quả verify
            "files":        dict,   # Đường dẫn file đã tạo
            "certificate_text": str # Nội dung biên bản text
        }
        hoặc None nếu chưa có biên bản cho campaign này.
    """
    try:
        w3       = connect_web3(rpc_url)
        addrs    = load_addresses()

        # Load VotingCertificate contract
        cert_contract = get_contract(w3, "VotingCertificate", addrs["votingCertificate"])

        # Đọc dữ liệu từ ON-CHAIN
        cert_data = fetch_certificate_onchain(w3, cert_contract, campaign_id)
        if cert_data is None:
            print(f"⚠️  Campaign #{campaign_id} chưa có biên bản on-chain.")
            print("    Hãy gọi finalizeCampaign() trước.")
            return None

        # Verify tính toàn vẹn (ON-CHAIN hash check)
        verification = verify_certificate_integrity(w3, cert_contract, campaign_id)

        # Export file (OFF-CHAIN)
        files = export_certificate(cert_data, verification, fmt=fmt)

        # In ra console
        cert_text = generate_certificate_text(cert_data, verification)
        print(cert_text)
        print(f"\n  ✅ Đã lưu biên bản:")
        for ftype, fpath in files.items():
            print(f"     [{ftype.upper()}] {fpath}")

        return {
            "cert_data":        cert_data,
            "verification":     verification,
            "files":            files,
            "certificate_text": cert_text,
        }

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return None


# ─── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    campaign_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"\n🔍 Đang lấy biên bản cho Campaign #{campaign_id}...\n")
    result = fetch_and_export_certificate(campaign_id)
    if result is None:
        print("Không tìm thấy biên bản. Campaign chưa finalize?")
