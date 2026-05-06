// scripts/setup_campaign.js
// ============================================================
//  Tạo 4 chiến dịch demo trên blockchain sau khi đã deploy
//  Yêu cầu: setup_demo.js đã chạy xong (có contract_addresses.json)
//
//  Chạy: npx hardhat run scripts/setup_campaign.js --network ganache
// ============================================================
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

// ─── Helper ───────────────────────────────────────────────────────────────────
function log(msg)     { console.log(`  ${msg}`); }
function ok(msg)      { console.log(`  ✅ ${msg}`); }
function warn(msg)    { console.log(`  ⚠️  ${msg}`); }
function section(t)   { console.log(`\n${"─".repeat(60)}\n  ${t}\n${"─".repeat(60)}`); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ─── Config 4 chiến dịch demo ─────────────────────────────────────────────────
// ProposalType:    0=ROUTINE  1=MAJOR  2=MA
// VotingMechanism: 0=LINEAR   1=QUADRATIC  2=EQUAL
// useCommitReveal: true/false
const CAMPAIGNS = [
  {
    title:          "Phê duyệt ngân sách R&D 2025",
    description:    "Phân bổ 2 tỷ VNĐ cho nghiên cứu và phát triển sản phẩm mới Q1-Q2 2025. " +
                    "Khoản đầu tư tập trung vào AI và tự động hóa quy trình sản xuất.",
    proposalType:   0,   // ROUTINE
    mechanism:      0,   // LINEAR
    commitReveal:   false,
    // Sau khi tạo: accounts[0..3] bỏ phiếu để kịch bản Pass
    votes: [
      { signerIdx: 0, option: 0 },  // Chủ tịch: FOR
      { signerIdx: 1, option: 0 },  // Quỹ PT:   FOR
      { signerIdx: 2, option: 1 },  // CĐ A:     AGAINST
      { signerIdx: 3, option: 0 },  // CĐ B:     FOR
      { signerIdx: 4, option: 2 },  // CĐ C:     ABSTAIN
    ],
    label: "ID-101 · Routine · Linear · KQ: ✅ PASS",
  },
  {
    title:          "Chia cổ tức 15% năm 2024",
    description:    "Đề xuất chia cổ tức 15% trên mệnh giá cổ phần cho toàn bộ cổ đông hiện hữu " +
                    "từ lợi nhuận năm tài chính 2024. Ngày chốt danh sách: 31/01/2025.",
    proposalType:   1,   // MAJOR
    mechanism:      0,   // LINEAR
    commitReveal:   false,
    votes: [
      { signerIdx: 0, option: 0 },  // Chủ tịch: FOR
      { signerIdx: 1, option: 0 },  // Quỹ PT:   FOR
      { signerIdx: 2, option: 0 },  // CĐ A:     FOR
      { signerIdx: 3, option: 1 },  // CĐ B:     AGAINST
      { signerIdx: 4, option: 0 },  // CĐ C:     FOR
    ],
    label: "ID-102 · Major · Linear · KQ: ✅ PASS",
  },
  {
    title:          "Bầu CEO mới — So sánh Linear vs Quadratic",
    description:    "Bầu chọn CEO nhiệm kỳ 2025-2028. Ứng viên: Nguyễn Văn A (nội bộ) vs " +
                    "Trần Thị B (bên ngoài). Kịch bản minh hoạ sự khác biệt giữa Linear và Quadratic.",
    proposalType:   1,   // MAJOR
    mechanism:      1,   // QUADRATIC
    commitReveal:   false,
    // Chủ tịch + CĐ C: FOR; Quỹ PT + CĐ A + CĐ B: AGAINST
    // Linear → Chủ tịch thắng; Quadratic → cổ đông nhỏ có ưu thế hơn
    votes: [
      { signerIdx: 0, option: 0 },  // Chủ tịch: FOR  (sqrt 4.5M ≈ 2121)
      { signerIdx: 1, option: 1 },  // Quỹ PT:   AGAINST (sqrt 2.5M ≈ 1581)
      { signerIdx: 2, option: 1 },  // CĐ A:     AGAINST (sqrt 1.5M ≈ 1224)
      { signerIdx: 3, option: 1 },  // CĐ B:     AGAINST (sqrt 1.0M = 1000)
      { signerIdx: 4, option: 0 },  // CĐ C:     FOR     (sqrt 0.5M ≈ 707)
    ],
    label: "ID-103 · Major · Quadratic · KQ: ❌ KHÔNG ĐẠT (Quadratic bảo vệ thiểu số)",
  },
  {
    title:          "Sáp nhập M&A — TechCorp Ltd",
    description:    "Thương vụ M&A chiến lược với TechCorp Ltd, định giá 150 tỷ VNĐ. " +
                    "Sử dụng Commit-Reveal để đảm bảo bỏ phiếu kín, tránh gây ảnh hưởng lẫn nhau.",
    proposalType:   2,   // MA
    mechanism:      0,   // LINEAR
    commitReveal:   true,
    votes: [],           // Commit-Reveal: không cast vote trực tiếp — giữ ở trạng thái COMMIT
    label: "ID-104 · M&A · Linear · Commit-Reveal (đang ở giai đoạn COMMIT)",
  },
];

// ─── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const accounts = await ethers.getSigners();
  section(`🗳️  Setup Campaigns trên ${network.name}`);
  log(`Deployer / Campaign Manager: ${accounts[0].address}`);

  // ── 1. Đọc địa chỉ contract đã deploy ────────────────────────────────────
  const addrFile = path.join(__dirname, "..", "dashboard", "contract_addresses.json");
  if (!fs.existsSync(addrFile)) {
    console.error("❌ Không tìm thấy dashboard/contract_addresses.json");
    console.error("   Chạy trước: npx hardhat run scripts/setup_demo.js --network ganache");
    process.exit(1);
  }
  const addrs = JSON.parse(fs.readFileSync(addrFile, "utf8"));
  log(`HSTToken:    ${addrs.hstToken}`);
  log(`Registry:    ${addrs.registry}`);
  log(`Governance:  ${addrs.governance}`);

  // ── 2. Attach contracts ────────────────────────────────────────────────────
  const gov      = await ethers.getContractAt("GovernanceContract",   addrs.governance);
  const hst      = await ethers.getContractAt("HSTToken",             addrs.hstToken);
  const registry = await ethers.getContractAt("ShareholderRegistry",  addrs.registry);

  // ── 3. Xác nhận CAMPAIGN_MANAGER_ROLE ─────────────────────────────────────
  section("🔑 Kiểm tra quyền Campaign Manager");
  const CAMPAIGN_MANAGER_ROLE = await gov.CAMPAIGN_MANAGER_ROLE();
  const hasRole = await gov.hasRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address);
  if (!hasRole) {
    log("Cấp CAMPAIGN_MANAGER_ROLE cho accounts[0]...");
    await gov.grantRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address);
    ok("Đã cấp CAMPAIGN_MANAGER_ROLE");
  } else {
    ok("accounts[0] đã có CAMPAIGN_MANAGER_ROLE");
  }

  // ── 4. Đảm bảo cổ đông đã self-delegate ────────────────────────────────────
  section("⚡ Self-delegation (đảm bảo voting power)");
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    try {
      const bal = await hst.balanceOf(accounts[i].address);
      if (bal === 0n) {
        log(`accounts[${i}] — 0 token, bỏ qua`);
        continue;
      }
      const vp = await hst.getVotes(accounts[i].address);
      if (vp === 0n) {
        await hst.connect(accounts[i]).delegate(accounts[i].address);
        ok(`accounts[${i}] self-delegated → ${ethers.formatUnits(bal, 18)} VP`);
      } else {
        ok(`accounts[${i}] đã có VP: ${ethers.formatUnits(vp, 18)}`);
      }
    } catch (e) {
      warn(`accounts[${i}] delegate failed: ${e.message}`);
    }
  }

  // ── 5. Kiểm tra registry.canVote cho từng cổ đông ─────────────────────────
  section("📋 Kiểm tra canVote cho cổ đông");
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    try {
      const can = await registry.canVote(accounts[i].address);
      log(`accounts[${i}] canVote: ${can ? "✅ YES" : "❌ NO"}`);
    } catch (e) {
      warn(`accounts[${i}] canVote error: ${e.message}`);
    }
  }

  // ── 6. Tạo campaigns + bỏ phiếu ──────────────────────────────────────────
  section("🗳️  Tạo 4 chiến dịch demo");
  const createdCampaigns = [];

  for (let ci = 0; ci < CAMPAIGNS.length; ci++) {
    const cfg = CAMPAIGNS[ci];
    log(`\n  [${ci + 1}/4] ${cfg.label}`);

    // Mine 1 block để snapshot voting power hợp lệ
    await ethers.provider.send("evm_mine", []);

    let campaignId;
    try {
      const tx = await gov.connect(accounts[0]).createCampaign(
        cfg.title,
        cfg.description,
        cfg.proposalType,
        cfg.mechanism,
        cfg.commitReveal,
      );
      const receipt = await tx.wait();

      // Parse campaignId từ event CampaignCreated
      const iface = gov.interface;
      let foundId = null;
      for (const log_ of receipt.logs) {
        try {
          const parsed = iface.parseLog(log_);
          if (parsed && parsed.name === "CampaignCreated") {
            foundId = parsed.args[0];
            break;
          }
        } catch (_) {}
      }
      campaignId = foundId ?? (await gov.campaignCounter());
      ok(`Tạo campaign #${campaignId}: "${cfg.title}"`);
      createdCampaigns.push({ id: Number(campaignId), ...cfg });
    } catch (e) {
      warn(`Tạo campaign thất bại: ${e.message}`);
      continue;
    }

    // Mine 1 block sau khi tạo để snapshot hợp lệ cho getPastVotes
    await ethers.provider.send("evm_mine", []);

    // Bỏ phiếu (nếu không phải Commit-Reveal)
    if (!cfg.commitReveal && cfg.votes.length > 0) {
      log(`  Đang cast votes...`);
      const optionLabel = ["FOR", "AGAINST", "ABSTAIN"];
      for (const v of cfg.votes) {
        if (v.signerIdx >= accounts.length) continue;
        const voter = accounts[v.signerIdx];
        try {
          // Kiểm tra canVote và voting power
          const canVote = await registry.canVote(voter.address);
          const vp = await hst.getVotes(voter.address);
          if (!canVote || vp === 0n) {
            warn(`accounts[${v.signerIdx}] không thể vote (canVote=${canVote}, vp=${vp})`);
            continue;
          }

          const alreadyVoted = await gov.hasVoted(campaignId, voter.address);
          if (alreadyVoted) {
            log(`  accounts[${v.signerIdx}] đã vote rồi, bỏ qua`);
            continue;
          }

          await gov.connect(voter).castVote(campaignId, v.option);
          ok(`accounts[${v.signerIdx}] → ${optionLabel[v.option]}`);
        } catch (e) {
          warn(`accounts[${v.signerIdx}] vote failed: ${e.message.slice(0, 80)}`);
        }
        // Nhỏ delay để tránh nonce conflict
        await sleep(50);
      }
    } else if (cfg.commitReveal) {
      log(`  ℹ️  Commit-Reveal campaign — giữ trạng thái COMMIT`);
    }
  }

  // ── 7. Lấy kết quả & in tóm tắt ──────────────────────────────────────────
  section("📊 Kết quả cuối cùng");
  const counter = Number(await gov.campaignCounter());
  const statusLabels = ["DRAFT","ACTIVE","COMMIT","REVEAL","TALLYING","EXECUTED","DEFEATED","CANCELLED"];
  const mechLabels   = ["Linear","Quadratic","Equal"];
  const typeLabels   = ["Routine","Major","M&A"];

  for (let id = 1; id <= counter; id++) {
    try {
      const c = await gov.getCampaign(id);
      const forV  = Number(ethers.formatUnits(c[15], 18)).toLocaleString("vi-VN");
      const agV   = Number(ethers.formatUnits(c[16], 18)).toLocaleString("vi-VN");
      const absV  = Number(ethers.formatUnits(c[17], 18)).toLocaleString("vi-VN");
      const status = statusLabels[Number(c[6])] ?? "?";
      const type_  = typeLabels[Number(c[4])] ?? "?";
      const mech   = mechLabels[Number(c[5])] ?? "?";

      console.log(`  #${id} [${status.padEnd(9)}] [${type_.padEnd(7)}] [${mech.padEnd(9)}] FOR=${forV} | AGAINST=${agV} | ABS=${absV}`);
      console.log(`       "${c[1]}"`);
    } catch (e) {
      warn(`getCampaign(${id}) failed: ${e.message}`);
    }
  }

  // ── 8. Cập nhật contract_addresses.json với thông tin campaign ────────────
  section("💾 Cập nhật contract_addresses.json");
  try {
    const updated = {
      ...addrs,
      campaigns: createdCampaigns.map((c) => ({
        id:           c.id,
        title:        c.title,
        proposalType: c.proposalType,
        mechanism:    c.mechanism,
        commitReveal: c.commitReveal,
        label:        c.label,
      })),
      campaignsSetupAt: new Date().toISOString(),
    };
    fs.writeFileSync(addrFile, JSON.stringify(updated, null, 2));
    ok(`Đã ghi ${createdCampaigns.length} campaign vào dashboard/contract_addresses.json`);
  } catch (e) {
    warn(`Không ghi được file: ${e.message}`);
  }

  console.log(`
  ┌──────────────────────────────────────────────────────────┐
  │  ✅ Setup campaign hoàn tất!                              │
  │                                                          │
  │  Chạy Dashboard:                                         │
  │    $env:PYTHONUTF8=1                                     │
  │    streamlit run dashboard/app.py                        │
  └──────────────────────────────────────────────────────────┘
  `);
}

main().catch((e) => {
  console.error("❌ setup_campaign failed:", e);
  process.exit(1);
});