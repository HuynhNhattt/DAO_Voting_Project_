// scripts/deploy_amoy.js
// ══════════════════════════════════════════════════════════════
// Deploy toàn bộ hệ thống lên Polygon Amoy Testnet
//
// Khác với setup_demo.js (Ganache):
//   - Không dùng evm_mine / evm_increaseTime (testnet thật)
//   - Lưu địa chỉ riêng vào contract_addresses_amoy.json
//   - In link Polygonscan để xem contract trên explorer
//   - Có bước verify contract (tuỳ chọn)
//
// Chuẩn bị:
//   1. cp .env.example .env  → điền DEPLOYER_PRIVATE_KEY
//   2. Lấy MATIC test: https://faucet.polygon.technology
//   3. npx hardhat run scripts/deploy_amoy.js --network amoy
// ══════════════════════════════════════════════════════════════
const { ethers, network, run } = require("hardhat");
const fs   = require("fs");
const path = require("path");

const EXPLORER = "https://amoy.polygonscan.com";

function log(msg)   { console.log(`  ${msg}`); }
function ok(msg)    { console.log(`  ✅ ${msg}`); }
function warn(msg)  { console.log(`  ⚠️  ${msg}`); }
function link(addr) { return `${EXPLORER}/address/${addr}`; }
function section(t) { console.log(`\n${"═".repeat(60)}\n  ${t}\n${"═".repeat(60)}`); }

// Cổ đông demo — điều chỉnh địa chỉ ví thật ở đây
// Với Amoy testnet, mỗi địa chỉ cần có MATIC test để vote
const SHAREHOLDERS = [
  { name: "Chủ tịch HĐQT",      hst: 4_500_000n, tier: 3 },
  { name: "Quỹ phát triển",      hst: 2_500_000n, tier: 2 },
  { name: "Cổ đông A (Tổ chức)", hst: 1_500_000n, tier: 1 },
  { name: "Cổ đông B (Tổ chức)", hst: 1_000_000n, tier: 1 },
  { name: "Cổ đông C (Nhỏ lẻ)",  hst:   500_000n, tier: 0 },
];

const toWei  = n => ethers.parseUnits(n.toString(), 18);
const fmt    = n => Number(n).toLocaleString("vi-VN");
const sleep  = ms => new Promise(r => setTimeout(r, ms));

// Chờ một số block để đảm bảo tx được confirm
async function waitBlocks(provider, n = 2) {
  const start = await provider.getBlockNumber();
  while (true) {
    await sleep(3000);
    const current = await provider.getBlockNumber();
    if (current >= start + n) break;
  }
}

