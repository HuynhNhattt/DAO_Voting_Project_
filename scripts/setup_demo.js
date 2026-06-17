// scripts/setup_demo.js — Cập nhật: link Timelock thật vào Governance
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

const SHAREHOLDERS = [
  { name: "Chủ tịch HĐQT",      hst: 4_500_000n, tier: 3 },
  { name: "Quỹ phát triển",      hst: 2_500_000n, tier: 2 },
  { name: "Cổ đông A (Tổ chức)", hst: 1_500_000n, tier: 1 },
  { name: "Cổ đông B (Tổ chức)", hst: 1_000_000n, tier: 1 },
  { name: "Cổ đông C (Nhỏ lẻ)",  hst:   500_000n, tier: 0 },
];

const toWei = n => ethers.parseUnits(n.toString(), 18);
const fmt   = n => Number(n).toLocaleString("vi-VN");
const ok    = msg => console.log(`  ✅ ${msg}`);
const warn  = msg => console.log(`  ⚠️  ${msg}`);
const section = t => console.log(`\n${"═".repeat(60)}\n  ${t}\n${"═".repeat(60)}`);

async function main() {
  const accounts = await ethers.getSigners();
  section(`Deploy on ${network.name}`);
  console.log(`  Deployer: ${accounts[0].address}`);

  section("1 Deploy HSTToken");
  const hst = await (await ethers.getContractFactory("HSTToken")).deploy(accounts[0].address);
  await hst.waitForDeployment();
  const hstAddress = await hst.getAddress();
  ok(`HSTToken: ${hstAddress}`);

  section("2 Deploy ShareholderRegistry");
  const registry = await (await ethers.getContractFactory("ShareholderRegistry")).deploy(hstAddress, accounts[0].address);
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();
  ok(`Registry: ${registryAddress}`);
  await hst.burn(accounts[0].address, await hst.totalSupply());
  await hst.transferOwnership(registryAddress);
  ok("Burn + transfer ownership");

  section("3 Deploy GovernanceContract");
  const gov = await (await ethers.getContractFactory("GovernanceContract")).deploy(hstAddress, registryAddress, accounts[0].address);
  await gov.waitForDeployment();
  const govAddress = await gov.getAddress();
  ok(`Governance: ${govAddress}`);
  await gov.grantRole(await gov.CAMPAIGN_MANAGER_ROLE(), accounts[0].address);

  section("4 Deploy HSTTimelockController");
  const timelock = await (await ethers.getContractFactory("HSTTimelockController")).deploy(
    [govAddress], [ethers.ZeroAddress], accounts[0].address
  );
  await timelock.waitForDeployment();
  const timelockAddress = await timelock.getAddress();
  ok(`Timelock: ${timelockAddress}`);

  section("5 Deploy VotingCertificate");
  const votingCert = await (await ethers.getContractFactory("VotingCertificate")).deploy(accounts[0].address);
  await votingCert.waitForDeployment();
  const votingCertAddress = await votingCert.getAddress();
  ok(`VotingCertificate: ${votingCertAddress}`);

  // ══ ĐIỂM MỚI: Link Timelock vào Governance ══════════════════
  section("6 LINK TIMELOCK -> GOVERNANCE (Moi)");
  await gov.setTimelock(timelockAddress);
  ok("gov.setTimelock() da duoc goi");
  ok("finalizeCampaign() gio se QUEUE len Timelock thay vi EXECUTED thang");
  const linked = await gov.timelock();
  ok(`Verify: gov.timelock() = ${linked}`);

  section("7 Link VotingCertificate");
  await votingCert.grantRole(await votingCert.CERTIFIER_ROLE(), govAddress);
  await gov.setCertificateContract(votingCertAddress);
  ok("VotingCertificate linked");

  section("8 Dang ky co dong");
  for (let i = 0; i < SHAREHOLDERS.length; i++) {
    if (i >= accounts.length) continue;
    const cfg = SHAREHOLDERS[i];
    const identityHash = ethers.keccak256(ethers.toUtf8Bytes(`DEMO_${i}_${accounts[i].address}`));
    try {
      await registry.connect(accounts[0]).addShareholder(accounts[i].address, identityHash, toWei(cfg.hst), cfg.tier);
      ok(`${cfg.name}: ${fmt(Number(cfg.hst))} HST`);
    } catch (e) { warn(`${cfg.name}: ${e.message.slice(0, 60)}`); }
  }

  section("9 Self-delegate");
  for (let i = 0; i < Math.min(SHAREHOLDERS.length, accounts.length); i++) {
    try {
      await hst.connect(accounts[i]).delegate(accounts[i].address);
      ok(`accounts[${i}] delegated`);
    } catch (e) { warn(`accounts[${i}]: ${e.message.slice(0, 40)}`); }
  }

  section("10 Luu dia chi");
  const addresses = {
    network: network.name, deployedAt: new Date().toISOString(),
    deployBlock: await ethers.provider.getBlockNumber(),
    hstToken: hstAddress, registry: registryAddress,
    governance: govAddress, timelock: timelockAddress,
    votingCertificate: votingCertAddress,
    timelockLinked: true,
    shareholders: SHAREHOLDERS.slice(0, Math.min(SHAREHOLDERS.length, accounts.length))
      .map((cfg, i) => ({ index: i, name: cfg.name, address: accounts[i]?.address ?? "N/A", hst: cfg.hst.toString(), tier: cfg.tier })),
  };
  const outDir = path.join(__dirname, "..", "dashboard");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "contract_addresses.json"), JSON.stringify(addresses, null, 2));
  ok("Saved contract_addresses.json");

  console.log(`
  TIMELOCK DA DUOC LINK THAT:
    finalizeCampaign() PASS -> QUEUED (cho delay)
    executeDecision()        -> EXECUTED (co hieu luc)
  `);
}
main().catch(e => { console.error("Failed:", e); process.exit(1); });
