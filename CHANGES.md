# CHANGES.md — Cải tiến theo nhận xét của thầy

## Tổng quan 4 nhận xét và file đã thay đổi

---

## #1 — Làm rõ chức năng và vai trò của Token

**File thay đổi:** `contracts/HSTToken.sol`

### Đã bổ sung:
- **Comment đầy đủ 3 vai trò** ngay đầu contract:
  - Chứng nhận sở hữu cổ phần (1 HST = 1 đơn vị cổ phần)
  - Quyền biểu quyết (cần delegate() để kích hoạt)
  - Chứng minh tư cách (Tier 0-3 dựa trên % sở hữu)
- **Giải thích tại sao dùng ERC20Votes** thay vì ERC20 thường:
  - Lưu lịch sử checkpoint → chống thao túng bằng cách mua/bán token
- **Hàm `getTokenInfo()`** — trả về toàn bộ thông tin token trong 1 call
- **Hàm `getDelegationStatus()`** — kiểm tra nhanh đã delegate chưa

**File thay đổi:** `utils/web3_helpers.py`
- Hàm `get_token_info()` — đọc thông tin token từ on-chain, kèm mô tả vai trò
- Hàm `get_delegation_status()` — kiểm tra trạng thái delegation + hint nhắc nhở

**File thay đổi:** `dashboard/app_additions.py`
- Hàm `render_token_info_tab()` — tab Dashboard hiển thị đầy đủ 3 vai trò token
- Bảng so sánh 3 cơ chế tính trọng số (Linear/Quadratic/Equal) với số liệu cụ thể

---

## #2 — Quy trình nghiệp vụ biểu quyết + ánh xạ thực tế

**File thay đổi:** `contracts/GovernanceContract.sol`

### Đã bổ sung:
- **Bảng ánh xạ** ở đầu contract:
  ```
  TRUYỀN THỐNG                    │ BLOCKCHAIN
  Ban tổ chức chuẩn bị tờ phiếu  │ createCampaign()
  Chốt danh sách cổ đông          │ snapshotBlock = block.number
  Phát phiếu tại hội trường       │ castVote()
  Thu phiếu, kiểm tra chữ ký      │ registry.canVote()
  Đếm phiếu thủ công              │ _recordVote()
  Công bố kết quả                 │ finalizeCampaign()
  Thư ký ký biên bản              │ VotingCertificate.issueCertificate()
  ```
- **Comments từng hàm** giải thích ánh xạ nghiệp vụ
- **Event `CampaignCreated`** thêm `snapshotBlock` và `votingDeadline`
- **Event `VoteCast`** thêm `mechanism` (để biết trọng số tính theo cơ chế nào)
- **Event `CampaignFinalized`** thêm `participationBps`, `forBps`, `certificateHash`
- **Hàm `previewResult()`** — xem kết quả dự kiến trước khi finalize (realtime)

**File thay đổi:** `contracts/ShareholderRegistry.sol`
- Bảng ánh xạ nghiệp vụ trong NatSpec
- Comment giải thích logic `canVote()`: lockUntil=0 → không bị khóa

**File thay đổi:** `dashboard/app_additions.py`
- Hàm `render_business_process_tab()` — tab Dashboard minh họa luồng nghiệp vụ
- So sánh song song truyền thống vs blockchain
- Kịch bản ID-101 demo kết quả thực tế với số liệu từ on-chain

---

## #3 — Biên bản chữ ký số sau khi finalize

**File mới:** `contracts/VotingCertificate.sol`

### Tính năng:
- **`issueCertificate()`** — tạo biên bản on-chain sau finalize
  - Tính `certificateHash = keccak256(tất cả dữ liệu quan trọng)`
  - Lưu vĩnh viễn: forVotes, againstVotes, kết quả, người ký, timestamp
  - Phát event `CertificateIssued` — chữ ký số on-chain
- **`verifyCertificate()`** — tính lại hash để xác minh toàn vẹn
- **`getCertificate()`** — đọc toàn bộ biên bản
- **`hasCertificate()`** — kiểm tra nhanh

**File thay đổi:** `contracts/GovernanceContract.sol`
- Tích hợp `VotingCertificate` vào `finalizeCampaign()`
- Tự động gọi `issueCertificate()` sau khi kết quả được xác định
- Truyền `certificateHash` trong event `CampaignFinalized`

**File thay đổi:** `scripts/setup_demo.js`
- Deploy `VotingCertificate` contract (bước 5)
- Cấp `CERTIFIER_ROLE` cho `GovernanceContract`
- Gọi `gov.setCertificateContract()` để liên kết
- Lưu `votingCertificate` address vào `contract_addresses.json`

