# 🏛️ DAO Voting System v2.0 — Hướng dẫn chạy đầy đủ

## Tổng quan các tính năng đã tích hợp

| # | Tính năng | Files chính |
|---|---|---|
| 1 | Polygon Amoy Testnet | `hardhat.config.js`, `scripts/deploy_amoy.js`, `utils/web3_helpers_amoy.py` |
| 2 | KYC on-chain | `contracts/IdentityVerifier.sol`, `utils/kyc_service.py`, `dashboard/pages/kyc_page.py` |
| 3 | Xác thực ví bằng ký số | `utils/auth_service.py`, `dashboard/pages/login_page.py` |
| + | Timelock thật | `contracts/GovernanceContract.sol` (setTimelock), `dashboard/pages/timelock_page.py` |
| + | Biên bản chữ ký số | `contracts/VotingCertificate.sol`, `utils/certificate_generator.py` |

---

## Cài đặt

```bash
# Node dependencies
npm install

# Python dependencies
pip install -r requirements_v2.txt --break-system-packages
```

---

## Chạy trên Ganache (Local)

```bash
# 1. Mở Ganache UI (port 7545), copy private keys vào .env
cp .env.example .env
# Điền GANACHE_PRIVATE_KEYS=0xKEY0,0xKEY1,0xKEY2,0xKEY3,0xKEY4

# 2. Compile contracts
npx hardhat compile

# 3. Deploy toàn bộ (1 lệnh duy nhất)
npm run deploy:ganache
# Hoặc: npx hardhat run scripts/setup_demo_full.js --network ganache

# 4. Tạo campaigns demo
npm run campaign:ganache
# Hoặc: npx hardhat run scripts/setup_campaign.js --network ganache

# 5. Chạy Dashboard
npm run dashboard
# Hoặc: streamlit run dashboard/app_v2.py
```

---

## Chạy trên Polygon Amoy Testnet

```bash
# 1. Cấu hình .env
cp .env.example .env
# Điền DEPLOYER_PRIVATE_KEY và AMOY_RPC_URL

# 2. Lấy MATIC test tại: https://faucet.polygon.technology

# 3. Deploy
npm run deploy:amoy
# Hoặc: npx hardhat run scripts/deploy_amoy.js --network amoy

# 4. Chạy Dashboard với Amoy
npm run dashboard:amoy
# Hoặc: AMOY_MODE=true streamlit run dashboard/app_v2.py
```

---

## Cấu trúc thư mục

```
dao-voting-system/
├── contracts/
│   ├── HSTToken.sol               # ERC20Votes token
│   ├── ShareholderRegistry.sol    # Quản lý cổ đông + KYC
│   ├── GovernanceContract.sol     # Logic biểu quyết + Timelock thật
│   ├── HSTTimelockController.sol  # Timelock với delay constants
│   ├── VotingCertificate.sol      # Biên bản chữ ký số
│   └── IdentityVerifier.sol       # KYC on-chain (MỚI)
│
├── scripts/
│   ├── setup_demo_full.js         # Deploy tất cả (1 lệnh)
│   ├── setup_campaign.js          # Tạo campaigns demo
│   └── deploy_amoy.js             # Deploy lên Polygon Amoy
│
├── dashboard/
│   ├── app_v2.py                  # Dashboard chính (mới)
│   ├── pages/
│   │   ├── login_page.py          # Đăng nhập bằng ký số (Feature 3)
│   │   ├── kyc_page.py            # KYC on-chain (Feature 2)
│   │   ├── kyc_status_widget.py   # KYC badge widget
│   │   ├── timelock_page.py       # Quản lý Timelock
│   │   ├── certificate_page.py    # Biên bản chữ ký số
│   │   └── amoy_network_widget.py # Network selector (Feature 1)
│   └── contract_addresses.json    # Địa chỉ contract (auto-generated)
│
├── utils/
│   ├── web3_helpers.py            # Core Web3 helpers
│   ├── web3_helpers_amoy.py       # Multi-network support (Feature 1)
│   ├── auth_service.py            # Challenge-response auth (Feature 3)
│   ├── kyc_service.py             # KYC signing service (Feature 2)
│   ├── certificate_generator.py   # Tạo biên bản PDF/JSON
│   └── on_off_chain_explainer.py  # Giải thích on/off-chain
│
├── hardhat.config.js              # Config Ganache + Amoy
├── package.json                   # npm scripts
├── requirements_v2.txt            # Python dependencies
└── .env.example                   # Template cấu hình
```

---

## Flow đăng nhập mới (Feature 3)

```
TRƯỚC (không an toàn):
  Nhập private key → textbox → lưu session_state

SAU (an toàn):
  1. Nhập địa chỉ ví → tạo challenge
  2. Nhập private key → ký challenge locally → private key xóa ngay
  3. Server verify signature → tạo session token
  4. Mọi transaction: lấy key từ RAM session → ký → xóa
```

---

## Flow KYC (Feature 2)

```
1. [OFF-CHAIN] Người dùng điền tên/CCCD/ngày sinh trên Dashboard
2. [OFF-CHAIN] Admin xác minh giấy tờ thật
3. [OFF-CHAIN] Admin ký KYC proof (kyc_service.py)
4. [ON-CHAIN]  Người dùng submit proof → IdentityVerifier.submitKYC()
5. [ON-CHAIN]  Admin gọi registry.addShareholderWithKYC()
```

---

## Flow Timelock thật

```
finalizeCampaign()
  → PASS  → timelock.schedule() → QUEUED (chờ 2/7/14 ngày)
  → DEFEAT→ DEFEATED (kết thúc)

Sau delay:
executeDecision()
  → timelock.execute()
  → governance._finalizeExecution()
  → EXECUTED
```
