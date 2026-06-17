# 🏛️ Hệ thống Biểu quyết Cổ đông Chiến lược dựa trên Blockchain

> **Nhóm 7** — Môn: Chuỗi khối và Tài sản Crypto  
> **GVHD:** Nguyễn Minh Nhật  
> **Công nghệ:** Solidity · Hardhat · Python · Streamlit · Polygon Amoy

---

## 📌 Giới thiệu

Hệ thống biểu quyết cổ đông phi tập trung (DAO) cho phép các cổ đông thực hiện quyền biểu quyết minh bạch, chống gian lận thông qua công nghệ blockchain. Toàn bộ phiếu bầu được ghi nhận on-chain, kết quả tự động tính toán mà không cần bên trung gian.

---

## ✨ Tính năng chính

| Tính năng | Mô tả |
|---|---|
| 🗳️ **3 cơ chế biểu quyết** | Linear / Quadratic / Equal |
| 🔐 **Commit-Reveal** | Bỏ phiếu kín chống ảnh hưởng lẫn nhau |
| ⏳ **Timelock** | Delay 2/7/14 ngày trước khi quyết định có hiệu lực |
| 🪪 **KYC on-chain** | Xác thực danh tính bằng chữ ký ECDSA của Admin |
| 📄 **Biên bản chữ ký số** | Tự động tạo sau finalize, verify được on-chain |
| 🔑 **Xác thực ví** | Challenge-response thay thế nhập private key trực tiếp |
| 🔷 **Polygon Amoy** | Triển khai trên testnet thực tế công khai |

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────┐
│              Dashboard (Streamlit)                   │
│  8 tabs: Tổng quan · Bỏ phiếu · Cổ đông            │
│          Phân tích · Biên bản · Timelock            │
│          KYC · On/Off-chain                         │
└─────────────────────┬───────────────────────────────┘
                      │ Web3.py
