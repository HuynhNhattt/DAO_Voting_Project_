// scripts/add_campaigns.js
// ============================================================
//  Thêm 4 chiến dịch MỚI để test vote trực tiếp trên dashboard
//  Không bỏ phiếu sẵn — để người dùng tự vote qua dashboard
//
//  Chạy: npx hardhat run scripts/add_campaigns.js --network ganache
// ============================================================
const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

function log(msg)   { console.log(`  ${msg}`); }
function ok(msg)    { console.log(`  ✅ ${msg}`); }
function warn(msg)  { console.log(`  ⚠️  ${msg}`); }
function section(t) { console.log(`\n${"─".repeat(60)}\n  ${t}\n${"─".repeat(60)}`); }

// ─── 4 chiến dịch mới — để TRỐNG votes, tự vote qua dashboard ────────────────
// ProposalType:    0=ROUTINE  1=MAJOR  2=MA
// VotingMechanism: 0=LINEAR   1=QUADRATIC  2=EQUAL
const NEW_CAMPAIGNS = [
  {
    title:        "Phê duyệt kế hoạch mở rộng văn phòng Q3-2025",
    description:  "Mở thêm chi nhánh tại TP.HCM và Đà Nẵng với tổng ngân sách 5 tỷ VNĐ. " +
                  "Bao gồm thuê mặt bằng, trang thiết bị và tuyển dụng 20 nhân sự mới.",
    proposalType: 0,   // ROUTINE
    mechanism:    0,   // LINEAR
    commitReveal: false,
    label: "ID-201 · Routine · Linear · ACTIVE — tự vote",
  },
  {
    title:        "Tăng vốn điều lệ thêm 20% — Phát hành cổ phiếu mới",
    description:  "Đề xuất tăng vốn điều lệ từ 100 tỷ lên 120 tỷ VNĐ thông qua phát hành " +
                  "thêm 20 triệu cổ phiếu phổ thông mệnh giá 1.000đ/cp cho cổ đông hiện hữu.",
    proposalType: 1,   // MAJOR
    mechanism:    0,   // LINEAR
    commitReveal: false,
    label: "ID-202 · Major · Linear · ACTIVE — tự vote",
  },
  {
    title:        "Bầu Trưởng ban Kiểm soát nhiệm kỳ 2025-2027",
    description:  "Bầu chọn Trưởng ban Kiểm soát nhiệm kỳ 2025-2027 bằng cơ chế Equal " +
                  "(1 cổ đông = 1 phiếu) nhằm đảm bảo công bằng giữa cổ đông lớn và nhỏ.",
    proposalType: 1,   // MAJOR
    mechanism:    2,   // EQUAL
    commitReveal: false,
    label: "ID-203 · Major · Equal · ACTIVE — tự vote",
  },
  {
    title:        "Hợp tác chiến lược với VietTech Group — Commit-Reveal",
    description:  "Ký kết hợp đồng hợp tác chiến lược 3 năm với VietTech Group, " +
                  "trị giá 80 tỷ VNĐ. Sử dụng Commit-Reveal để bảo mật phiếu bầu.",
    proposalType: 2,   // MA
    mechanism:    0,   // LINEAR
    commitReveal: true,
    label: "ID-204 · M&A · Linear · Commit-Reveal — tự commit",
  },
];

