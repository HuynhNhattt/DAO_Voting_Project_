// scripts/add_new_campaigns.js
// Tạo thêm 3 campaign mới chưa có ai vote để tự bỏ phiếu trên dashboard
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

const ok   = msg => console.log(`  ✅ ${msg}`);
const warn = msg => console.log(`  ⚠️  ${msg}`);

const NEW_CAMPAIGNS = [
  {
    title:        "Phe duyet ngan sach marketing Q3-2025",
    description:  "Phan bo 1.5 ty VND cho chien dich marketing so va quang cao thuong hieu nam 2025.",
    proposalType: 0,   // ROUTINE
    mechanism:    0,   // LINEAR
    commitReveal: false,
  },
  {
    title:        "Bau Truong ban Kiem soat nhiem ky 2025-2027",
    description:  "Bau chon Truong ban Kiem soat bang co che Equal (1 co dong = 1 phieu).",
    proposalType: 1,   // MAJOR
    mechanism:    2,   // EQUAL
    commitReveal: false,
  },
  {
    title:        "Tang von dieu le them 10% - Phat hanh co phieu moi",
    description:  "De xuat tang von dieu le tu 100 ty len 110 ty VND phat hanh them 10 trieu co phieu.",
    proposalType: 1,   // MAJOR
    mechanism:    1,   // QUADRATIC
    commitReveal: false,
  },
];

async function main() {
  const accounts = await ethers.getSigners();
  console.log(`\nThem campaign moi de tu vote — ${network.name}`);

  const addrFile = path.join(__dirname, "..", "dashboard", "contract_addresses.json");
  const addrs    = JSON.parse(fs.readFileSync(addrFile, "utf8"));
  const gov      = await ethers.getContractAt("GovernanceContract", addrs.governance);
  const hst      = await ethers.getContractAt("HSTToken",           addrs.hstToken);

  // Đảm bảo có CAMPAIGN_MANAGER_ROLE
  const ROLE = await gov.CAMPAIGN_MANAGER_ROLE();
  if (!await gov.hasRole(ROLE, accounts[0].address)) {
    await gov.grantRole(ROLE, accounts[0].address);
  }

  // Đảm bảo đã delegate
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    const bal = await hst.balanceOf(accounts[i].address);
    if (bal > 0n && (await hst.getVotes(accounts[i].address)) === 0n) {
      await hst.connect(accounts[i]).delegate(accounts[i].address);
    }
  }

  const created = [];
  for (const cfg of NEW_CAMPAIGNS) {
    await ethers.provider.send("evm_mine", []);
    try {
      const tx      = await gov.connect(accounts[0]).createCampaign(
        cfg.title, cfg.description, cfg.proposalType, cfg.mechanism, cfg.commitReveal
      );
      const receipt = await tx.wait();
      let id = null;
      for (const l of receipt.logs) {
        try {
          const p = gov.interface.parseLog(l);
          if (p?.name === "CampaignCreated") { id = Number(p.args[0]); break; }
        } catch(_) {}
      }
      id = id ?? Number(await gov.campaignCounter());
      ok(`Campaign #${id}: "${cfg.title}"`);
      created.push({ id, ...cfg });
    } catch(e) {
      warn(`That bai: ${e.message.slice(0,80)}`);
    }
    await ethers.provider.send("evm_mine", []);
  }

  // Cập nhật contract_addresses.json
  const existing = addrs.campaigns || [];
  addrs.campaigns = [
    ...existing,
    ...created.map(c => ({
      id: c.id, title: c.title,
      proposalType: c.proposalType,
      mechanism: c.mechanism,
      commitReveal: c.commitReveal,
      label: `#${c.id} - ACTIVE - tu vote`,
    }))
  ];
  fs.writeFileSync(addrFile, JSON.stringify(addrs, null, 2));

  console.log(`\n  Da tao ${created.length} campaign moi!`);
  console.log(`  Vao Dashboard tab "Bo phieu" de tu vote.`);
}

main().catch(e => { console.error("Failed:", e); process.exit(1); });