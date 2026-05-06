// test/Governance.test.js
const { expect }      = require("chai");
const { ethers }      = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");
const { time }        = require("@nomicfoundation/hardhat-toolbox/network-helpers");

const toWei = (n) => ethers.parseUnits(n.toString(), 18);
const DAYS  = (n) => n * 24 * 60 * 60;

const ProposalType = { ROUTINE: 0, MAJOR: 1, MA: 2 };
const VotingMech   = { LINEAR: 0, QUADRATIC: 1, EQUAL: 2 };
const VoteOption   = { FOR: 0, AGAINST: 1, ABSTAIN: 2 };

// ─── Fixture ──────────────────────────────────────────────────────────────────
async function deployFullSystemFixture() {
  const [owner, quydpt, cdA, cdB, cdC, nobody] = await ethers.getSigners();

  // 1. HSTToken
  const HSTToken = await ethers.getContractFactory("HSTToken");
  const hst = await HSTToken.deploy(owner.address);
  await hst.waitForDeployment();

  // 2. ShareholderRegistry
  const Registry = await ethers.getContractFactory("ShareholderRegistry");
  const registry = await Registry.deploy(await hst.getAddress(), owner.address);
  await registry.waitForDeployment();

  // Chuyen ownership sang registry de mint
  await hst.transferOwnership(await registry.getAddress());

  // 3. GovernanceContract
  const Governance = await ethers.getContractFactory("GovernanceContract");
  const gov = await Governance.deploy(
    await hst.getAddress(),
    await registry.getAddress(),
    owner.address
  );
  await gov.waitForDeployment();

  await gov.grantRole(await gov.CAMPAIGN_MANAGER_ROLE(), owner.address);

  // 4. Dang ky co dong
  const shareholders = [
    { acc: quydpt, hst: 2_500_000n, tier: 2 },
    { acc: cdA,    hst: 1_500_000n, tier: 1 },
    { acc: cdB,    hst: 1_000_000n, tier: 1 },
    { acc: cdC,    hst:   500_000n, tier: 0 },
  ];

  for (const s of shareholders) {
    const idHash = ethers.keccak256(ethers.toUtf8Bytes(`ID_${s.acc.address}`));
    await registry.addShareholder(s.acc.address, idHash, toWei(s.hst), s.tier);
  }

  // 5. Self-delegate + mine 1 block de snapshot hop le
  await hst.connect(owner).delegate(owner.address);
  for (const s of shareholders) {
    await hst.connect(s.acc).delegate(s.acc.address);
  }

  // Mine them 1 block sau khi delegate de getPastVotes khong bi "future lookup"
  await ethers.provider.send("evm_mine", []);

  // Dang ky owner vao registry (owner giu token tu constructor)
  // Owner can duoc dang ky de canVote() tra ve true
  const ownerIdHash = ethers.keccak256(ethers.toUtf8Bytes(`ID_${owner.address}`));

  // Transfer lai ownership ve owner tam thoi de dang ky
  // Cach khac: dung transferOwnership va mint truc tiep
  // Owner da co token nen chi can dang ky vao registry ma khong mint them
  // Ta them owner vao registry bang cach goi addShareholder voi 1 wei (symbolic)
  // Nhung truoc tien phai lay lai quyen mint:
  // => Thay vao do, ta deploy lai voi thu tu khac: owner tu dang ky truoc

  return { hst, registry, gov, owner, quydpt, cdA, cdB, cdC, nobody };
}

