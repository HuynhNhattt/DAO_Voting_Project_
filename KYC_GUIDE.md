# 🪪 Hướng dẫn KYC on-chain

## Tóm tắt thay đổi

| Trước | Sau |
|---|---|
| `identityHash = keccak256("DEMO_CCCD_0_0x...")` giả | `identityHash = keccak256(tênThật + CCCD + ngàySinh)` thật |
| Admin tự điền hash, không xác minh | Admin ký off-chain sau khi xác minh giấy tờ thật |
| 1 người có thể đăng ký nhiều ví | 1 CCCD chỉ đăng ký được 1 ví (chặn Sybil Attack) |
| KYC không hết hạn | KYC hết hạn sau 1 năm |

---

## Flow hoàn chỉnh

```
[OFF-CHAIN] Người dùng điền tên, CCCD, ngày sinh → Dashboard
     ↓
[OFF-CHAIN] KYCService.submit_kyc_request() → lưu pending
     ↓
[OFF-CHAIN] Admin xác minh giấy tờ thật (manual)
     ↓
[OFF-CHAIN] KYCService.approve_kyc() → tạo chữ ký ECDSA
     ↓
[ON-CHAIN]  Người dùng gọi IdentityVerifier.submitKYC(signature)
     ↓
[ON-CHAIN]  Contract verify chữ ký → lưu identityHash + kycRecord
     ↓
[ON-CHAIN]  Admin gọi registry.addShareholderWithKYC(wallet, ...)
            → tự đọc identityHash từ IdentityVerifier
```

---

## Deploy

```bash
# Bước 1: Deploy các contract chính
npx hardhat run scripts/setup_demo.js --network ganache

# Bước 2: Deploy IdentityVerifier và link vào Registry
npx hardhat run scripts/setup_demo_kyc.js --network ganache

# Bước 3: Chạy Dashboard
streamlit run dashboard/app.py
```

---

## Bật KYC bắt buộc (production)

```javascript
// Trong Hardhat console hoặc script:
const registry = await ethers.getContractAt("ShareholderRegistry", REGISTRY_ADDRESS);
await registry.setRequireKYC(true);
// Sau đó addShareholder() sẽ revert → phải dùng addShareholderWithKYC()
```

---

## Dữ liệu ON-CHAIN vs OFF-CHAIN

| Dữ liệu | Lưu ở đâu | Ai truy cập được |
|---|---|---|
| `identityHash` | ON-CHAIN (IdentityVerifier) | Công khai |
| `kycHash` | ON-CHAIN | Công khai |
| `kycLevel`, `expiresAt` | ON-CHAIN | Công khai |
| Tên thật, số CCCD | OFF-CHAIN (Admin server) | Chỉ Admin |
| Ảnh CCCD | OFF-CHAIN | Chỉ Admin |
| Private key KYC Signer | OFF-CHAIN (.env) | Chỉ Admin |

---

## Thêm vào app.py

```python
from pages.kyc_page import render_kyc_page

# Trong tabs:
with tab_kyc:
    render_kyc_page(
        contracts=contracts,
        w3=w3,
        wallet=st.session_state.get("wallet_address"),
        private_key=st.session_state.get("private_key"),
        is_admin=st.session_state.get("is_admin", False),
    )
```
