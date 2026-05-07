# 🏛️ DAO Voting System — Hệ thống Biểu quyết Cổ đông Blockchain

> **Đồ án môn học: Công nghệ Blockchain ứng dụng**
> Xây dựng nền tảng quản trị phi tập trung (DAO) cho doanh nghiệp cổ phần trên Ethereum

---

## 📋 Thông tin Đồ án

| Mục | Nội dung |
|---|---|
| **Tên đồ án** | DAO Voting System — Hệ thống Biểu quyết Cổ đông Blockchain |
| **Loại** | Đồ án sinh viên — Blockchain ứng dụng thực tế |
| **Nền tảng** | Ethereum (EVM) · Ganache local · Hardhat |
| **Ngôn ngữ** | Solidity 0.8.20 · JavaScript (Node ≥18) · Python ≥ 3.10 |
| **Framework** | Hardhat · OpenZeppelin v4 · Web3.py · Streamlit |
| **Mạng demo** | Ganache UI (port 7545, Chain ID 1337) |

### Mục tiêu đồ án

Xây dựng một hệ thống quản trị DAO hoàn chỉnh cho doanh nghiệp cổ phần, bao gồm:

- **Token hoá quyền sở hữu** — ERC-20 với snapshot voting (ERC20Votes)
- **Đăng ký cổ đông** — quản lý danh tính, tier và điều kiện biểu quyết
- **Ba cơ chế biểu quyết** — Linear (tỷ lệ token), Quadratic (√token), Equal (1 người 1 phiếu)
- **Bỏ phiếu kín** — Commit-Reveal scheme chống front-running
- **Timelock** — trì hoãn thực thi nghị quyết theo mức độ quan trọng
- **Dashboard trực quan** — giao diện Streamlit kết nối live blockchain

---

## 📊 Đánh giá mức độ hoàn thiện

### ✅ Đã hoàn chỉnh (Production-ready)

| Hạng mục | Chi tiết | Mức độ |
|---|---|---|
| **HSTToken.sol** | ERC20Votes + snapshot + mint/burn by owner | ✅ Hoàn chỉnh |
| **ShareholderRegistry.sol** | RBAC, tier tự động, canVote(), lock mechanism | ✅ Hoàn chỉnh |
| **GovernanceContract.sol** | 3 cơ chế vote, Commit-Reveal, finalize, quorum | ✅ Hoàn chỉnh |
| **HSTTimelockController.sol** | 3 mức delay theo ProposalType | ✅ Hoàn chỉnh |
| **setup_demo.js** | Deploy toàn bộ + phân bổ token + lưu địa chỉ | ✅ Hoàn chỉnh |
| **setup_campaign.js** | Tạo 4 kịch bản demo + bỏ phiếu sẵn | ✅ Hoàn chỉnh |
| **add_campaigns.js** | Thêm campaign mới để test tự vote | ✅ Hoàn chỉnh |
| **HSTToken.test.js** | Unit test token đầy đủ | ✅ Hoàn chỉnh |
| **Governance.test.js** | Integration test 4 kịch bản | ✅ Hoàn chỉnh |
| **web3_helpers.py** | Kết nối Web3, đọc on-chain, helper function | ✅ Hoàn chỉnh |
| **distribute_tokens.py** | Calculator phân bổ + so sánh 3 cơ chế | ✅ Hoàn chỉnh |
| **app.py (Dashboard)** | Login ví, bỏ phiếu, Commit-Reveal UI, phân tích | ✅ Hoàn chỉnh |

### ⚠️ Giới hạn có chủ đích (demo scope)

| Hạng mục | Lý do giới hạn |
|---|---|
| **Không có MetaMask** | Dùng private key trực tiếp — phù hợp Ganache demo, không dùng production |
| **Không có real-time auto-refresh** | Streamlit không hỗ trợ WebSocket native — cần bấm Refresh thủ công |
| **Timelock chưa tích hợp UI** | Timelock contract đã deploy, nhưng execute qua console Hardhat |
| **Không có AUDITOR dashboard** | Vai trò AUDITOR trong contract nhưng chưa có trang riêng trên UI |