**File mới:** `utils/certificate_generator.py`
- `fetch_certificate_onchain()` — đọc biên bản từ on-chain
- `verify_certificate_integrity()` — verify hash
- `generate_certificate_text()` — tạo biên bản text đẹp
- `export_certificate()` — xuất file JSON + TXT
- `fetch_and_export_certificate()` — pipeline đầy đủ

**File thay đổi:** `dashboard/app_additions.py`
- Hàm `render_certificate_tab()` — tab Dashboard hiển thị biên bản
- Nút Verify biên bản on-chain
- Nút Tải biên bản (.txt)

---

## #4 — On-chain / Off-chain giải thích rõ hơn

**File thay đổi:** `contracts/HSTToken.sol`
- Section "ON-CHAIN vs OFF-CHAIN" trong NatSpec constructor

**File thay đổi:** `contracts/GovernanceContract.sol`
- Section "ON-CHAIN / OFF-CHAIN" liệt kê rõ thứ gì lưu ở đâu

**File thay đổi:** `contracts/ShareholderRegistry.sol`
- Phân vùng rõ ON-CHAIN (struct data, identityHash) và OFF-CHAIN (tên thật, CCCD gốc)
- Giải thích cơ chế anchoring: hash(CCCD) lưu on-chain → verify được

**File mới:** `utils/on_off_chain_explainer.py`
- `SYSTEM_DATA_MAP` — bản đồ đầy đủ ON/OFF-CHAIN của toàn hệ thống
- `print_onchain_offchain_map()` — in ra console để báo cáo
- `check_system_health()` — kiểm tra trạng thái thực tế

**File thay đổi:** `utils/web3_helpers.py`
- Mỗi hàm có comment rõ "ON-CHAIN" hoặc "OFF-CHAIN"
- Giải thích luồng: đọc (←) vs ghi (→) lên blockchain

**File thay đổi:** `dashboard/app_additions.py`
- Hàm `render_onchain_offchain_tab()` — tab Dashboard 3 phần:
  - ON-CHAIN: danh sách dữ liệu + live data realtime
  - OFF-CHAIN: danh sách + rủi ro + cách anchor
  - Luồng dữ liệu: ASCII diagram End-to-End

---

## Bảo mật — Xác thực ví bằng chữ ký số

**File thay đổi:** `utils/web3_helpers.py`
- `generate_login_challenge()` — tạo thông điệp challenge
- `sign_challenge()` — ký bằng private key (local, không gửi lên server)
- `recover_signer()` — khôi phục địa chỉ ví từ chữ ký
- `verify_wallet_login()` — pipeline xác thực đầy đủ

**File thay đổi:** `dashboard/app_additions.py`
- `render_secure_login()` — widget đăng nhập an toàn
  - Thay vì nhập private key trực tiếp → ký challenge
  - Verify chữ ký OFF-CHAIN + canVote() ON-CHAIN
  - Session state lưu trong RAM, không persist

---

## Cấu trúc file sau cải tiến

```
dao_improved/
├── contracts/
│   ├── HSTToken.sol              ✏️  Cập nhật (vai trò token rõ hơn)
│   ├── ShareholderRegistry.sol   ✏️  Cập nhật (on/off-chain comments)
│   ├── GovernanceContract.sol    ✏️  Cập nhật (nghiệp vụ + tích hợp cert)
│   ├── HSTTimelockController.sol ━   Không thay đổi
│   └── VotingCertificate.sol     🆕  MỚI (biên bản chữ ký số)
│
├── scripts/
│   ├── setup_demo.js             ✏️  Cập nhật (deploy VotingCertificate)
│   ├── setup_campaign.js         ━   Không thay đổi
│   └── add_campaigns.js          ━   Không thay đổi
│
├── dashboard/
│   ├── app.py                    ✏️  Tích hợp app_additions.py
│   └── app_additions.py          🆕  MỚI (4 tabs mới)
│
└── utils/
    ├── web3_helpers.py           ✏️  Cập nhật (cert + sign auth)
    ├── certificate_generator.py  🆕  MỚI (xuất biên bản)
    └── on_off_chain_explainer.py 🆕  MỚI (giải thích on/off-chain)
```

---

## Hướng dẫn deploy lại

```bash
# 1. Compile contracts mới
npx hardhat compile

# 2. Deploy lại toàn bộ (bao gồm VotingCertificate mới)
npx hardhat run scripts/setup_demo.js --network ganache

# 3. Tạo chiến dịch demo
npx hardhat run scripts/setup_campaign.js --network ganache

# 4. Chạy Dashboard
$env:PYTHONUTF8=1
streamlit run dashboard/app.py --server.fileWatcherType none
```