┌─────────────────────▼───────────────────────────────┐
│              Middleware (Python)                     │
│  web3_helpers.py      · web3_helpers_amoy.py        │
│  auth_service.py      · kyc_service.py              │
│  certificate_generator.py                           │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│              Blockchain Layer                        │
│  HSTToken · ShareholderRegistry · GovernanceContract│
│  HSTTimelockController · VotingCertificate          │
│  IdentityVerifier                                   │
│                                                     │
│  🏠 Ganache Local (dev)  |  🔷 Polygon Amoy (test) │
└─────────────────────────────────────────────────────┘
```

---

## 📦 Smart Contracts

| Contract | Chức năng |
|---|---|
| `HSTToken.sol` | ERC20Votes — chứng nhận cổ phần, quyền biểu quyết, xác định Tier |
| `ShareholderRegistry.sol` | Quản lý danh sách cổ đông, canVote(), tích hợp KYC |
| `GovernanceContract.sol` | Lõi logic biểu quyết, Timelock flow, tạo biên bản |
| `HSTTimelockController.sol` | Delay 2/7/14 ngày theo ProposalType |
| `VotingCertificate.sol` | Biên bản chữ ký số on-chain sau finalize |
| `IdentityVerifier.sol` | KYC on-chain với Admin ECDSA signature pattern |

---

## 📁 Cấu trúc thư mục

```
DAO_Voting_Project/
│
├── contracts/                          # Smart Contracts (Solidity)
│   ├── HSTToken.sol                    # ERC20Votes token
│   ├── ShareholderRegistry.sol         # Quản lý cổ đông + KYC
│   ├── GovernanceContract.sol          # Lõi biểu quyết + Timelock
│   ├── HSTTimelockController.sol       # Timelock với delay constants
│   ├── VotingCertificate.sol           # Biên bản chữ ký số
│   └── IdentityVerifier.sol            # KYC on-chain
│
├── scripts/                            # Deploy & Setup Scripts
│   ├── setup_demo_full.js              # Deploy toàn bộ 6 contracts (dùng cái này)
│   ├── setup_demo.js                   # Deploy cơ bản 4 contracts
│   ├── setup_campaign.js               # Tạo 4 campaigns demo có votes sẵn
│   ├── setup_demo_kyc.js               # Deploy thêm IdentityVerifier
│   └── deploy_amoy.js                  # Deploy lên Polygon Amoy Testnet
│
├── dashboard/                          # Giao diện Streamlit
│   ├── app_v2.py                       # Dashboard chính — 8 tabs (CHẠY CÁI NÀY)
│   ├── app_auth_patch.py               # Hướng dẫn tích hợp auth
│   ├── app_kyc_patch.py                # Hướng dẫn tích hợp KYC
│   ├── app_timelock_patch.py           # Hướng dẫn tích hợp Timelock
│   └── pages/                          # Các trang con của Dashboard
│       ├── login_page.py               # Đăng nhập bằng chữ ký số
│       ├── kyc_page.py                 # Form KYC + Admin review
│       ├── kyc_status_widget.py        # Badge trạng thái KYC
│       ├── timelock_page.py            # Quản lý QUEUED campaigns
│       ├── certificate_page.py         # Xem + download biên bản
│       └── amoy_network_widget.py      # Toggle Ganache / Amoy
│
├── utils/                              # Python Helpers
│   ├── web3_helpers.py                 # Core: kết nối, đọc contract
│   ├── web3_helpers_amoy.py            # Multi-network: Ganache + Amoy
│   ├── auth_service.py                 # Xác thực ví bằng challenge-response
│   ├── kyc_service.py                  # Admin ký KYC proof off-chain
│   ├── certificate_generator.py        # Xuất biên bản PDF/JSON
│   └── on_off_chain_explainer.py       # Giải thích on/off-chain
│
├── test/                               # Unit Tests (30+ test cases)
│   ├── HSTToken.test.js
│   └── Governance.test.js
│
├── .env.example                        # Mẫu cấu hình (copy → .env)
├── .gitignore
├── hardhat.config.js                   # Config Ganache + Polygon Amoy
├── package.json
├── requirements_v2.txt                 # Python dependencies
├── AMOY_GUIDE.md                       # Hướng dẫn deploy Polygon Amoy
├── KYC_GUIDE.md                        # Hướng dẫn tích hợp KYC
├── INTEGRATION_GUIDE.md                # Hướng dẫn tích hợp tổng thể
└── README.md                           # File này
```

---

## 🚀 Cài đặt và Chạy

### Yêu cầu
- Node.js ≥ 18 · npm ≥ 9
- Python ≥ 3.10
- Ganache UI (port 7545)

### Bước 1 — Cài đặt dependencies

```bash
npm install
pip install -r requirements_v2.txt
```

### Bước 2 — Cấu hình .env

```bash
cp .env.example .env
# Mở .env, điền 5 private keys từ Ganache UI (tab Accounts → icon 🔑)
```

### Bước 3 — Compile & Deploy (Ganache)

```bash
# Mở Ganache UI trước
npx hardhat compile
npx hardhat run scripts/setup_demo_full.js --network ganache
npx hardhat run scripts/setup_campaign.js --network ganache
```

### Bước 4 — Chạy Dashboard

```powershell
# Windows PowerShell
$env:PYTHONUTF8=1; $env:PYTHONPATH="utils;dashboard\pages"; streamlit run dashboard/app_v2.py
```

```bash
# Linux / Mac
PYTHONUTF8=1 PYTHONPATH="utils:dashboard/pages" streamlit run dashboard/app_v2.py
```

Mở trình duyệt: **http://localhost:8501**

### Thêm campaigns để tự vote

```bash
npx hardhat run scripts/add_new_campaigns.js --network ganache
```

### Deploy lên Polygon Amoy (tuỳ chọn)

```bash
# Thêm DEPLOYER_PRIVATE_KEY vào .env
# Lấy MATIC test miễn phí: https://faucet.polygon.technology
npx hardhat run scripts/deploy_amoy.js --network amoy
# Chạy Dashboard với Amoy:
# $env:AMOY_MODE="true"; streamlit run dashboard/app_v2.py
```

---

## 👥 Cổ đông Demo

| Tên | HST | Tỷ lệ | Tier |
|---|---|---|---|
| Chủ tịch HĐQT | 4,500,000 | 45% | 3 — Sáng lập |
| Quỹ phát triển | 2,500,000 | 25% | 2 — Chiến lược |
| Cổ đông A (Tổ chức) | 1,500,000 | 15% | 1 — Tổ chức |
| Cổ đông B (Tổ chức) | 1,000,000 | 10% | 1 — Tổ chức |
| Cổ đông C (Nhỏ lẻ) | 500,000 | 5% | 0 — Nhỏ lẻ |

---

## 🗳️ Kịch bản Demo

| ID | Chiến dịch | Loại | Cơ chế | Kết quả |
|---|---|---|---|---|
| 101 | Phê duyệt ngân sách R&D 2025 | Routine | Linear | ✅ PASS |
| 102 | Chia cổ tức 15% năm 2024 | Major | Linear | ✅ PASS |
| 103 | Bầu CEO mới — So sánh Linear vs Quadratic | Major | Quadratic | ❌ DEFEAT |
| 104 | Sáp nhập M&A — TechCorp Ltd | M&A | Commit-Reveal | 🔒 COMMIT |

---

## 📊 Ngưỡng biểu quyết

| Loại | Thông qua | Quorum | Voting | Timelock |
|---|---|---|---|---|
| ROUTINE | > 50% | 10% | 7 ngày | 2 ngày |
| MAJOR | > 66% | 20% | 14 ngày | 7 ngày |
| M&A | > 75% | 30% | 21 ngày | 14 ngày |

---

## 🔒 Bảo mật

- **Snapshot voting** — ERC20Votes chặn mua token "phút chót"
- **Commit-Reveal** — bỏ phiếu kín, chống ảnh hưởng lẫn nhau
- **Timelock** — delay trước khi quyết định có hiệu lực, cổ đông có thời gian phản ứng
- **KYC on-chain** — 1 CCCD = 1 ví, chặn Sybil Attack trong Quadratic
- **Xác thực ký số** — private key không bao giờ lên server
- **ReentrancyGuard** — chống tấn công reentrancy
- **Trustless execution** — `finalizeCampaign()` và `executeDecision()` ai cũng gọi được

---

## 🛠️ Tech Stack

**Blockchain:** Solidity 0.8.20 · OpenZeppelin 4.9.6 · Hardhat 2.22 · Ganache · Polygon Amoy  
**Backend:** Python 3.10+ · Web3.py 6.15 · eth-account 0.11.2  
**Frontend:** Streamlit 1.33  

---

*Đồ án môn Chuỗi khối và Tài sản Crypto — UEH 2026*