---

## 📁 Cấu trúc Dự án

```
dao-voting-system/
│
├── contracts/                        # ═══ Smart Contracts (Solidity) ═══
│   ├── HSTToken.sol                  # ERC-20 + ERC20Votes — token cổ phần
│   ├── ShareholderRegistry.sol       # Quản lý cổ đông + điều kiện vote
│   ├── GovernanceContract.sol        # Logic biểu quyết toàn bộ
│   └── HSTTimelockController.sol     # Trì hoãn thực thi nghị quyết
│
├── scripts/                          # ═══ Deployment & Setup Scripts ═══
│   ├── setup_demo.js                 # Deploy tất cả contract + phân bổ token
│   ├── setup_campaign.js             # Tạo 4 kịch bản demo + bỏ phiếu sẵn
│   └── add_campaigns.js              # Thêm campaign ACTIVE để tự vote
│
├── test/                             # ═══ Test Suite ═══
│   ├── HSTToken.test.js              # Unit tests token (mint, burn, vote, snapshot)
│   └── Governance.test.js            # Integration tests 4 kịch bản (ID-101 → 104)
│
├── utils/                            # ═══ Python Utilities ═══
│   ├── web3_helpers.py               # Kết nối Web3, load contract, đọc on-chain
│   └── distribute_tokens.py          # Tính phân bổ token + so sánh cơ chế
│
├── dashboard/                        # ═══ Streamlit Dashboard ═══
│   ├── app.py                        # Giao diện chính 5 trang
│   └── contract_addresses.json       # Auto-generated sau khi deploy
│
├── hardhat.config.js                 # Cấu hình Hardhat (Ganache, Amoy, gas)
├── package.json                      # NPM dependencies
├── requirements.txt                  # Python dependencies
├── .env                              # Private keys (KHÔNG commit lên git)
└── .gitignore
```

---

## 🔧 Chịu trách nhiệm gì — Từng module

### Smart Contracts (`contracts/`)

#### `HSTToken.sol` — Token Cổ phần
```
Chịu trách nhiệm:
  ✦ Đại diện quyền sở hữu công ty dưới dạng ERC-20
  ✦ Snapshot voting power tại từng block (ERC20Votes)
  ✦ Cho phép delegation (ủy quyền biểu quyết)
  ✦ Mint/burn chỉ bởi owner (ShareholderRegistry)

Giao diện quan trọng:
  → mint(to, amount, reason)       — Registry gọi khi thêm cổ đông
  → burn(from, amount)             — Admin gọi khi cần
  → delegate(delegatee)            — Cổ đông tự kích hoạt voting power
  → getPastVotes(voter, block)     — Governance đọc VP tại snapshot
  → getPastTotalSupply(block)      — Governance tính quorum
```

#### `ShareholderRegistry.sol` — Sổ đăng ký Cổ đông
```
Chịu trách nhiệm:
  ✦ Lưu trữ danh tính cổ đông (địa chỉ + identity hash)
  ✦ Phân loại tier (0–3) dựa trên tỷ lệ nắm giữ
  ✦ Quản lý trạng thái: isActive, lockUntil
  ✦ Cổng kiểm tra điều kiện biểu quyết: canVote()
  ✦ Mint token khi thêm cổ đông mới (gọi HSTToken.mint)

Tier phân loại:
  Tier 3 (Sáng lập):   ≥ 30% tổng cung
  Tier 2 (Chiến lược): ≥ 10% tổng cung
  Tier 1 (Tổ chức):    ≥  1% tổng cung
  Tier 0 (Nhỏ lẻ):     <  1% tổng cung

Giao diện quan trọng:
  → addShareholder(wallet, idHash, tokens, tier)  — REGISTRY_ADMIN
  → deactivateShareholder(wallet, reason)          — REGISTRY_ADMIN
  → canVote(wallet) → bool                         — GovernanceContract
```

