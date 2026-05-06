// scripts/setup_demo.js
// ============================================================
//  Deploy toàn bộ contract + phân bổ token + lưu địa chỉ ra file
//  Chạy: npx hardhat run scripts/setup_demo.js --network ganache
//        npx hardhat run scripts/setup_demo.js --network hardhat
// ============================================================
const { ethers, network } = require("hardhat");
const fs = require("fs");
const path = require("path");

// ─── Cấu hình cổ đông demo ────────────────────────────────────────────────────
const SHAREHOLDER_CONFIG = [
  // [0] Chủ tịch HĐQT — Sáng lập (45%) — đã giữ từ constructor
  { name: "Chủ tịch HĐQT",       hst: 4_500_000n, tier: 3 },
  // [1] Quỹ phát triển — Chiến lược (25%)
  { name: "Quỹ phát triển",       hst: 2_500_000n, tier: 2 },
  // [2] Cổ đông A — Tổ chức (15%)
  { name: "Cổ đông A (Tổ chức)",  hst: 1_500_000n, tier: 1 },
  // [3] Cổ đông B — Tổ chức (10%)
  { name: "Cổ đông B (Tổ chức)",  hst: 1_000_000n, tier: 1 },
  // [4] Cổ đông C — Nhỏ lẻ (5%)
  { name: "Cổ đông C (Nhỏ lẻ)",   hst:   500_000n, tier: 0 },
  // [5] Ví không hợp lệ — 0 token (để test reject)
  { name: "Ví không hợp lệ",      hst:         0n, tier: 0 },
];

// ─── Helper ───────────────────────────────────────────────────────────────────
const toWei = (n) => ethers.parseUnits(n.toString(), 18);
const fmt   = (n) => Number(n).toLocaleString("vi-VN");