// Fixture rieng: owner duoc dang ky vao registry
async function deployWithOwnerRegistered() {
  const [owner, quydpt, cdA, cdB, cdC, nobody] = await ethers.getSigners();

  const HSTToken = await ethers.getContractFactory("HSTToken");
  const hst = await HSTToken.deploy(owner.address);
  await hst.waitForDeployment();

  const Registry = await ethers.getContractFactory("ShareholderRegistry");
  const registry = await Registry.deploy(await hst.getAddress(), owner.address);
  await registry.waitForDeployment();

  // Dang ky owner TRUOC khi chuyen ownership
  // Owner co san 10M token tu constructor, ta burn het roi mint lai qua registry
  // Cach don gian: chuyen ownership, roi addShareholder cho owner voi 0 token bo sung
  // Nhung registry.addShareholder se mint them => owner se co them token
  // 
  // Giai phap: KHONG chuyen ownership ngay, dang ky owner truoc
  const ownerIdHash = ethers.keccak256(ethers.toUtf8Bytes(`ID_OWNER`));

  // Burn het token cua owner truoc
  // Sau do addShareholder se mint chinh xac 4_500_000 HST cho owner
  await hst.burn(owner.address, toWei(10_000_000n)); // burn het supply cu

  // Bay gio chuyen ownership sang registry
  await hst.transferOwnership(await registry.getAddress());

  // Dang ky tat ca co dong (registry se mint)
  const shareholders = [
    { acc: owner,  hst: 4_500_000n, tier: 3 },
    { acc: quydpt, hst: 2_500_000n, tier: 2 },
    { acc: cdA,    hst: 1_500_000n, tier: 1 },
    { acc: cdB,    hst: 1_000_000n, tier: 1 },
    { acc: cdC,    hst:   500_000n, tier: 0 },
  ];

  for (const s of shareholders) {
    const idHash = ethers.keccak256(ethers.toUtf8Bytes(`ID_${s.acc.address}`));
    await registry.addShareholder(s.acc.address, idHash, toWei(s.hst), s.tier);
  }

  // GovernanceContract
  const Governance = await ethers.getContractFactory("GovernanceContract");
  const gov = await Governance.deploy(
    await hst.getAddress(),
    await registry.getAddress(),
    owner.address
  );
  await gov.waitForDeployment();
  await gov.grantRole(await gov.CAMPAIGN_MANAGER_ROLE(), owner.address);

  // Self-delegate
  for (const s of shareholders) {
    await hst.connect(s.acc).delegate(s.acc.address);
  }

  // Mine 1 block de snapshot hop le
  await ethers.provider.send("evm_mine", []);

  return { hst, registry, gov, owner, quydpt, cdA, cdB, cdC, nobody };
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("GovernanceContract", function () {

  // ── Campaign Creation ────────────────────────────────────────────────────────
  describe("Campaign Creation", function () {
    it("CAMPAIGN_MANAGER can create a campaign", async function () {
      const { gov, owner } = await loadFixture(deployWithOwnerRegistered);

      await expect(
        gov.createCampaign("Test Proposal", "Description", ProposalType.ROUTINE, VotingMech.LINEAR, false)
      ).to.emit(gov, "CampaignCreated").withArgs(1n, "Test Proposal", 0, 0, owner.address);

      const c = await gov.getCampaign(1n);
      expect(c.id).to.equal(1n);
      expect(c.status).to.equal(1); // ACTIVE
    });

    it("non-manager cannot create campaign", async function () {
      const { gov, nobody } = await loadFixture(deployWithOwnerRegistered);

      await expect(
        gov.connect(nobody).createCampaign("Hack", "...", ProposalType.ROUTINE, VotingMech.LINEAR, false)
      ).to.be.reverted;
    });

    it("snapshot block is set at creation time", async function () {
      const { gov } = await loadFixture(deployWithOwnerRegistered);
      const blockBefore = await ethers.provider.getBlockNumber();

      await gov.createCampaign("Snapshot Test", "...", ProposalType.ROUTINE, VotingMech.LINEAR, false);

      const c = await gov.getCampaign(1n);
      expect(c.snapshotBlock).to.be.gte(blockBefore);
    });
  });

  // ── ID-101 ───────────────────────────────────────────────────────────────────
  describe("ID-101: Phe duyet ngan sach R&D (Routine, Linear)", function () {
    it("should PASS: owner+quydpt (70%) > threshold 50%", async function () {
      const { gov, owner, quydpt, cdA, cdB, cdC } =
        await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign(
        "Phe duyet ngan sach R&D 2025", "Ngan sach 2 ty VND cho R&D",
        ProposalType.ROUTINE, VotingMech.LINEAR, false
      );
      const cId = 1n;

      await gov.connect(owner).castVote(cId, VoteOption.FOR);
      await gov.connect(quydpt).castVote(cId, VoteOption.FOR);
      await gov.connect(cdA).castVote(cId, VoteOption.AGAINST);
      await gov.connect(cdB).castVote(cId, VoteOption.AGAINST);
      await gov.connect(cdC).castVote(cId, VoteOption.AGAINST);

      await time.increase(DAYS(8));
      await gov.finalizeCampaign(cId);

      const c = await gov.getCampaign(cId);
      expect(c.status).to.equal(5); // EXECUTED
    });

    it("accounts[5] (nobody) bi reject: No voting power", async function () {
      const { gov, nobody } = await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign("Test", "...", ProposalType.ROUTINE, VotingMech.LINEAR, false);

      await expect(
        gov.connect(nobody).castVote(1n, VoteOption.FOR)
      ).to.be.revertedWith("Gov: not eligible to vote");
    });

    it("cannot vote twice", async function () {
      const { gov, owner } = await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign("Test", "...", ProposalType.ROUTINE, VotingMech.LINEAR, false);
      await gov.connect(owner).castVote(1n, VoteOption.FOR);

      await expect(
        gov.connect(owner).castVote(1n, VoteOption.AGAINST)
      ).to.be.revertedWith("Gov: already voted");
    });

    it("cannot vote after deadline", async function () {
      const { gov, owner } = await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign("Test", "...", ProposalType.ROUTINE, VotingMech.LINEAR, false);
      await time.increase(DAYS(8));

      await expect(
        gov.connect(owner).castVote(1n, VoteOption.FOR)
      ).to.be.revertedWith("Gov: voting ended");
    });
  });

  // ── ID-102 ───────────────────────────────────────────────────────────────────
  describe("ID-102: Chia co tuc (Major, Linear, 66% threshold)", function () {
    it("should PASS with 70% despite minority opposition", async function () {
      const { gov, owner, quydpt, cdA, cdB, cdC } =
        await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign(
        "Chia co tuc 15%", "Phan phoi 15% loi nhuan",
        ProposalType.MAJOR, VotingMech.LINEAR, false
      );
      const cId = 1n;

      await gov.connect(owner).castVote(cId, VoteOption.FOR);
      await gov.connect(quydpt).castVote(cId, VoteOption.FOR);
      await gov.connect(cdA).castVote(cId, VoteOption.AGAINST);
      await gov.connect(cdB).castVote(cId, VoteOption.AGAINST);
      await gov.connect(cdC).castVote(cId, VoteOption.AGAINST);

      await time.increase(DAYS(15));
      await gov.finalizeCampaign(cId);

      const c = await gov.getCampaign(cId);
      expect(c.status).to.equal(5); // EXECUTED
    });

    it("should FAIL if quorum not met", async function () {
      const { gov, cdC } = await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign("Chia co tuc", "...", ProposalType.MAJOR, VotingMech.LINEAR, false);
      await gov.connect(cdC).castVote(1n, VoteOption.FOR);

      await time.increase(DAYS(15));
      await gov.finalizeCampaign(1n);

      const c = await gov.getCampaign(1n);
      expect(c.status).to.equal(6); // DEFEATED
    });
  });

  // ── ID-103 ───────────────────────────────────────────────────────────────────
  describe("ID-103: Bau CEO (Linear vs Quadratic comparison)", function () {
    it("LINEAR: owner (45%) dominates result", async function () {
      const { gov, owner, quydpt, cdA, cdB, cdC } =
        await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign("Bau CEO - Linear", "...", ProposalType.MAJOR, VotingMech.LINEAR, false);

      await gov.connect(owner).castVote(1n, VoteOption.FOR);
      await gov.connect(quydpt).castVote(1n, VoteOption.FOR);
      await gov.connect(cdA).castVote(1n, VoteOption.AGAINST);
      await gov.connect(cdB).castVote(1n, VoteOption.AGAINST);
      await gov.connect(cdC).castVote(1n, VoteOption.AGAINST);

      const [forV, againstV] = await gov.getVoteCounts(1n);
      expect(forV).to.be.gt(againstV);
    });

    it("QUADRATIC: power gap reduced (sqrt operator)", async function () {
      const { gov, owner, cdC } = await loadFixture(deployWithOwnerRegistered);

      // Mine them 1 block truoc khi tao campaign de snapshotBlock < currentBlock
      await ethers.provider.send("evm_mine", []);

      await gov.createCampaign("Bau CEO - Quadratic", "...", ProposalType.MAJOR, VotingMech.QUADRATIC, false);

      // Mine them 1 block de snapshotBlock la "qua khu"
      await ethers.provider.send("evm_mine", []);

      const ownerWeight = await gov.getEffectiveWeight(1n, owner.address);
      const cdCWeight   = await gov.getEffectiveWeight(1n, cdC.address);

      const ownerHST = toWei(4_500_000n);
      const cdCHST   = toWei(500_000n);

      const linearRatio    = Number(ownerHST) / Number(cdCHST);
      const quadraticRatio = Number(ownerWeight) / Number(cdCWeight);

      expect(quadraticRatio).to.be.lt(linearRatio);
      console.log(`    Linear ratio: ${linearRatio.toFixed(2)}:1`);
      console.log(`    Quadratic ratio: ${quadraticRatio.toFixed(2)}:1`);
    });

    it("EQUAL: all voters have weight 1", async function () {
      const { gov, owner, cdC } = await loadFixture(deployWithOwnerRegistered);

      await ethers.provider.send("evm_mine", []);
      await gov.createCampaign("Bau CEO - Equal", "...", ProposalType.MAJOR, VotingMech.EQUAL, false);
      await ethers.provider.send("evm_mine", []);

      const ownerWeight = await gov.getEffectiveWeight(1n, owner.address);
      const cdCWeight   = await gov.getEffectiveWeight(1n, cdC.address);

      expect(ownerWeight).to.equal(1n);
      expect(cdCWeight).to.equal(1n);
    });
  });

  // ── ID-104: Commit-Reveal ────────────────────────────────────────────────────
  describe("ID-104: M&A - Commit-Reveal scheme", function () {
    async function createCommitRevealCampaign(gov) {
      await gov.createCampaign(
        "Sap nhap cong ty XYZ", "Thuong vu M&A voi XYZ Corp",
        ProposalType.MA, VotingMech.LINEAR, true
      );
      return 1n;
    }

    it("commit dung -> reveal thanh cong", async function () {
      const { gov, cdA } = await loadFixture(deployWithOwnerRegistered);
      const cId = await createCommitRevealCampaign(gov);

      const option = VoteOption.FOR;
      const salt = ethers.randomBytes(32);
      const voteHash = ethers.keccak256(
        ethers.solidityPacked(["uint8", "bytes32", "address"], [option, salt, cdA.address])
      );

      await gov.connect(cdA).commitVote(cId, voteHash);

      await time.increase(DAYS(8));
      await gov.transitionToReveal(cId);

      await expect(gov.connect(cdA).revealVote(cId, option, salt))
        .to.emit(gov, "VoteRevealed");
    });

    it("reveal voi salt sai -> revert hash mismatch", async function () {
      const { gov, cdB } = await loadFixture(deployWithOwnerRegistered);
      const cId = await createCommitRevealCampaign(gov);

      const option    = VoteOption.FOR;
      const goodSalt  = ethers.randomBytes(32);
      const wrongSalt = ethers.randomBytes(32);

      const voteHash = ethers.keccak256(
        ethers.solidityPacked(["uint8", "bytes32", "address"], [option, goodSalt, cdB.address])
      );
      await gov.connect(cdB).commitVote(cId, voteHash);

      await time.increase(DAYS(8));
      await gov.transitionToReveal(cId);

      // Fix: dung revertedWith dung voi error message trong contract (da doi thanh -)
      await expect(
        gov.connect(cdB).revealVote(cId, option, wrongSalt)
      ).to.be.revertedWith("Gov: hash mismatch - invalid reveal");
    });

    it("khong commit ma co reveal -> revert", async function () {
      const { gov, cdC } = await loadFixture(deployWithOwnerRegistered);
      const cId = await createCommitRevealCampaign(gov);

      await time.increase(DAYS(8));
      await gov.transitionToReveal(cId);

      const salt = ethers.randomBytes(32);
      await expect(
        gov.connect(cdC).revealVote(cId, VoteOption.FOR, salt)
      ).to.be.reverted;
    });

    it("commit khi da qua deadline -> revert", async function () {
      const { gov, cdA } = await loadFixture(deployWithOwnerRegistered);
      const cId = await createCommitRevealCampaign(gov);

      await time.increase(DAYS(8));

      const voteHash = ethers.randomBytes(32);
      await expect(
        gov.connect(cdA).commitVote(cId, voteHash)
      ).to.be.revertedWith("Gov: commit phase ended");
    });
  });

  // ── ABSTAIN ──────────────────────────────────────────────────────────────────
  describe("ABSTAIN voting", function () {
    it("ABSTAIN counts toward quorum but not pass rate", async function () {
      const { gov, owner, quydpt, cdA } = await loadFixture(deployWithOwnerRegistered);

      await gov.createCampaign("Abstain test", "...", ProposalType.ROUTINE, VotingMech.LINEAR, false);

      await gov.connect(owner).castVote(1n, VoteOption.ABSTAIN);
      await gov.connect(quydpt).castVote(1n, VoteOption.FOR);
      await gov.connect(cdA).castVote(1n, VoteOption.AGAINST);

      const [forV, againstV, abstainV] = await gov.getVoteCounts(1n);
      expect(abstainV).to.be.gt(0n);

      await time.increase(DAYS(8));
      await gov.finalizeCampaign(1n);

      const c = await gov.getCampaign(1n);
      expect(c.status).to.equal(5); // EXECUTED
    });
  });

});