#### `GovernanceContract.sol` — Lõi Biểu quyết
```
Chịu trách nhiệm:
  ✦ Tạo và quản lý chiến dịch biểu quyết (Campaign lifecycle)
  ✦ Tính trọng số theo 3 cơ chế:
      Linear    → weight = VP token tại snapshotBlock
      Quadratic → weight = √(VP token)   ← bảo vệ quyền thiểu số
      Equal     → weight = 1 nếu có token, 0 nếu không
  ✦ Commit-Reveal scheme chống front-running
  ✦ Finalize + kiểm tra quorum và ngưỡng thông qua

Lifecycle chiến dịch:
  DRAFT → ACTIVE/COMMIT → (REVEAL) → TALLYING → EXECUTED / DEFEATED

Tham số theo loại đề xuất:
  Routine: pass >50%, quorum 10%, 7 ngày
  Major:   pass >66%, quorum 20%, 14 ngày
  M&A:     pass >75%, quorum 30%, 21 ngày

Giao diện quan trọng:
  → createCampaign(title, desc, type, mech, commitReveal)
  → castVote(campaignId, option)         — ACTIVE campaign
  → commitVote(campaignId, voteHash)     — COMMIT phase
  → revealVote(campaignId, option, salt) — REVEAL phase
  → finalizeCampaign(campaignId)         — sau deadline
```

#### `HSTTimelockController.sol` — Bộ trì hoãn
```
Chịu trách nhiệm:
  ✦ Trì hoãn thực thi nghị quyết đã thông qua
  ✦ Cửa sổ thời gian:
      Routine: 2 ngày
      Major:   7 ngày
      M&A:     14 ngày
  ✦ Chỉ Governance được queue, bất kỳ ai có thể execute sau delay
```

---

### Scripts (`scripts/`)

#### `setup_demo.js` — Deploy toàn hệ thống
```
Luồng thực hiện:
  1. Deploy HSTToken (mint 10M HST → accounts[0])
  2. Burn toàn bộ 10M HST ban đầu của accounts[0]
  3. Deploy ShareholderRegistry + transfer ownership HSTToken → Registry
  4. Deploy GovernanceContract + cấp CAMPAIGN_MANAGER_ROLE
  5. Deploy HSTTimelockController
  6. addShareholder() cho 5 cổ đông → Registry tự mint đúng số token
  7. Self-delegate cho tất cả → kích hoạt voting power
  8. Xuất dashboard/contract_addresses.json

Lý do burn ở bước 2:
  Registry mint token cho cổ đông qua addShareholder().
  Nếu không burn ban đầu, accounts[0] sẽ có 10M + 4.5M = 14.5M HST
  → tổng cung bị sai, tier tính sai.
```

#### `setup_campaign.js` — Tạo 4 kịch bản demo
```
ID-101: Routine  · Linear    — bỏ phiếu sẵn → PASS 70%
ID-102: Major    · Linear    — bỏ phiếu sẵn → PASS 95%
ID-103: Major    · Quadratic — bỏ phiếu sẵn → KHÔNG ĐẠT (Quadratic bảo vệ thiểu số)
ID-104: M&A      · Commit-Reveal — giữ trạng thái COMMIT để demo
```

#### `add_campaigns.js` — Thêm campaign mới để tự vote
```
ID-201: Routine  · Linear  — ACTIVE, không bỏ phiếu sẵn
ID-202: Major    · Linear  — ACTIVE, không bỏ phiếu sẵn
ID-203: Major    · Equal   — ACTIVE, không bỏ phiếu sẵn
ID-204: M&A      · Commit-Reveal — COMMIT, để tự commit
```

---

### Python Utilities (`utils/`)

#### `web3_helpers.py` — Cầu nối blockchain ↔ Python
```
Chịu trách nhiệm:
  ✦ connect_web3(rpc_url)         — kết nối Ganache
  ✦ load_abi(contract_name)       — đọc ABI từ artifacts Hardhat
  ✦ get_all_contracts(w3)         — trả về dict 3 contracts
  ✦ get_shareholder_info(reg, wallet)
  ✦ get_voting_power(hst, wallet)
  ✦ get_campaign_data(gov, id)    — đọc toàn bộ struct Campaign
  ✦ get_all_campaigns(gov)        — iterate từ 1 đến counter
  ✦ get_vote_participation(...)   — tính % quorum
```