function log(msg) { console.log(`  ${msg}`); }
function section(title) {
  console.log(`\n${"─".repeat(60)}`);
  console.log(`  ${title}`);
  console.log("─".repeat(60));
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const accounts = await ethers.getSigners();
  section(`🚀 Deploying on network: ${network.name}`);
  log(`Deployer: ${accounts[0].address}`);
  log(`Block:    ${await ethers.provider.getBlockNumber()}`);

  // ── 1. Deploy HSTToken ──────────────────────────────────────────────────────
  section("1️⃣  Deploy HSTToken");
  const HSTToken = await ethers.getContractFactory("HSTToken");
  const hst = await HSTToken.deploy(accounts[0].address);
  await hst.waitForDeployment();
  const hstAddress = await hst.getAddress();
  log(`✅ HSTToken deployed: ${hstAddress}`);
  log(`   Total supply: ${fmt(Number(ethers.formatUnits(await hst.totalSupply(), 18)))} HST`);

  // ── 2. Deploy ShareholderRegistry ──────────────────────────────────────────
  section("2️⃣  Deploy ShareholderRegistry");
  const Registry = await ethers.getContractFactory("ShareholderRegistry");
  const registry = await Registry.deploy(hstAddress, accounts[0].address);
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();
  log(`✅ ShareholderRegistry deployed: ${registryAddress}`);

  // Chuyển ownership HSTToken sang Registry để Registry có thể mint
  await hst.transferOwnership(registryAddress);
  log(`   HSTToken ownership → Registry ✅`);

  // ── 3. Deploy GovernanceContract ───────────────────────────────────────────
  section("3️⃣  Deploy GovernanceContract");
  const Governance = await ethers.getContractFactory("GovernanceContract");
  const gov = await Governance.deploy(hstAddress, registryAddress, accounts[0].address);
  await gov.waitForDeployment();
  const govAddress = await gov.getAddress();
  log(`✅ GovernanceContract deployed: ${govAddress}`);

  // Cấp CAMPAIGN_MANAGER_ROLE cho accounts[0]
  const CAMPAIGN_MANAGER_ROLE = await gov.CAMPAIGN_MANAGER_ROLE();
  await gov.grantRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address);
  log(`   CAMPAIGN_MANAGER_ROLE → accounts[0] ✅`);

  // ── 4. Deploy TimelockController ───────────────────────────────────────────
  section("4️⃣  Deploy HSTTimelockController");
  const Timelock = await ethers.getContractFactory("HSTTimelockController");
  const timelock = await Timelock.deploy(
    [govAddress],           // proposers: chỉ Governance được queue
    [ethers.ZeroAddress],   // executors: address(0) = bất kỳ ai có thể execute
    accounts[0].address     // admin ban đầu
  );
  await timelock.waitForDeployment();
  const timelockAddress = await timelock.getAddress();
  log(`✅ TimelockController deployed: ${timelockAddress}`);

  // ── 5. Đăng ký cổ đông + phân bổ token ────────────────────────────────────
  section("5️⃣  Phân bổ token cho cổ đông");

  // accounts[0] đã giữ toàn bộ supply từ constructor
  // Cần transfer cho accounts[1..4], accounts[5] giữ 0
  const REGISTRY_ADMIN_ROLE = await registry.REGISTRY_ADMIN_ROLE();

  for (let i = 0; i < SHAREHOLDER_CONFIG.length; i++) {
    const cfg = SHAREHOLDER_CONFIG[i];
    if (i >= accounts.length) {
      log(`⚠️  Bỏ qua ${cfg.name} — không đủ accounts`);
      continue;
    }

    const acc = accounts[i];
    if (cfg.hst === 0n) {
      log(`⏭️  ${cfg.name} (accounts[${i}]) — 0 HST, bỏ qua đăng ký`);
      continue;
    }

    // Transfer token từ accounts[0] sang accounts[i] (trừ accounts[0] đã có)
    if (i > 0) {
      // Trước tiên registry cần được cấp quyền mint hoặc owner transfer
      // Ở đây dùng transfer trực tiếp từ accounts[0] (owner ban đầu)
      // vì registry.addShareholder sẽ mint — nhưng ownership đã chuyển về registry
      // → Dùng registry.addShareholder() cho tất cả accounts[1..4]
    }

    // Tạo identity hash giả (demo)
    const identityHash = ethers.keccak256(
      ethers.toUtf8Bytes(`DEMO_CCCD_${i}_${acc.address}`)
    );

    try {
      if (i === 0) {
        // accounts[0] đã có token từ constructor, chỉ cần đăng ký vào registry
        // Tạm thời chuyển ownership lại để addShareholder hoạt động với accounts[0]
        // accounts[0] bypass: đăng ký thủ công bằng cách gọi registry
        log(`ℹ️  accounts[0] (${cfg.name}) - token từ constructor, skip addShareholder`);
      } else {
        await registry.connect(accounts[0]).addShareholder(
          acc.address,
          identityHash,
          toWei(cfg.hst),
          cfg.tier
        );
        log(`✅ Registered: ${cfg.name} (accounts[${i}]) — ${fmt(Number(cfg.hst))} HST, Tier ${cfg.tier}`);
      }
    } catch (err) {
      log(`❌ Failed ${cfg.name}: ${err.message}`);
    }
  }

  // ── 6. Delegation — Mỗi cổ đông tự delegate cho mình ─────────────────────
  section("6️⃣  Self-delegation (activate voting power)");
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    if (SHAREHOLDER_CONFIG[i].hst === 0n) continue;
    try {
      await hst.connect(accounts[i]).delegate(accounts[i].address);
      const vp = await hst.getVotes(accounts[i].address);
      log(`✅ accounts[${i}] delegated → voting power: ${fmt(Number(ethers.formatUnits(vp, 18)))} HST`);
    } catch (err) {
      log(`⚠️  accounts[${i}] delegate failed: ${err.message}`);
    }
  }

  // ── 7. Lưu địa chỉ contract ra file ───────────────────────────────────────
  section("7️⃣  Lưu contract addresses");
  const addresses = {
    network:          network.name,
    deployedAt:       new Date().toISOString(),
    deployBlock:      await ethers.provider.getBlockNumber(),
    hstToken:         hstAddress,
    registry:         registryAddress,
    governance:       govAddress,
    timelock:         timelockAddress,
    shareholders:     SHAREHOLDER_CONFIG.slice(0, accounts.length).map((cfg, i) => ({
      index:   i,
      name:    cfg.name,
      address: accounts[i]?.address ?? "N/A",
      hst:     cfg.hst.toString(),
      tier:    cfg.tier,
    })),
  };

  const outDir = path.join(__dirname, "..", "dashboard");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(
    path.join(outDir, "contract_addresses.json"),
    JSON.stringify(addresses, null, 2)
  );
  log(`✅ Saved → dashboard/contract_addresses.json`);

  // ── 8. Summary ─────────────────────────────────────────────────────────────
  section("📊 Deployment Summary");
  console.log(`
  ┌─────────────────────────────────────────────────────────┐
  │  HSTToken         ${hstAddress}  │
  │  Registry         ${registryAddress}  │
  │  Governance       ${govAddress}  │
  │  Timelock         ${timelockAddress}  │
  └─────────────────────────────────────────────────────────┘

  ✅ Setup hoàn tất! Chạy dashboard:
     $env:PYTHONUTF8=1
     streamlit run dashboard/app.py --server.fileWatcherType none
  `);
}

main().catch((err) => {
  console.error("❌ Deploy failed:", err);
  process.exit(1);
});
