# 📋 HƯỚNG DẪN TÍCH HỢP — CẢI TIẾN THEO NHẬN XÉT THẦY

## Tổng quan 4 nhận xét → 4 thay đổi

| # | Nhận xét thầy | File đã thêm/sửa |
|---|---|---|
| 1 | Làm rõ vai trò token | `HSTToken.sol` → thêm `getTokenInfo()`, `getDelegationStatus()`, comments đầy đủ |
| 2 | Quy trình nghiệp vụ + ánh xạ thực tế | `GovernanceContract.sol` → comments + events mở rộng + `previewResult()` |
| 3 | Biên bản chữ ký số sau finalize | `VotingCertificate.sol` (MỚI) + `certificate_generator.py` (MỚI) |
| 4 | On-chain / Off-chain rõ hơn | `on_off_chain_explainer.py` (MỚI) + `web3_helpers.py` cập nhật |

---

## Bước 1: Copy file vào project

```
Từ dao_improved/ copy vào project gốc:

contracts/
  ├── HSTToken.sol              ← THAY THẾ file cũ
  ├── GovernanceContract.sol    ← THAY THẾ file cũ
  └── VotingCertificate.sol     ← FILE MỚI

scripts/
  ├── setup_demo.js             ← THAY THẾ file cũ
  └── setup_campaign.js         ← THAY THẾ file cũ

utils/
  ├── web3_helpers.py           ← THAY THẾ file cũ
  ├── certificate_generator.py  ← FILE MỚI
  └── on_off_chain_explainer.py ← FILE MỚI

dashboard/pages/
  └── certificate_page.py       ← FILE MỚI (thêm vào app.py)
```

---

## Bước 2: Compile và deploy lại

```bash
# Compile contracts mới
npx hardhat compile

# Deploy (tự động deploy VotingCertificate và link vào Governance)
npx hardhat run scripts/setup_demo.js --network ganache

# Tạo campaigns + finalize + tạo biên bản
npx hardhat run scripts/setup_campaign.js --network ganache
```

---

## Bước 3: Thêm vào app.py

Trong file `dashboard/app.py`, tìm phần định nghĩa tabs và thêm:

```python
# Thêm vào phần import ở đầu file
from pages.certificate_page import render_certificate_page, render_onchain_offchain_tab

# Thêm 2 tab mới trong phần tabs
tab_home, tab_vote, tab_shareholders, tab_analysis, tab_cert, tab_info, tab_guide = st.tabs([
    "🏠 Tổng quan", "🗳️ Bỏ phiếu", "👥 Cổ đông",
    "📊 Phân tích", "📄 Biên bản",  "⛓️ On/Off-chain", "📖 Hướng dẫn"
])

# Tab Biên bản (Nhận xét #3)
with tab_cert:
    render_certificate_page(contracts, w3)

# Tab On/Off-chain (Nhận xét #4)
with tab_info:
    render_onchain_offchain_tab()
```

---

## Bước 4: Cập nhật contract_addresses.json

Sau khi chạy `setup_demo.js` mới, file `dashboard/contract_addresses.json`
sẽ tự động có thêm trường:

```json
{
  "votingCertificate": "0x..."
}
```

---

## Điểm nổi bật theo từng nhận xét

### Nhận xét #1 — Vai trò token

`HSTToken.sol` giờ có:
- `getTokenInfo()` — trả về name, symbol, supply, owner, giải thích 3 vai trò
- `getDelegationStatus()` — kiểm tra cổ đông đã activate voting power chưa
- Comments chi tiết giải thích tại sao dùng ERC20Votes thay ERC20 thường

### Nhận xét #2 — Quy trình nghiệp vụ + ánh xạ thực tế

`GovernanceContract.sol` giờ có:
- Comments đầu file: bảng ánh xạ "Truyền thống → Blockchain" đầy đủ
- `CampaignCreated` event thêm `snapshotBlock` và `votingDeadline`
- `VoteCast` event thêm `mechanism` (biết trọng số tính theo cơ chế nào)
- `CampaignFinalized` event thêm `participationBps`, `forBps`, `certificateHash`
- `previewResult()` — Dashboard xem kết quả tạm thời realtime
- `setup_campaign.js` có comments ánh xạ từng bước

### Nhận xét #3 — Biên bản chữ ký số

`VotingCertificate.sol` (contract mới):
- `issueCertificate()` — tạo biên bản on-chain sau finalize
- `verifyCertificate()` — verify hash toàn vẹn
- `getCertificate()` — đọc biên bản đầy đủ
- Tự động tạo trong `finalizeCampaign()` của GovernanceContract

`certificate_generator.py`:
- Đọc biên bản từ on-chain
- Export JSON + text có thể in
- Verify hash on-chain ↔ off-chain

`dashboard/pages/certificate_page.py`:
- Tab "📄 Biên bản" trong Dashboard
- Hiển thị kết quả, verify hash, download JSON/TXT

### Nhận xét #4 — On-chain / Off-chain rõ hơn

`on_off_chain_explainer.py`:
- Bản đồ đầy đủ: từng loại data thuộc on-chain hay off-chain
- Lý do tại sao mỗi loại được đặt ở đó
- Hàm `check_system_health()` — kiểm tra trạng thái thực tế

`web3_helpers.py` cập nhật:
- Comments mỗi hàm ghi rõ "ON-CHAIN" hay "OFF-CHAIN"
- Hỗ trợ VotingCertificate contract
- `build_tx()` giải thích rõ: ký off-chain, gửi on-chain

`dashboard/pages/certificate_page.py`:
- Tab "⛓️ On/Off-chain" với bảng ánh xạ trực quan
- So sánh quy trình ĐHCĐ truyền thống vs blockchain