#### `distribute_tokens.py` — Tính phân bổ
```
Chịu trách nhiệm:
  ✦ distribute_proportional()  — phân theo tỷ lệ cổ phiếu
  ✦ distribute_equal()         — phân đều 1 người 1 phần
  ✦ compare_voting_mechanisms()— so sánh Linear / Quadratic / Equal
  ✦ Xuất JSON phân tích ra utils/distribution_plan.json
```

---

### Dashboard (`dashboard/app.py`)

```
5 trang — mỗi trang một nhiệm vụ rõ ràng:

🏠 Tổng quan
  ✦ 4 KPI: số cổ đông, tổng HST, chiến dịch mở, nghị quyết pass
  ✦ Danh sách chiến dịch đang mở + thanh vote thực tế
  ✦ Biểu đồ phân bổ token theo cổ đông

🔐 Đăng nhập ví
  ✦ Nhập address + private key → verify khớp nhau
  ✦ Kiểm tra canVote() on-chain
  ✦ Hiển thị tier, HST balance, voting power, lock status

🗳️ Bỏ phiếu
  ✦ Bỏ phiếu thường: castVote() on-chain (signed tx)
  ✦ Commit-Reveal: commitVote() → revealVote() on-chain
  ✦ Finalize campaign sau deadline (evm_increaseTime trên Ganache)
  ✦ Mine block, nhảy thời gian để demo

👥 Cổ đông
  ✦ Bảng cổ đông với filter tier và search
  ✦ Dữ liệu live từ on-chain khi kết nối

📊 Phân tích
  ✦ So sánh trực quan Linear / Quadratic / Equal
  ✦ Biểu đồ tỷ lệ tham gia từng chiến dịch
  ✦ Kịch bản ID-103: kết quả khác nhau giữa 2 cơ chế
```

---

## 🚀 Hướng dẫn Chạy từ đầu

### Yêu cầu hệ thống

```
Node.js  ≥ 18.0.0
npm      ≥ 9.0.0
Python   ≥ 3.10
Ganache UI — tải tại https://trufflesuite.com/ganache/
```

### Bước 1 — Cài dependencies

```bash
# JavaScript
npm install

# Python
pip install -r requirements.txt
```

### Bước 2 — Cấu hình `.env`

Tạo file `.env` ở thư mục gốc:

```env
# Lấy từ Ganache UI > Accounts > biểu tượng chìa khóa
# Cần ít nhất 6 tài khoản, mỗi tài khoản ≥ 1 ETH
GANACHE_PRIVATE_KEYS=0xPK0,0xPK1,0xPK2,0xPK3,0xPK4,0xPK5
```

### Bước 3 — Compile contracts

```bash
npx hardhat compile
# → Sinh ra artifacts/ (ABI + bytecode)
```

### Bước 4 — Chạy test (không cần Ganache)

```bash
# Toàn bộ test suite
npx hardhat test

# Test từng file
npx hardhat test test/HSTToken.test.js
npx hardhat test test/Governance.test.js

# Kèm gas report
REPORT_GAS=true npx hardhat test
```

### Bước 5 — Mở Ganache

```
Ganache UI:
  ├── RPC Server: HTTP://127.0.0.1:7545
  ├── Chain ID: 1337
  └── Accounts: cho sẳn 10 tài khoản, 100 ETH mỗi tài khoản
```

### Bước 6 — Deploy hệ thống

```bash
npx hardhat run scripts/setup_demo.js --network ganache
```

Output mong đợi:
```
✅ HSTToken deployed: 0x...
✅ ShareholderRegistry deployed: 0x...
✅ GovernanceContract deployed: 0x...
✅ TimelockController deployed: 0x...
✅ Registered: Chủ tịch HĐQT — 4,500,000 HST, Tier 3
...
✅ Saved → dashboard/contract_addresses.json
```

### Bước 7 — Tạo chiến dịch demo (4 kịch bản)

```bash
npx hardhat run scripts/setup_campaign.js --network ganache
```

### Bước 8 — (Tùy chọn) Thêm chiến dịch để tự vote

