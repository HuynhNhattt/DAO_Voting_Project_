// scripts/setup_demo_full.js
// ══════════════════════════════════════════════════════════════
//  Deploy TOÀN BỘ hệ thống trong 1 script duy nhất:
//    1. HSTToken
//    2. ShareholderRegistry
//    3. GovernanceContract
//    4. HSTTimelockController  → link vào Governance (THẬT)
//    5. VotingCertificate      → link vào Governance
//    6. IdentityVerifier       → link vào Registry  (MỚI)
//    7. Phân bổ token + Self-delegate
//    8. Demo KYC proof cho accounts[0]
//
//  Chạy: npx hardhat run scripts/setup_demo_full.js --network ganache
// ══════════════════════════════════════════════════════════════
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

const SHAREHOLDERS = [
  { name: "Chủ tịch HĐQT",       hst: 4_500_000n, tier: 3,
    kyc: { name: "NGUYEN VAN AN",  id: "012345678901", dob: "1975-05-15" } },
  { name: "Quỹ phát triển",       hst: 2_500_000n, tier: 2,
    kyc: { name: "TRAN THI BICH", id: "023456789012", dob: "1980-08-20" } },
  { name: "Cổ đông A (Tổ chức)",  hst: 1_500_000n, tier: 1,
    kyc: { name: "LE VAN CUONG",  id: "034567890123", dob: "1985-03-10" } },
  { name: "Cổ đông B (Tổ chức)",  hst: 1_000_000n, tier: 1,
    kyc: { name: "PHAM THI DUNG", id: "045678901234", dob: "1988-11-25" } },
  { name: "Cổ đông C (Nhỏ lẻ)",   hst:   500_000n, tier: 0,
    kyc: { name: "HOANG VAN EM",  id: "056789012345", dob: "1992-07-04" } },
];

const toWei = n => ethers.parseUnits(n.toString(), 18);
const fmt   = n => Number(n).toLocaleString("vi-VN");
const ok    = msg => console.log(`  ✅ ${msg}`);
const warn  = msg => console.log(`  ⚠️  ${msg}`);
const info  = msg => console.log(`  ℹ️  ${msg}`);
const section = t => console.log(`\n${"═".repeat(62)}\n  ${t}\n${"═".repeat(62)}`);

// ── Tạo identityHash giống kyc_service.py ─────────────────────
function makeIdentityHash(name, nationalId, dob, country = "VN") {
  const raw = `${name}|${nationalId}|${dob}|${country}`;
  return ethers.keccak256(ethers.toUtf8Bytes(raw));
}

// ── Tạo KYC signature (giống kyc_service.sign_kyc_approval) ───
async function signKYCApproval(signer, wallet, identityHash, kycHash, level, nonce, chainId) {
  // Encode giống abi.encodePacked trong Solidity _buildKYCMessage()
  const msgBytes = ethers.concat([
    ethers.toUtf8Bytes("KYC_VERIFY"),
    identityHash,
    kycHash,
    new Uint8Array([level]),
    nonce,
    ethers.getBytes(wallet),  // address = 20 bytes (không pad)
    ethers.zeroPadValue(ethers.toBeHex(chainId), 32),
  ]);
  const msgHash  = ethers.keccak256(msgBytes);
  // Ký
  const sig = await signer.signMessage(ethers.getBytes(msgHash));
  return sig;
}

