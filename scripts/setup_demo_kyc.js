// scripts/setup_demo_kyc.js
// ══════════════════════════════════════════════════════════════
// Deploy thêm IdentityVerifier và gắn vào ShareholderRegistry
// Chạy SAU setup_demo.js (đọc contract_addresses.json đã có)
//
// Chạy: npx hardhat run scripts/setup_demo_kyc.js --network ganache
// ══════════════════════════════════════════════════════════════
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

const ok      = msg => console.log(`  ✅ ${msg}`);
const warn    = msg => console.log(`  ⚠️  ${msg}`);
const section = t   => console.log(`\n${"═".repeat(60)}\n  ${t}\n${"═".repeat(60)}`);

async function main() {
  const accounts = await ethers.getSigners();
  const deployer = accounts[0];

  section(`Deploy IdentityVerifier — ${network.name}`);
  console.log(`  Deployer: ${deployer.address}`);

  // ── Đọc địa chỉ đã deploy ──────────────────────────────────
  const addrFile = path.join(__dirname, "..", "dashboard", "contract_addresses.json");
  if (!fs.existsSync(addrFile)) {
    console.error("❌ Chạy setup_demo.js trước!");
    process.exit(1);
  }
  const addrs = JSON.parse(fs.readFileSync(addrFile, "utf8"));

  // ── Deploy IdentityVerifier ─────────────────────────────────
  section("Deploy IdentityVerifier");
  //
  // KYC Signer = accounts[0] trong demo
  // Trong production: dùng địa chỉ ví riêng của KYC team
  //
  const kycSigner = deployer.address;
  const IdVerifier = await ethers.getContractFactory("IdentityVerifier");
  const idVerifier = await IdVerifier.deploy(deployer.address, kycSigner);
  await idVerifier.waitForDeployment();
  const idVerifierAddress = await idVerifier.getAddress();
  ok(`IdentityVerifier: ${idVerifierAddress}`);
  ok(`KYC Signer: ${kycSigner}`);

  // ── Gắn vào ShareholderRegistry ────────────────────────────
  section("Link IdentityVerifier → ShareholderRegistry");
  const registry = await ethers.getContractAt("ShareholderRegistry", addrs.registry);
  await registry.setIdentityVerifier(idVerifierAddress);
  ok("registry.setIdentityVerifier() done");

  // Chưa bật requireKYC — để backward-compatible với demo cũ
  // Khi sẵn sàng production: registry.setRequireKYC(true)
  ok("requireKYC = false (backward-compatible)");
  ok("Để bật KYC bắt buộc: registry.setRequireKYC(true)");

  // ── Demo: Tạo KYC proof cho cổ đông demo ───────────────────
  section("Demo KYC — Tạo proof cho cổ đông #0 (Chủ tịch HĐQT)");
  //
  // Trong production: người dùng tự submit qua Dashboard
  // Ở đây demo bằng cách Admin tạo và submit luôn
  //
  const { ethers: et } = require("hardhat");

  // Tạo identity hash (giả lập thông tin Chủ tịch HĐQT)
  const fullName    = "NGUYEN VAN AN";
  const nationalId  = "012345678901";
  const dob         = "1975-05-15";
  const country     = "VN";
  const rawIdentity = `${fullName}|${nationalId}|${dob}|${country}`;
  const identityHash = et.keccak256(et.toUtf8Bytes(rawIdentity));

  const timestamp = Math.floor(Date.now() / 1000);
  const rawKyc    = `${identityHash}|2|${timestamp}|demo`;
  const kycHash   = et.keccak256(et.toUtf8Bytes(rawKyc));

  // Nonce ngẫu nhiên
  const nonce     = et.randomBytes(32);

  // Tạo message hash giống _buildKYCMessage() trong Solidity
  const chainId   = network.config.chainId ?? 1337;
  const msgBytes  = et.concat([
    et.toUtf8Bytes("KYC_VERIFY"),
    identityHash,
    kycHash,
    new Uint8Array([2]),           // KYCLevel.STANDARD = 2
    nonce,
    et.zeroPadValue(accounts[0].address, 32),
    et.zeroPadValue(et.toBeHex(chainId), 32),
  ]);
  const msgHash = et.keccak256(msgBytes);

  // KYC Signer ký (trong demo = accounts[0])
  const signerWallet = new et.Wallet(
    process.env.GANACHE_PRIVATE_KEYS?.split(",")[0]?.trim() ?? ""
  );

  let signature;
  try {
    // Ký bằng ethers signMessage (thêm prefix \x19Ethereum Signed Message)
    signature = await signerWallet.signMessage(et.getBytes(msgHash));
    ok(`KYC Signer signed: ${signerWallet.address}`);
  } catch (e) {
    warn(`Không ký được (thiếu private key trong .env): ${e.message.slice(0, 60)}`);
    warn("Bỏ qua bước submit KYC demo — sẽ tự submit qua Dashboard");
    signature = null;
  }

  if (signature) {
    try {
      await idVerifier.connect(accounts[0]).submitKYC(
        identityHash,
        kycHash,
        2,        // STANDARD
        nonce,
        country,
        signature
      );
      ok(`KYC submitted cho accounts[0] (${accounts[0].address})`);
    } catch (e) {
      warn(`submitKYC demo failed: ${e.message.slice(0, 80)}`);
    }
  }

  // ── Lưu địa chỉ ────────────────────────────────────────────
  section("Cập nhật contract_addresses.json");
  const updated = { ...addrs, identityVerifier: idVerifierAddress, kycSigner };
  fs.writeFileSync(addrFile, JSON.stringify(updated, null, 2));
  ok("Saved → dashboard/contract_addresses.json");

  section("📊 Summary");
  console.log(`
  ┌────────────────────────────────────────────────────────────┐
  │  IdentityVerifier : ${idVerifierAddress}  │
  │  KYC Signer       : ${kycSigner}  │
  ├────────────────────────────────────────────────────────────┤
  │  Thêm cổ đông có KYC thật:                                 │
  │    registry.addShareholderWithKYC(wallet, tokens, tier, 2) │
  │                                                            │
  │  Bật KYC bắt buộc (production):                            │
  │    registry.setRequireKYC(true)                            │
  │                                                            │
  │  Dashboard KYC: tab "🪪 KYC" trong app.py                 │
  └────────────────────────────────────────────────────────────┘
  `);
}

main().catch(e => { console.error("❌", e); process.exit(1); });