```bash
npx hardhat run scripts/add_campaigns.js --network ganache
```

### Bước 9 — Chạy Dashboard

```bash
# Windows PowerShell
$env:PYTHONUTF8=1
streamlit run dashboard/app.py --server.fileWatcherType none

# macOS / Linux
PYTHONUTF8=1 streamlit run dashboard/app.py --server.fileWatcherType none
```

Mở trình duyệt: **http://localhost:8501**

---

## 🔄 Workflow — Luồng hoạt động chi tiết

### Workflow 1: Deploy & Setup

```
Máy tính cục bộ                    Ganache (EVM)
─────────────────                  ──────────────
setup_demo.js
  │
  ├─ deploy HSTToken          ──►  [Contract] HSTToken
  │    └─ mint 10M → burn 10M
  │
  ├─ deploy Registry          ──►  [Contract] ShareholderRegistry
  │    └─ transferOwnership
  │         HSTToken → Registry
  │
  ├─ deploy Governance        ──►  [Contract] GovernanceContract
  │
  ├─ deploy Timelock          ──►  [Contract] HSTTimelockController
  │
  ├─ addShareholder(×5)       ──►  Registry.mint() → HSTToken
  │    └─ mỗi cổ đông nhận        Cổ đông nhận đúng số HST
  │       đúng số HST
  │
  ├─ delegate(×5)             ──►  ERC20Votes snapshot kích hoạt
  │
  └─ ghi file JSON            ──►  dashboard/contract_addresses.json
```

### Workflow 2: Bỏ phiếu thông thường (Standard Vote)

```
Cổ đông (Dashboard)                Ganache (EVM)
───────────────────                ──────────────
1. Nhập address + private key
2. verify: derivedAddress == inputAddress
3. canVote() ──────────────────►  Registry.canVote(wallet)
                                    = isActive && lockUntil < now && balance > 0
4. Chọn chiến dịch ACTIVE
5. Bấm FOR / AGAINST / ABSTAIN
6. Build transaction
7. Sign bằng private key
8. send_raw_transaction ────────►  GovernanceContract.castVote()
                                    ├─ require: ACTIVE status
                                    ├─ require: trước votingDeadline
                                    ├─ require: chưa bỏ phiếu
                                    ├─ require: canVote() == true
                                    ├─ weight = getEffectiveWeight()
                                    │     Linear    → getPastVotes(snapshotBlock)
                                    │     Quadratic → √(getPastVotes)
                                    │     Equal     → 1
                                    └─ _recordVote() → cập nhật forVotes/...
9. Nhận receipt ← ─ ─ ─ ─ ─ ─ ─
10. Refresh UI → hiện kết quả mới
```

### Workflow 3: Commit-Reveal (Bỏ phiếu kín)

```
Giai đoạn COMMIT (7 ngày):
─────────────────────────
Cổ đông
  │
  ├─ Chọn phiếu: FOR / AGAINST / ABSTAIN (chưa lộ)
  ├─ Tạo salt = random 32 bytes
  ├─ hash = keccak256(option_byte || salt_bytes32 || msg.sender)
  └─ commitVote(campaignId, hash) ──────────────────────────►  on-chain
                                    commitments[cId][sender] = hash
                                    → không ai biết phiếu thực

Sau commitDeadline → transitionToReveal():
─────────────────────────────────────────
  CAMPAIGN_MANAGER_ROLE gọi transitionToReveal()
  Status: COMMIT → REVEAL

Giai đoạn REVEAL (3 ngày):
──────────────────────────
Cổ đông (cần salt đã lưu)
  │
  ├─ Nhập lại: option + salt
  └─ revealVote(campaignId, option, salt) ─────────────────►  on-chain
                                    expectedHash = keccak256(option||salt||sender)
                                    require: commitments[cId][sender] == expectedHash
                                    → _recordVote() ghi nhận phiếu

Sau revealDeadline → finalizeCampaign():
  → EXECUTED hoặc DEFEATED
```

### Workflow 4: Finalize & Timelock