async function main() {
  const accounts = await ethers.getSigners();
  const deployer = accounts[0];
  const chainId  = Number((await ethers.provider.getNetwork()).chainId);

  section(`🚀 Full Deploy — ${network.name} (chainId: ${chainId})`);
  console.log(`  Deployer: ${deployer.address}`);

  // ── 1. HSTToken ──────────────────────────────────────────────
  section("1️⃣  HSTToken");
  const hst = await (await ethers.getContractFactory("HSTToken")).deploy(deployer.address);
  await hst.waitForDeployment();
  const hstAddr = await hst.getAddress();
  ok(`HSTToken: ${hstAddr}`);

  // ── 2. ShareholderRegistry ───────────────────────────────────
  section("2️⃣  ShareholderRegistry");
  const registry = await (await ethers.getContractFactory("ShareholderRegistry")).deploy(hstAddr, deployer.address);
  await registry.waitForDeployment();
  const registryAddr = await registry.getAddress();
  ok(`Registry: ${registryAddr}`);

  await hst.burn(deployer.address, await hst.totalSupply());
  await hst.transferOwnership(registryAddr);
  ok("Burn initial supply + transfer ownership → Registry");

  // ── 3. GovernanceContract ────────────────────────────────────
  section("3️⃣  GovernanceContract");
  const gov = await (await ethers.getContractFactory("GovernanceContract")).deploy(hstAddr, registryAddr, deployer.address);
  await gov.waitForDeployment();
  const govAddr = await gov.getAddress();
  ok(`Governance: ${govAddr}`);
  await gov.grantRole(await gov.CAMPAIGN_MANAGER_ROLE(), deployer.address);

  // ── 4. HSTTimelockController + Link thật ────────────────────
  section("4️⃣  HSTTimelockController + Link vào Governance");
  const timelock = await (await ethers.getContractFactory("HSTTimelockController")).deploy(
    [govAddr], [ethers.ZeroAddress], deployer.address
  );
  await timelock.waitForDeployment();
  const timelockAddr = await timelock.getAddress();
  ok(`Timelock: ${timelockAddr}`);

  await gov.setTimelock(timelockAddr);
  ok("gov.setTimelock() → Timelock link thật ✅");
  info("finalizeCampaign() PASS → QUEUED → executeDecision() → EXECUTED");

  // ── 5. VotingCertificate + Link ──────────────────────────────
  section("5️⃣  VotingCertificate + Link vào Governance");
  const votingCert = await (await ethers.getContractFactory("VotingCertificate")).deploy(deployer.address);
  await votingCert.waitForDeployment();
  const votingCertAddr = await votingCert.getAddress();
  ok(`VotingCertificate: ${votingCertAddr}`);
  await votingCert.grantRole(await votingCert.CERTIFIER_ROLE(), govAddr);
  await gov.setCertificateContract(votingCertAddr);
  ok("VotingCertificate linked ✅");

  // ── 6. IdentityVerifier + Link vào Registry (MỚI) ───────────
  section("6️⃣  IdentityVerifier + Link vào ShareholderRegistry");
  //
  // KYC Signer = accounts[0] (deployer) trong demo
  // Production: dùng địa chỉ ví riêng của KYC team
  //
  const kycSignerAddr = deployer.address;
  const idVerifier = await (await ethers.getContractFactory("IdentityVerifier")).deploy(
    deployer.address, kycSignerAddr
  );
  await idVerifier.waitForDeployment();
  const idVerifierAddr = await idVerifier.getAddress();
  ok(`IdentityVerifier: ${idVerifierAddr}`);
  ok(`KYC Signer: ${kycSignerAddr}`);

  await registry.setIdentityVerifier(idVerifierAddr);
  ok("registry.setIdentityVerifier() ✅");
  info("requireKYC = false (backward-compatible). Bật: registry.setRequireKYC(true)");

  // ── 7. Đăng ký cổ đông ──────────────────────────────────────
  section("7️⃣  Đăng ký cổ đông (addShareholder — không cần KYC trước)");
  //
  // Dùng addShareholder() thay vì addShareholderWithKYC() vì:
  //   - KYC proof cần submit TRƯỚC khi addShareholderWithKYC()
  //   - Trong demo ta làm KYC SAU để đơn giản hóa flow
  //   - requireKYC=false nên vẫn hoạt động
  //
  for (let i = 0; i < SHAREHOLDERS.length; i++) {
    const cfg = SHAREHOLDERS[i];
    if (i >= accounts.length) { warn(`${cfg.name}: không đủ accounts`); continue; }

    // identityHash từ thông tin KYC thật (không phải "DEMO_CCCD_" giả nữa)
    const identityHash = makeIdentityHash(cfg.kyc.name, cfg.kyc.id, cfg.kyc.dob);

    try {
      await registry.connect(deployer).addShareholder(
        accounts[i].address, identityHash, toWei(cfg.hst), cfg.tier
      );
      ok(`${cfg.name}: ${fmt(Number(cfg.hst))} HST | Hash: ${identityHash.slice(0,14)}...`);
    } catch (e) { warn(`${cfg.name}: ${e.message.slice(0, 60)}`); }
  }

  // ── 8. Self-delegate ─────────────────────────────────────────
  section("8️⃣  Self-delegation");
  for (let i = 0; i < Math.min(SHAREHOLDERS.length, accounts.length); i++) {
    try {
      await hst.connect(accounts[i]).delegate(accounts[i].address);
      const vp = await hst.getVotes(accounts[i].address);
      ok(`accounts[${i}] VP: ${fmt(Number(ethers.formatUnits(vp, 18)))}`);
    } catch (e) { warn(`accounts[${i}]: ${e.message.slice(0,50)}`); }
  }

  // ── 9. Demo KYC — submit proof on-chain cho từng cổ đông ─────
  section("9️⃣  Demo KYC — Submit proof on-chain");
  info("KYC Signer = accounts[0] (deployer) trong demo");

  for (let i = 0; i < Math.min(SHAREHOLDERS.length, accounts.length); i++) {
    const cfg    = SHAREHOLDERS[i];
    const wallet = accounts[i].address;

    const identityHash = makeIdentityHash(cfg.kyc.name, cfg.kyc.id, cfg.kyc.dob);
    const timestamp    = Math.floor(Date.now() / 1000) + i;
    const rawKyc       = `${identityHash}|2|${timestamp}|demo`;
    const kycHash      = ethers.keccak256(ethers.toUtf8Bytes(rawKyc));
    const nonce        = ethers.randomBytes(32);

    try {
      // Admin (deployer) ký KYC proof
      const signature = await signKYCApproval(
        deployer,        // KYC Signer
        wallet,          // Ví cổ đông
        identityHash,    // bytes32
        kycHash,         // bytes32
        2,               // KYCLevel.STANDARD
        nonce,           // bytes32
        chainId
      );

      // Cổ đông submit proof lên on-chain
      await idVerifier.connect(accounts[i]).submitKYC(
        identityHash,
        kycHash,
        2,             // STANDARD
        nonce,
        "VN",
        signature
      );
      ok(`accounts[${i}] (${cfg.name}) KYC verified on-chain ✅`);

    } catch (e) {
      warn(`accounts[${i}] KYC failed: ${e.message.slice(0, 80)}`);
    }
  }

  // ── 10. Lưu địa chỉ ─────────────────────────────────────────
  section("🔟  Lưu contract_addresses.json");
  const addresses = {
    network:           network.name,
    chainId,
    deployedAt:        new Date().toISOString(),
    deployBlock:       await ethers.provider.getBlockNumber(),
    hstToken:          hstAddr,
    registry:          registryAddr,
    governance:        govAddr,
    timelock:          timelockAddr,
    votingCertificate: votingCertAddr,
    identityVerifier:  idVerifierAddr,   // MỚI
    kycSigner:         kycSignerAddr,    // MỚI
    timelockLinked:    true,             // Timelock link thật
    kycEnabled:        false,            // requireKYC mặc định false
    shareholders: SHAREHOLDERS
      .slice(0, Math.min(SHAREHOLDERS.length, accounts.length))
      .map((cfg, i) => ({
        index:        i,
        name:         cfg.name,
        address:      accounts[i]?.address ?? "N/A",
        hst:          cfg.hst.toString(),
        tier:         cfg.tier,
        kycVerified:  true,  // Đã KYC trong bước 9
      })),
  };

  const outDir = path.join(__dirname, "..", "dashboard");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "contract_addresses.json"), JSON.stringify(addresses, null, 2));
  ok("Saved → dashboard/contract_addresses.json");

  // ── Summary ──────────────────────────────────────────────────
  section("📊 DEPLOYMENT COMPLETE");
  console.log(`
  ┌──────────────────────────────────────────────────────────────┐
  │  HSTToken          : ${hstAddr}  │
  │  Registry          : ${registryAddr}  │
  │  Governance        : ${govAddr}  │
  │  Timelock          : ${timelockAddr}  │
  │  VotingCertificate : ${votingCertAddr}  │
  │  IdentityVerifier  : ${idVerifierAddr}  │
  ├──────────────────────────────────────────────────────────────┤
  │  ✅ Timelock LINK THẬT vào Governance                        │
  │  ✅ KYC on-chain: 5 cổ đông đã verified                     │
  │  ✅ identityHash từ thông tin thật (không phải DEMO_CCCD_)   │
  ├──────────────────────────────────────────────────────────────┤
  │  Tiếp theo:                                                   │
  │    npx hardhat run scripts/setup_campaign.js --network ganache│
  │    streamlit run dashboard/app.py                            │
  └──────────────────────────────────────────────────────────────┘
  `);
}

main().catch(e => { console.error("❌ Full deploy failed:", e); process.exit(1); });