async function main() {
  const accounts = await ethers.getSigners();
  section(`🗳️  Thêm chiến dịch mới trên ${network.name}`);
  log(`Người tạo: ${accounts[0].address}`);

  // ── 1. Đọc địa chỉ contract ──────────────────────────────────────────────────
  const addrFile = path.join(__dirname, "..", "dashboard", "contract_addresses.json");
  if (!fs.existsSync(addrFile)) {
    console.error("❌ Không tìm thấy dashboard/contract_addresses.json");
    console.error("   Chạy trước: npx hardhat run scripts/setup_demo.js --network ganache");
    process.exit(1);
  }
  const addrs = JSON.parse(fs.readFileSync(addrFile, "utf8"));
  log(`GovernanceContract: ${addrs.governance}`);

  // ── 2. Attach contracts ──────────────────────────────────────────────────────
  const gov = await ethers.getContractAt("GovernanceContract", addrs.governance);
  const hst = await ethers.getContractAt("HSTToken",           addrs.hstToken);

  // ── 3. Đảm bảo accounts[0] có CAMPAIGN_MANAGER_ROLE ────────────────────────
  section("🔑 Kiểm tra quyền");
  const CAMPAIGN_MANAGER_ROLE = await gov.CAMPAIGN_MANAGER_ROLE();
  const hasRole = await gov.hasRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address);
  if (!hasRole) {
    await gov.grantRole(CAMPAIGN_MANAGER_ROLE, accounts[0].address);
    ok("Đã cấp CAMPAIGN_MANAGER_ROLE cho accounts[0]");
  } else {
    ok("accounts[0] đã có CAMPAIGN_MANAGER_ROLE");
  }

  // ── 4. Đảm bảo tất cả cổ đông đã self-delegate ──────────────────────────────
  section("⚡ Kiểm tra self-delegation");
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    try {
      const bal = await hst.balanceOf(accounts[i].address);
      if (bal === 0n) { log(`accounts[${i}] — 0 token, bỏ qua`); continue; }
      const vp = await hst.getVotes(accounts[i].address);
      if (vp === 0n) {
        await hst.connect(accounts[i]).delegate(accounts[i].address);
        ok(`accounts[${i}] self-delegated → ${ethers.formatUnits(bal, 18)} VP`);
      } else {
        ok(`accounts[${i}] VP: ${ethers.formatUnits(vp, 18)}`);
      }
    } catch (e) {
      warn(`accounts[${i}]: ${e.message.slice(0, 60)}`);
    }
  }

  // ── 5. Tạo chiến dịch (không vote sẵn) ──────────────────────────────────────
  section("🗳️  Tạo 4 chiến dịch mới");
  const created = [];
  const counterBefore = Number(await gov.campaignCounter());
  log(`Campaign counter hiện tại: ${counterBefore}`);

  for (let ci = 0; ci < NEW_CAMPAIGNS.length; ci++) {
    const cfg = NEW_CAMPAIGNS[ci];
    log(`\n  [${ci + 1}/4] ${cfg.label}`);

    // Mine block để snapshot hợp lệ
    await ethers.provider.send("evm_mine", []);

    try {
      const tx = await gov.connect(accounts[0]).createCampaign(
        cfg.title,
        cfg.description,
        cfg.proposalType,
        cfg.mechanism,
        cfg.commitReveal,
      );
      const receipt = await tx.wait();

      // Parse campaignId từ event
      const iface = gov.interface;
      let foundId = null;
      for (const l of receipt.logs) {
        try {
          const parsed = iface.parseLog(l);
          if (parsed && parsed.name === "CampaignCreated") {
            foundId = parsed.args[0]; break;
          }
        } catch (_) {}
      }
      const campaignId = foundId ?? (await gov.campaignCounter());
      ok(`Campaign #${campaignId} tạo thành công: "${cfg.title}"`);
      created.push({ id: Number(campaignId), ...cfg });
    } catch (e) {
      warn(`Tạo thất bại: ${e.message.slice(0, 100)}`);
    }

    await ethers.provider.send("evm_mine", []);
  }

  // ── 6. In tóm tắt ────────────────────────────────────────────────────────────
  section("📊 Kết quả");
  const statusLabels = ["DRAFT","ACTIVE","COMMIT","REVEAL","TALLYING","EXECUTED","DEFEATED","CANCELLED"];
  const mechLabels   = ["Linear","Quadratic","Equal"];
  const typeLabels   = ["Routine","Major","M&A"];

  for (const c of created) {
    try {
      const raw = await gov.getCampaign(c.id);
      const status = statusLabels[Number(raw[6])] ?? "?";
      const type_  = typeLabels[Number(raw[4])]  ?? "?";
      const mech   = mechLabels[Number(raw[5])]  ?? "?";
      console.log(`  #${c.id} [${status.padEnd(8)}] [${type_.padEnd(7)}] [${mech.padEnd(9)}] CR=${raw[14]}`);
      console.log(`       "${raw[1]}"`);
      console.log(`       votingDeadline: ${new Date(Number(raw[10]) * 1000).toLocaleString("vi-VN")}`);
    } catch (e) {
      warn(`getCampaign(${c.id}) failed: ${e.message}`);
    }
  }

  // ── 7. Cập nhật contract_addresses.json ─────────────────────────────────────
  section("💾 Cập nhật contract_addresses.json");
  try {
    const existingCampaigns = addrs.campaigns || [];
    const newEntries = created.map(c => ({
      id:           c.id,
      title:        c.title,
      proposalType: c.proposalType,
      mechanism:    c.mechanism,
      commitReveal: c.commitReveal,
      label:        c.label,
    }));
    const updated = {
      ...addrs,
      campaigns: [...existingCampaigns, ...newEntries],
      campaignsSetupAt: new Date().toISOString(),
    };
    fs.writeFileSync(addrFile, JSON.stringify(updated, null, 2));
    ok(`Đã thêm ${created.length} campaign vào dashboard/contract_addresses.json`);
  } catch (e) {
    warn(`Không ghi được file: ${e.message}`);
  }

  console.log(`
  ┌──────────────────────────────────────────────────────────┐
  │  ✅ Thêm ${created.length} chiến dịch hoàn tất!                         │
  │                                                          │
  │  Các chiến dịch ĐỀU ở trạng thái ACTIVE — vào dashboard │
  │  để tự bỏ phiếu:                                         │
  │                                                          │
  │  ID-201: Routine  · Linear       → bỏ phiếu thường      │
  │  ID-202: Major    · Linear       → bỏ phiếu thường      │
  │  ID-203: Major    · Equal        → 1 người = 1 phiếu    │
  │  ID-204: M&A      · Commit-Reveal→ bỏ phiếu kín         │
  │                                                          │
  │  Chạy Dashboard:                                         │
  │    $env:PYTHONUTF8=1                                     │
  │    streamlit run dashboard/app.py                        │
  └──────────────────────────────────────────────────────────┘
  `);
}

main().catch(e => {
  console.error("❌ add_campaigns failed:", e);
  process.exit(1);
});