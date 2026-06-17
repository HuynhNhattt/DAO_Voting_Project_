// scripts/setup_campaign.js
// ============================================================
//  Tạo 4 chiến dịch demo + bỏ phiếu sẵn + finalize + tạo biên bản
//  Nhận xét thầy #2: Chứng minh quy trình nghiệp vụ thực tế
//  Nhận xét thầy #3: Tạo biên bản chữ ký số sau finalize
//
//  Chạy: npx hardhat run scripts/setup_campaign.js --network ganache
// ============================================================
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

function log(msg)   { console.log(`  ${msg}`); }
function ok(msg)    { console.log(`  ✅ ${msg}`); }
function warn(msg)  { console.log(`  ⚠️  ${msg}`); }
function section(t) { console.log(`\n${"─".repeat(60)}\n  ${t}\n${"─".repeat(60)}`); }
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ─── 4 chiến dịch demo ────────────────────────────────────────
// Nhận xét thầy #2: mỗi campaign là 1 kịch bản nghiệp vụ thực tế
const CAMPAIGNS = [
  {
    // ── Kịch bản 1: Quyết định thường lệ ──────────────────────
    // Thực tế: họp HĐQT thường niên phê duyệt ngân sách R&D
    // Cơ chế: LINEAR — quyền lực theo % cổ phần (phù hợp tài chính)
    title:        "Phê duyệt ngân sách R&D 2025",
    description:  "Phân bổ 2 tỷ VNĐ cho nghiên cứu và phát triển Q1-Q2 2025.",
    proposalType: 0,   // ROUTINE
    mechanism:    0,   // LINEAR
    commitReveal: false,
    votes: [
      { signerIdx: 0, option: 0 },  // Chủ tịch (45%): FOR
      { signerIdx: 1, option: 0 },  // Quỹ PT   (25%): FOR
      { signerIdx: 2, option: 1 },  // CĐ A     (15%): AGAINST
      { signerIdx: 3, option: 0 },  // CĐ B     (10%): FOR
      { signerIdx: 4, option: 2 },  // CĐ C      (5%): ABSTAIN
    ],
    shouldFinalize: true,
    label: "ID-101 · Routine · Linear · KQ: ✅ PASS",
  },
  {
    // ── Kịch bản 2: Quyết định quan trọng ─────────────────────
    // Thực tế: ĐHCĐ thường niên biểu quyết chia cổ tức
    // Cơ chế: LINEAR — tỷ lệ cổ phần quyết định (cổ đông lớn chịu rủi ro nhiều hơn)
    title:        "Chia cổ tức 15% năm 2024",
    description:  "Đề xuất chia cổ tức 15% trên mệnh giá cho toàn bộ cổ đông từ lợi nhuận 2024.",
    proposalType: 1,   // MAJOR
    mechanism:    0,   // LINEAR
    commitReveal: false,
    votes: [
      { signerIdx: 0, option: 0 },  // Chủ tịch: FOR
      { signerIdx: 1, option: 0 },  // Quỹ PT:   FOR
      { signerIdx: 2, option: 0 },  // CĐ A:     FOR
      { signerIdx: 3, option: 1 },  // CĐ B:     AGAINST
      { signerIdx: 4, option: 0 },  // CĐ C:     FOR
    ],
    shouldFinalize: true,
    label: "ID-102 · Major · Linear · KQ: ✅ PASS",
  },
  {
    // ── Kịch bản 3: So sánh Linear vs Quadratic ───────────────
    // Thực tế: Bầu CEO — cổ đông nhỏ phản đối ứng viên của cổ đông lớn
    // Linear → Chủ tịch thắng; Quadratic → cổ đông nhỏ bảo vệ được
    // Minh chứng: Quadratic bảo vệ tiếng nói thiểu số
    title:        "Bầu CEO mới — So sánh Linear vs Quadratic",
    description:  "Bầu CEO nhiệm kỳ 2025-2028. Minh hoạ khác biệt giữa Linear và Quadratic.",
    proposalType: 1,   // MAJOR
    mechanism:    1,   // QUADRATIC ← điểm khác biệt
    commitReveal: false,
    votes: [
      // sqrt(4.5M)≈2121 FOR, vs sqrt(2.5M)+sqrt(1.5M)+sqrt(1M)≈3805 AGAINST
      { signerIdx: 0, option: 0 },  // Chủ tịch: FOR  (weight≈2121)
      { signerIdx: 1, option: 1 },  // Quỹ PT:   AGAINST (weight≈1581)
      { signerIdx: 2, option: 1 },  // CĐ A:     AGAINST (weight≈1224)
      { signerIdx: 3, option: 1 },  // CĐ B:     AGAINST (weight≈1000)
      { signerIdx: 4, option: 0 },  // CĐ C:     FOR  (weight≈707)
    ],
    shouldFinalize: true,
    label: "ID-103 · Major · Quadratic · KQ: ❌ KHÔNG ĐẠT (Quadratic bảo vệ thiểu số)",
  },
  {
    // ── Kịch bản 4: M&A với bỏ phiếu kín ─────────────────────
    // Thực tế: Thương vụ M&A nhạy cảm — dùng Commit-Reveal để
    // tránh ảnh hưởng lẫn nhau khi biết phiếu của nhau trước
    title:        "Sáp nhập M&A — TechCorp Ltd",
    description:  "Thương vụ M&A 150 tỷ VNĐ. Dùng Commit-Reveal để bảo mật phiếu bầu.",
    proposalType: 2,   // MA
    mechanism:    0,   // LINEAR
    commitReveal: true,
    votes: [],         // Giữ ở COMMIT phase — demo Commit-Reveal UI
    shouldFinalize: false,
    label: "ID-104 · M&A · Linear · Commit-Reveal (đang ở COMMIT)",
  },
];