async function main() {
  const accounts = await ethers.getSigners();
  const deployer = accounts[0];

  section(`🚀 Deploy lên ${network.name.toUpperCase()}`);
  log(`Deployer  : ${deployer.address}`);
  log(`Explorer  : ${link(deployer.address)}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  log(`MATIC dư  : ${ethers.formatEther(balance)} MATIC`);

  if (balance < ethers.parseEther("0.1")) {
    console.error("\n❌ Số dư MATIC không đủ!");
    console.error("   Lấy MATIC test tại: https://faucet.polygon.technology");
    console.error("   Cần ít nhất 0.1 MATIC để deploy");
    process.exit(1);
  }

  log(`Block     : ${await ethers.provider.getBlockNumber()}`);

  // ── 1. Deploy HSTToken ──────────────────────────────────────
  section("1️⃣  Deploy HSTToken");
  const HSTToken = await ethers.getContractFactory("HSTToken");
  log("Đang deploy... (chờ xác nhận blockchain)");
  const hst = await HSTToken.deploy(deployer.address);
  await hst.waitForDeployment();
  const hstAddress = await hst.getAddress();
  ok(`HSTToken: ${hstAddress}`);
  log(`   🔗 ${link(hstAddress)}`);
  await waitBlocks(ethers.provider);

  // ── 2. Deploy ShareholderRegistry ──────────────────────────
  section("2️⃣  Deploy ShareholderRegistry");
  const Registry = await ethers.getContractFactory("ShareholderRegistry");
  const registry = await Registry.deploy(hstAddress, deployer.address);
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();
  ok(`ShareholderRegistry: ${registryAddress}`);
  log(`   🔗 ${link(registryAddress)}`);
  await waitBlocks(ethers.provider);

  // Burn + transfer ownership
  const initialSupply = await hst.totalSupply();
  const burnTx = await hst.burn(deployer.address, initialSupply);
  await burnTx.wait();
  ok(`Burned ${fmt(Number(ethers.formatUnits(initialSupply, 18)))} HST`);

  const ownTx = await hst.transferOwnership(registryAddress);
  await ownTx.wait();
  ok("HSTToken ownership → Registry");
  await waitBlocks(ethers.provider);

  // ── 3. Deploy GovernanceContract ───────────────────────────
  section("3️⃣  Deploy GovernanceContract");
  const Governance = await ethers.getContractFactory("GovernanceContract");
  const gov = await Governance.deploy(hstAddress, registryAddress, deployer.address);
  await gov.waitForDeployment();
  const govAddress = await gov.getAddress();
  ok(`GovernanceContract: ${govAddress}`);
  log(`   🔗 ${link(govAddress)}`);

  const CAMPAIGN_MANAGER_ROLE = await gov.CAMPAIGN_MANAGER_ROLE();
  const grantTx = await gov.grantRole(CAMPAIGN_MANAGER_ROLE, deployer.address);
  await grantTx.wait();
  ok("CAMPAIGN_MANAGER_ROLE → deployer");
  await waitBlocks(ethers.provider);

  // ── 4. Deploy TimelockController ───────────────────────────
  section("4️⃣  Deploy HSTTimelockController");
  const Timelock = await ethers.getContractFactory("HSTTimelockController");
  const timelock = await Timelock.deploy(
    [govAddress], [ethers.ZeroAddress], deployer.address
  );
  await timelock.waitForDeployment();
  const timelockAddress = await timelock.getAddress();
  ok(`Timelock: ${timelockAddress}`);
  log(`   🔗 ${link(timelockAddress)}`);
  await waitBlocks(ethers.provider);

  // ── 5. Deploy VotingCertificate ────────────────────────────
  section("5️⃣  Deploy VotingCertificate");
  const VotingCertificate = await ethers.getContractFactory("VotingCertificate");
  const votingCert = await VotingCertificate.deploy(deployer.address);
  await votingCert.waitForDeployment();
  const votingCertAddress = await votingCert.getAddress();
  ok(`VotingCertificate: ${votingCertAddress}`);
  log(`   🔗 ${link(votingCertAddress)}`);

  // Cấp CERTIFIER_ROLE cho Governance
  const CERTIFIER_ROLE = await votingCert.CERTIFIER_ROLE();
  const certGrantTx = await votingCert.grantRole(CERTIFIER_ROLE, govAddress);
  await certGrantTx.wait();
  ok("CERTIFIER_ROLE → GovernanceContract");
  await waitBlocks(ethers.provider);

  // ── 6. Link VotingCertificate vào Governance ───────────────
  section("6️⃣  Tích hợp VotingCertificate");
  const linkTx = await gov.setCertificateContract(votingCertAddress);
  await linkTx.wait();
  ok("GovernanceContract ↔ VotingCertificate linked");
  await waitBlocks(ethers.provider);

  // ── 7. Đăng ký cổ đông ─────────────────────────────────────
  section("7️⃣  Đăng ký cổ đông");
  for (let i = 0; i < SHAREHOLDERS.length; i++) {
    const cfg = SHAREHOLDERS[i];
    if (i >= accounts.length) {
      warn(`${cfg.name} — không đủ accounts trong .env, bỏ qua`);
      continue;
    }
    const acc          = accounts[i];
    const identityHash = ethers.keccak256(
      ethers.toUtf8Bytes(`AMOY_DEMO_${i}_${acc.address}`)
    );
    try {
      const tx = await registry.connect(deployer).addShareholder(
        acc.address, identityHash, toWei(cfg.hst), cfg.tier
      );
      await tx.wait();
      ok(`${cfg.name}: ${acc.address.slice(0, 10)}... — ${fmt(Number(cfg.hst))} HST`);
      log(`   🔗 ${link(acc.address)}`);
      await sleep(1000); // tránh nonce conflict
    } catch (e) {
      warn(`${cfg.name} failed: ${e.message.slice(0, 80)}`);
    }
  }

  // ── 8. Self-delegate ────────────────────────────────────────
  section("8️⃣  Self-delegation");
  for (let i = 0; i < Math.min(SHAREHOLDERS.length, accounts.length); i++) {
    if (SHAREHOLDERS[i].hst === 0n) continue;
    try {
      const tx = await hst.connect(accounts[i]).delegate(accounts[i].address);
      await tx.wait();
      const vp = await hst.getVotes(accounts[i].address);
      ok(`accounts[${i}] → ${fmt(Number(ethers.formatUnits(vp, 18)))} VP`);
      await sleep(1000);
    } catch (e) {
      warn(`accounts[${i}] delegate failed: ${e.message.slice(0, 60)}`);
    }
  }

  // ── 9. Lưu địa chỉ ─────────────────────────────────────────
  section("9️⃣  Lưu địa chỉ contract");
  const addresses = {
    network:           network.name,
    chainId:           80002,
    explorer:          EXPLORER,
    deployedAt:        new Date().toISOString(),
    deployBlock:       await ethers.provider.getBlockNumber(),
    deployer:          deployer.address,
    hstToken:          hstAddress,
    registry:          registryAddress,
    governance:        govAddress,
    timelock:          timelockAddress,
    votingCertificate: votingCertAddress,
    links: {
      hstToken:          `${link(hstAddress)}`,
      registry:          `${link(registryAddress)}`,
      governance:        `${link(govAddress)}`,
      timelock:          `${link(timelockAddress)}`,
      votingCertificate: `${link(votingCertAddress)}`,
    },
    shareholders: SHAREHOLDERS
      .slice(0, Math.min(SHAREHOLDERS.length, accounts.length))
      .map((cfg, i) => ({
        index:   i,
        name:    cfg.name,
        address: accounts[i]?.address ?? "N/A",
        hst:     cfg.hst.toString(),
        tier:    cfg.tier,
        explorerLink: link(accounts[i]?.address ?? ""),
      })),
  };

  const outDir = path.join(__dirname, "..", "dashboard");
  fs.mkdirSync(outDir, { recursive: true });

  // Lưu riêng file amoy để không ghi đè Ganache
  const amoyFile = path.join(outDir, "contract_addresses_amoy.json");
  fs.writeFileSync(amoyFile, JSON.stringify(addresses, null, 2));
  ok(`Saved → dashboard/contract_addresses_amoy.json`);

  // Ghi đè file chính nếu muốn Dashboard dùng Amoy
  // (bỏ comment dòng dưới nếu muốn switch sang Amoy)
  // fs.writeFileSync(path.join(outDir, "contract_addresses.json"), JSON.stringify(addresses, null, 2));

  // ── 10. Summary ─────────────────────────────────────────────
  section("📊 DEPLOYMENT SUMMARY — POLYGON AMOY TESTNET");
  console.log(`
  ┌───────────────────────────────────────────────────────────────┐
  │              ✅ DEPLOY THÀNH CÔNG TRÊN AMOY TESTNET           │
  ├───────────────────────────────────────────────────────────────┤
  │  HSTToken          : ${hstAddress}  │
  │  ShareholderRegistry: ${registryAddress}  │
  │  GovernanceContract: ${govAddress}  │
  │  TimelockController: ${timelockAddress}  │
  │  VotingCertificate : ${votingCertAddress}  │
  ├───────────────────────────────────────────────────────────────┤
  │  🔗 Xem trên Polygonscan:                                     │
  │  ${EXPLORER}                        │
  ├───────────────────────────────────────────────────────────────┤
  │  Bước tiếp theo:                                              │
  │  1. Verify contract (tuỳ chọn):                               │
  │     npx hardhat verify --network amoy <address> <args>        │
  │  2. Chạy Dashboard với Amoy RPC:                              │
  │     AMOY_MODE=true streamlit run dashboard/app.py             │
  │  3. Thêm Amoy vào MetaMask:                                   │
  │     RPC: https://rpc-amoy.polygon.technology                  │
  │     ChainID: 80002, Symbol: MATIC                             │
  └───────────────────────────────────────────────────────────────┘
  `);
}

main().catch(e => {
  console.error("❌ Deploy Amoy failed:", e.message);
  process.exit(1);
});
