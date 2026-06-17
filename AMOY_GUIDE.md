# 🔷 Hướng dẫn triển khai lên Polygon Amoy Testnet

## Tại sao chọn Polygon Amoy?

| Tiêu chí | Ganache (Local) | Polygon Amoy (Testnet) |
|---|---|---|
| Internet | Không cần | Cần |
| Chi phí | Miễn phí | Miễn phí (MATIC test) |
| Ai xem được | Chỉ máy bạn | Cả thế giới |
| Tốc độ | Ngay lập tức | ~2-5 giây/block |
| Demo được online | ❌ | ✅ |
| Explorer (verify) | ❌ | ✅ Polygonscan |
| Giống production | ❌ | ✅ Gần nhất |

---

## Bước 1: Cài đặt môi trường

```bash
# Cài dependencies (nếu chưa)
npm install

# Copy file .env
cp .env.example .env
```

---

## Bước 2: Cấu hình .env

Mở file `.env` và điền:

```env
# Private key ví MetaMask của bạn
# MetaMask → Ba chấm → Account details → Show private key
DEPLOYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# RPC URL (dùng mặc định hoặc Alchemy miễn phí)
AMOY_RPC_URL=https://rpc-amoy.polygon.technology

# Polygonscan API (để verify contract — tuỳ chọn)
POLYGONSCAN_API_KEY=YOUR_API_KEY
```

> ⚠️ **QUAN TRỌNG:** Không commit file `.env` lên Git!

---

## Bước 3: Lấy MATIC test (miễn phí)

1. Mở [https://faucet.polygon.technology](https://faucet.polygon.technology)
2. Chọn **Amoy**
3. Dán địa chỉ ví MetaMask của bạn
4. Nhấn **Submit** → nhận ~0.5 MATIC test
5. Lặp lại nếu cần (cần ~0.3-0.5 MATIC để deploy đủ 5 contract)

---

## Bước 4: Deploy

```bash
# Compile contracts
npx hardhat compile

# Deploy lên Amoy
npx hardhat run scripts/deploy_amoy.js --network amoy
```

Kết quả thành công sẽ in ra:
```
✅ HSTToken: 0xABC...
✅ ShareholderRegistry: 0xDEF...
✅ GovernanceContract: 0xGHI...
✅ TimelockController: 0xJKL...
✅ VotingCertificate: 0xMNO...
🔗 https://amoy.polygonscan.com/address/0xABC...
```

File địa chỉ được lưu tại: `dashboard/contract_addresses_amoy.json`

---

## Bước 5: Thêm Amoy vào MetaMask

| Trường | Giá trị |
|---|---|
| Network Name | Polygon Amoy Testnet |
| RPC URL | https://rpc-amoy.polygon.technology |
| Chain ID | 80002 |
| Symbol | MATIC |
| Explorer | https://amoy.polygonscan.com |

---

## Bước 6: Chạy Dashboard với Amoy

```bash
# Bật chế độ Amoy
set AMOY_MODE=true       # Windows
export AMOY_MODE=true    # Linux/Mac

# Chạy Dashboard
streamlit run dashboard/app.py
```

Hoặc chọn trực tiếp trong sidebar Dashboard: **🔷 Polygon Amoy (Testnet)**

---

## Bước 7 (Tuỳ chọn): Verify contract trên Polygonscan

Sau khi deploy, verify để ai cũng đọc được source code:

```bash
# Verify HSTToken
npx hardhat verify --network amoy \
  <HST_TOKEN_ADDRESS> \
  "<DEPLOYER_ADDRESS>"

# Verify GovernanceContract
npx hardhat verify --network amoy \
  <GOVERNANCE_ADDRESS> \
  "<HST_ADDRESS>" "<REGISTRY_ADDRESS>" "<DEPLOYER_ADDRESS>"
```

Sau khi verify, contract trên Polygonscan sẽ có tab **Contract** màu xanh ✅

---

## Lưu ý khi demo

- Mỗi cổ đông cần có MATIC test để bỏ phiếu (trả gas)
- Block time trên Amoy: ~2-5 giây (không ngay lập tức như Ganache)
- Snapshot block được chốt khi tạo campaign — đây là testnet thật
- Mọi transaction đều có link Polygonscan để xem và verify