// ─── Main ─────────────────────────────────────────────────────
async function main() {
  const accounts = await ethers.getSigners();
  section(`🗳️  Setup Campaigns — ${network.name}`);
  log(`Campaign Manager: ${accounts[0].address}`);

  // ── 1. Load contracts ──────────────────────────────────────
  const addrFile = path.join(__dirname, "..", "dashboard", "contract_addresses.json");
  if (!fs.existsSync(addrFile)) {
    console.error("❌ Không tìm thấy contract_addresses.json — chạy setup_demo.js trước");
    process.exit(1);
  }
  const addrs = JSON.parse(fs.readFileSync(addrFile, "utf8"));

  const gov      = await ethers.getContractAt("GovernanceContract",   addrs.governance);
  const hst      = await ethers.getContractAt("HSTToken",             addrs.hstToken);
  const registry = await ethers.getContractAt("ShareholderRegistry",  addrs.registry);

  // VotingCertificate (nếu đã deploy)
  let votingCert = null;
  if (addrs.votingCertificate) {
    votingCert = await ethers.getContractAt("VotingCertificate", addrs.votingCertificate);
    ok(`VotingCertificate loaded: ${addrs.votingCertificate}`);
  }

  // ── 2. Kiểm tra quyền ─────────────────────────────────────
  section("🔑 Kiểm tra quyền Campaign Manager");
  const CAMPAIGN_MANAGER_ROLE = await gov.CAMPAIGN_MANAGER_ROLE();
  if (!await gov.hasRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address)) {
    await gov.grantRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address);
    ok("Đã cấp CAMPAIGN_MANAGER_ROLE");
  } else {
    ok("accounts[0] đã có CAMPAIGN_MANAGER_ROLE");
  }

  // ── 3. Self-delegation ─────────────────────────────────────
  section("⚡ Self-delegation");
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    try {
      const bal = await hst.balanceOf(accounts[i].address);
      if (bal === 0n) continue;
      const vp = await hst.getVotes(accounts[i].address);
      if (vp === 0n) {
        await hst.connect(accounts[i]).delegate(accounts[i].address);
        ok(`accounts[${i}] self-delegated`);
      } else {
        ok(`accounts[${i}] VP: ${ethers.formatUnits(vp, 18)}`);
      }
    } catch (e) { warn(`accounts[${i}]: ${e.message.slice(0, 60)}`); }
  }

  // ── 4. Tạo campaigns + vote + finalize ─────────────────────
  section("🗳️  Tạo campaigns — Quy trình nghiệp vụ đầy đủ");
  const created = [];

  for (let ci = 0; ci < CAMPAIGNS.length; ci++) {
    const cfg = CAMPAIGNS[ci];
    log(`\n  [${ci + 1}/${CAMPAIGNS.length}] ${cfg.label}`);

    await ethers.provider.send("evm_mine", []);

    // ── Bước 1: createCampaign ─────────────────────────────
    // Ánh xạ nghiệp vụ: "Ban tổ chức phát hành tờ phiếu"
    let campaignId;
    try {
      const tx      = await gov.connect(accounts[0]).createCampaign(
        cfg.title, cfg.description,
        cfg.proposalType, cfg.mechanism, cfg.commitReveal
      );
      const receipt = await tx.wait();
      const iface   = gov.interface;
      let foundId   = null;
      for (const l of receipt.logs) {
        try {
          const parsed = iface.parseLog(l);
          if (parsed?.name === "CampaignCreated") { foundId = parsed.args[0]; break; }
        } catch (_) {}
      }
      campaignId = foundId ?? (await gov.campaignCounter());
      ok(`Campaign #${campaignId} tạo thành công`);
      created.push({ id: Number(campaignId), ...cfg });
    } catch (e) {
      warn(`Tạo thất bại: ${e.message.slice(0, 100)}`);
      continue;
    }

    await ethers.provider.send("evm_mine", []);

    // ── Bước 2: castVote ────────────────────────────────────
    // Ánh xạ nghiệp vụ: "Cổ đông bỏ phiếu vào hòm phiếu"
    if (!cfg.commitReveal && cfg.votes.length > 0) {
      const optLabels = ["FOR", "AGAINST", "ABSTAIN"];
      for (const v of cfg.votes) {
        if (v.signerIdx >= accounts.length) continue;
        const voter = accounts[v.signerIdx];
        try {
          const canVote = await registry.canVote(voter.address);
          const vp      = await hst.getVotes(voter.address);
          if (!canVote || vp === 0n) { warn(`accounts[${v.signerIdx}] không thể vote`); continue; }
          if (await gov.hasVoted(campaignId, voter.address)) continue;
          await gov.connect(voter).castVote(campaignId, v.option);
          ok(`accounts[${v.signerIdx}] → ${optLabels[v.option]}`);
        } catch (e) { warn(`accounts[${v.signerIdx}] vote failed: ${e.message.slice(0, 60)}`); }
        await sleep(50);
      }
    } else if (cfg.commitReveal) {
      log(`  ℹ️  Commit-Reveal — giữ trạng thái COMMIT để demo`);
    }

    // ── Bước 3: Finalize + tạo biên bản ────────────────────
    // Ánh xạ nghiệp vụ: "Ban kiểm phiếu đếm và công bố kết quả,
    //                     Thư ký ký biên bản"
    if (cfg.shouldFinalize && !cfg.commitReveal) {
      log(`  ⏩ Fast-forward time để finalize...`);
      try {
        // Tua thời gian vượt votingDeadline
        await ethers.provider.send("evm_increaseTime", [8 * 24 * 3600]);
        await ethers.provider.send("evm_mine", []);

        await gov.connect(accounts[0]).finalizeCampaign(campaignId);
        const camp = await gov.getCampaign(campaignId);
        const statusLabels = ["DRAFT","ACTIVE","COMMIT","REVEAL","TALLYING","EXECUTED","DEFEATED","CANCELLED","QUEUED","EXECUTABLE"];
        const st = statusLabels[Number(camp.statusInt ?? camp[6])] ?? "?";
        ok(`Finalized → ${st}`);

        // Kiểm tra biên bản đã được tạo tự động chưa
        if (votingCert) {
          const hasCert = await votingCert.hasCertificate(campaignId);
          if (hasCert) {
            const cert = await votingCert.getCertificate(campaignId);
            ok(`Biên bản tạo tự động ✅ Hash: ${cert.certificateHash.slice(0, 20)}...`);
          } else {
            warn(`Biên bản chưa được tạo — kiểm tra CERTIFIER_ROLE`);
          }
        }
      } catch (e) {
        warn(`Finalize failed: ${e.message.slice(0, 80)}`);
      }
    }
  }

  // ── 5. Tổng kết ────────────────────────────────────────────
  section("📊 Kết quả");
  const STATUS_L = ["DRAFT","ACTIVE","COMMIT","REVEAL","TALLYING","EXECUTED","DEFEATED","CANCELLED","QUEUED","EXECUTABLE"];
  const TYPE_L   = ["Routine","Major","M&A"];
  const MECH_L   = ["Linear","Quadratic","Equal"];

  for (let id = 1; id <= Number(await gov.campaignCounter()); id++) {
    try {
      const c      = await gov.getCampaign(id);
      const status = STATUS_L[Number(c[6])] ?? "?";
      const type_  = TYPE_L[Number(c[4])]  ?? "?";
      const mech   = MECH_L[Number(c[5])]  ?? "?";
      const forV   = Number(ethers.formatUnits(c[15], 18)).toLocaleString("vi-VN");
      const agV    = Number(ethers.formatUnits(c[16], 18)).toLocaleString("vi-VN");

      // Kiểm tra biên bản
      let certInfo = "";
      if (votingCert) {
        const hasCert = await votingCert.hasCertificate(id).catch(() => false);
        certInfo = hasCert ? " 📄 Biên bản: ✅" : " 📄 Biên bản: -";
      }

      console.log(`  #${id} [${status.padEnd(9)}] [${type_.padEnd(7)}] [${mech.padEnd(9)}] FOR=${forV} | AGAINST=${agV}${certInfo}`);
      console.log(`       "${c[1]}"`);
    } catch (e) { warn(`getCampaign(${id}) failed`); }
  }

  // ── 6. Cập nhật contract_addresses.json ────────────────────
  section("💾 Cập nhật contract_addresses.json");
  try {
    const updated = {
      ...addrs,
      campaigns: created.map(c => ({
        id: c.id, title: c.title,
        proposalType: c.proposalType,
        mechanism: c.mechanism,
        commitReveal: c.commitReveal,
        label: c.label,
      })),
      campaignsSetupAt: new Date().toISOString(),
    };
    fs.writeFileSync(addrFile, JSON.stringify(updated, null, 2));
    ok(`Đã ghi ${created.length} campaign`);
  } catch (e) { warn(`Không ghi được: ${e.message}`); }

  console.log(`
  ┌──────────────────────────────────────────────────────────┐
  │  ✅ Setup campaign hoàn tất!                              │
  │                                                          │
  │  Điểm mới (theo nhận xét thầy):                          │
  │  #1 Vai trò token: getTokenInfo() trên dashboard         │
  │  #2 Quy trình: createCampaign→castVote→finalize đủ       │
  │  #3 Biên bản: VotingCertificate tự động tạo sau finalize │
  │  #4 On/Off chain: xem on_off_chain_explainer.py          │
  │                                                          │
  │  Chạy Dashboard:                                         │
  │    streamlit run dashboard/app.py                        │
  └──────────────────────────────────────────────────────────┘
  `);
}

main().catch(e => { console.error("❌", e); process.exit(1); });