```
Bất kỳ ai                          GovernanceContract
──────────                         ──────────────────
finalizeCampaign(id) ────────────► require: status == ACTIVE hoặc REVEAL
                                   require: block.timestamp >= votingDeadline
                                   _checkResult():
                                     participation = totalVoted / totalSupply
                                     if participation < quorumBps → DEFEATED
                                     forBps = forVotes / (for+against)
                                     if forBps > passThreshold → EXECUTED
                                   emit CampaignFinalized
                         ◄────────
(Tương lai — Phase 5):
EXECUTED → Governance queue lên HSTTimelockController
delay 2/7/14 ngày theo ProposalType
→ bất kỳ ai execute sau delay 
```

---

## 🧪 Test Coverage

| File | Số test | Nội dung |
|---|---|---|
| `HSTToken.test.js` | 12 test | Deployment, Mint, Burn, Voting Power, Delegation, Snapshot |
| `Governance.test.js` | ~20 test | Campaign creation, ID-101 (Linear PASS), ID-102 (Major PASS), ID-103 (Quadratic), ID-104 (Commit-Reveal) |

```bash
# Chạy và xem coverage
npx hardhat coverage
```

---

## 🗺️ Kịch bản Demo — 4+4 chiến dịch

### Nhóm 1: Đã bỏ phiếu sẵn (setup_campaign.js)

| ID | Tiêu đề | Loại | Cơ chế | Kết quả |
|---|---|---|---|---|
| **1** | Phê duyệt ngân sách R&D 2025 | Routine | Linear | ✅ PASS |
| **2** | Chia cổ tức 15% năm 2024 | Major | Linear | ✅ PASS |
| **3** | Bầu CEO nhiệm kỳ 2025-2028 | Major | Quadratic | ❌ KHÔNG ĐẠT |
| **4** | Sáp nhập M&A — TechCorp Ltd | M&A | Linear | 🔒 COMMIT |

### Nhóm 2: Để trống để tự vote (add_campaigns.js)

| ID | Tiêu đề | Loại | Cơ chế | Trạng thái |
|---|---|---|---|---|
| **5** | Mở rộng văn phòng Q3-2025 | Routine | Linear | 🟢 ACTIVE |
| **6** | Tăng vốn điều lệ 20% | Major | Linear | 🟢 ACTIVE |
| **7** | Bầu Trưởng ban Kiểm soát | Major | Equal | 🟢 ACTIVE |
| **8** | Hợp tác VietTech Group | M&A | Linear | 🔒 COMMIT |

---

## 📐 Kiến trúc Tổng thể

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                    │
│              dashboard/app.py  (Port 8501)               │
└──────────────────────┬──────────────────────────────────┘
                       │ web3.py calls
                       ▼
┌─────────────────────────────────────────────────────────┐
│              utils/web3_helpers.py                       │
│   connect · load_abi · get_contracts · read on-chain    │
└──────────────────────┬──────────────────────────────────┘
                       │ JSON-RPC (HTTP)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 Ganache UI (Port 7545)                   │
│                  EVM — Chain ID 1337                     │
│                                                         │
│  ┌──────────────┐  ┌──────────────────────────────┐    │
│  │  HSTToken    │  │    ShareholderRegistry         │    │
│  │ ERC20Votes   │◄─┤  canVote · tier · addSH       │    │
│  │ snapshot     │  │  owns HSTToken (mint/burn)    │    │
│  └──────┬───────┘  └──────────────────────────────┘    │
│         │ getPastVotes                                   │
│         ▼                                               │
│  ┌──────────────────────────────────────────────┐      │
│  │           GovernanceContract                  │      │
│  │  createCampaign · castVote · commitVote       │      │
│  │  revealVote · finalizeCampaign                │      │
│  │  Linear / Quadratic / Equal weight            │      │
│  └──────────────────────┬───────────────────────┘      │
│                          │ queue (Phase 5)               │
│                          ▼                              │
│  ┌──────────────────────────────────────────────┐      │
│  │         HSTTimelockController                 │      │
│  │  Routine 2d · Major 7d · M&A 14d             │      │
│  └──────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ Công cụ & Công nghệ

