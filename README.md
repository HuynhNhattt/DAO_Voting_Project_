# 🏛️ DAO Voting System — Hệ thống Biểu quyết Cổ đông Blockchain

> Đồ án sinh viên — Blockchain DAO Platform v2.1.0  
> Stack: Solidity + Hardhat + Web3.py + Streamlit

---

## 📁 Cấu trúc Dự án

```
dao-voting-system/
│
├── contracts/                   # Smart Contracts (Solidity)
│   ├── HSTToken.sol             # ERC-20 + ERC20Votes token
│   ├── ShareholderRegistry.sol  # Quản lý danh sách cổ đông
│   ├── GovernanceContract.sol   # Logic biểu quyết chính
│   └── HSTTimelockController.sol# Trì hoãn thực thi
│
├── scripts/
│   └── setup_demo.js            # Deploy contracts + phân bổ token
│
├── test/
│   ├── HSTToken.test.js         # Unit test token
│   └── Governance.test.js       # Integration test 4 kịch bản
│
├── utils/
│   ├── distribute_tokens.py     # Tính phân bổ token (Python)
│   └── web3_helpers.py          # Helper kết nối Web3 cho dashboard
│
├── dashboard/
│   ├── app.py                   # Streamlit dashboard (Phase 4)
│   └── contract_addresses.json  # Auto-generated sau khi deploy
│
├── docs/                        # Tài liệu bổ sung
├── hardhat.config.js
├── package.json
├── requirements.txt
└── .env.
```

---

## 🚀 Hướng dẫn Chạy

### Yêu cầu

- Node.js >= 18
- Python >= 3.10
- Ganache UI hoặc CLI

### Bước 1: Cài dependencies

```bash
# JavaScript (Hardhat + OpenZeppelin)
npm install

# Python (Web3 + Streamlit)
pip install -r requirements.txt
```

### Bước 2: Cấu hình môi trường

```bash
cp .env .env
# Điền private keys từ Ganache vào .env
```

### Bước 3: Compile contracts

```bash
npx hardhat compile
```

### Bước 4: Chạy test

```bash
# Chạy tất cả test (không cần Ganache)
npx hardhat test

# Xem gas usage
npm run test:gas

# Coverage
npm run coverage
```

### Bước 5: Deploy lên Ganache

```bash
# Mở Ganache UI trước, port 7545, chainId 1337
npx hardhat run scripts/setup_demo.js --network ganache
```

### Bước 6: Chạy Dashboard

```bash
$env:PYTHONUTF8=1
streamlit run dashboard/app.py --server.fileWatcherType none
# Mở: http://localhost:8501
```

---

## 📊 Kịch bản Demo

| ID | Tên | Cơ chế | Kết quả kỳ vọng |
|---|---|---|---|
| ID-101 | Phê duyệt ngân sách R&D | Linear, Routine | ✅ Pass (70% > 50%) |
| ID-102 | Chia cổ tức 15% | Linear, Major | ✅ Pass (70% > 66%) |
| ID-103 | Bầu CEO mới | Linear vs Quadratic | So sánh tỷ lệ quyền lực |
| ID-104 | Sáp nhập M&A | Commit-Reveal | Test bỏ phiếu kín |

---

## 🗺️ Lộ trình

- [x] **Phase 1** — Smart Contracts (Token + Registry + Governance + Timelock)
- [x] **Phase 2** — Deploy scripts + Test suite (4 kịch bản)
- [x] **Phase 3** — Python utilities (distribution + web3 helpers)
- [ ] **Phase 4** — Streamlit Dashboard
- [ ] **Phase 5** — Testnet deploy (Polygon Amoy)