| Công cụ | Phiên bản | Vai trò |
|---|---|---|
| **Solidity** | 0.8.20 | Ngôn ngữ smart contract |
| **OpenZeppelin** | ^4.9.6 | ERC20Votes, AccessControl, TimelockController |
| **Hardhat** | ^2.22.3 | Compile, test, deploy, console |
| **ethers.js** | ^6.11.1 | Tương tác contract trong JS |
| **Chai** | ^4.4.1 | Assertion test |
| **Hardhat Toolbox** | ^5.0.0 | Test helpers, network helpers |
| **Python** | ≥ 3.10 | Dashboard và utility |
| **web3.py** | 6.15.1 | Kết nối blockchain từ Python |
| **eth-account** | 0.11.2 | Ký transaction từ Python |
| **Streamlit** | 1.33.0 | Dashboard web UI |
| **Ganache UI** | latest | Local EVM để phát triển |

---

## 🌟 Phương hướng Phát triển Tương lai

### Phase 5 — Testnet & Tích hợp Timelock UI *(ngắn hạn)*

- **Deploy lên Polygon Amoy testnet** — cấu hình sẵn trong `hardhat.config.js`
- **Hoàn thiện vòng Timelock** — UI cho queue/execute nghị quyết sau delay
- **Xác minh contract trên PolygonScan** — `npx hardhat verify --network amoy`

### Phase 6 — Bảo mật & Audit *(trung hạn)*

- **Formal audit** — thuê audit firm kiểm tra GovernanceContract và Registry
- **Fuzz testing** — dùng Echidna/Foundry để kiểm tra edge case
- **Reentrancy audit** — xem xét thêm guard cho finalizeCampaign
- **Upgrade pattern** — chuyển sang UUPS Proxy để nâng cấp contract an toàn

### Phase 7 — MetaMask & Web3 UX *(trung hạn)*

- **Tích hợp MetaMask** — thay private key nhập tay bằng browser wallet
- **WalletConnect** — hỗ trợ mobile wallet
- **Thay Streamlit bằng React** — dùng wagmi + viem cho UX tốt hơn
- **Real-time update** — WebSocket events thay vì Refresh thủ công

### Phase 8 — Token Economics *(dài hạn)*

- **Delegation UI** — giao diện ủy quyền biểu quyết cho đại diện
- **Cổ tức on-chain** — smart contract phân phối ETH/stablecoin tự động
- **Token lock vesting** — cơ chế vesting cho cổ đông sáng lập
- **Governance token transfer restriction** — giới hạn chuyển nhượng theo tier

### Phase 9 — Multi-company & SaaS *(dài hạn)*

- **Factory pattern** — deploy một bộ contract riêng cho từng công ty
- **Subgraph indexing** — The Graph để query on-chain data nhanh hơn
- **IPFS document storage** — lưu tài liệu nghị quyết lên IPFS
- **Legal wrapper** — tích hợp chữ ký điện tử với hệ thống pháp lý Việt Nam

---

## 🐛 Lỗi đã biết & Cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `ABI không tìm thấy` | Chưa compile | `npx hardhat compile` |
| `Không kết nối Ganache` | Ganache chưa chạy | Mở Ganache UI trước |
| `canVote = false` | Chưa self-delegate | Chạy lại `setup_demo.js` |
| `hash mismatch` khi Reveal | Sai option hoặc salt | Dùng đúng option+salt đã commit |
| `commit not ended` khi transitionToReveal | Chưa hết commitDeadline | Dùng nút "Nhảy qua commitDeadline" |
| `PYTHONUTF8` error trên Windows | Encoding | Chạy `$env:PYTHONUTF8=1` trước |

---

## 📝 Ghi chú Bảo mật

> ⚠️ **ĐÂY LÀ MÔI TRƯỜNG DEMO — KHÔNG DÙNG PRODUCTION**

- Private key được nhập trực tiếp vào dashboard — **chỉ dùng tài khoản Ganache test**
- Không dùng ví chứa tiền thật trên dashboard này
- Môi trường production cần: MetaMask, hardware wallet, hoặc HSM (nhưng tốn phí)
- Contract chưa được audit bảo mật chuyên nghiệp

---
