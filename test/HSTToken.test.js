// test/HSTToken.test.js
// ============================================================
//  Unit tests cho HSTToken
//  Chạy: npx hardhat test test/HSTToken.test.js
// ============================================================
const { expect }        = require("chai");
const { ethers }        = require("hardhat");
const { loadFixture }   = require("@nomicfoundation/hardhat-toolbox/network-helpers");

// ─── Fixture ──────────────────────────────────────────────────────────────────
async function deployHSTTokenFixture() {
  const [owner, alice, bob, carol, nobody] = await ethers.getSigners();

  const HSTToken = await ethers.getContractFactory("HSTToken");
  const hst = await HSTToken.deploy(owner.address);
  await hst.waitForDeployment();

  const TOTAL_SUPPLY = await hst.TOTAL_INITIAL_SUPPLY();

  return { hst, owner, alice, bob, carol, nobody, TOTAL_SUPPLY };
}

// ─── Test Suite ───────────────────────────────────────────────────────────────
describe("HSTToken", function () {

  // ── Deployment ──────────────────────────────────────────────────────────────
  describe("Deployment", function () {
    it("should set correct name and symbol", async function () {
      const { hst } = await loadFixture(deployHSTTokenFixture);
      expect(await hst.name()).to.equal("Holding Share Token");
      expect(await hst.symbol()).to.equal("HST");
    });

    it("should mint total supply to owner on deploy", async function () {
      const { hst, owner, TOTAL_SUPPLY } = await loadFixture(deployHSTTokenFixture);
      expect(await hst.balanceOf(owner.address)).to.equal(TOTAL_SUPPLY);
      expect(await hst.totalSupply()).to.equal(TOTAL_SUPPLY);
    });

    it("should have 18 decimals", async function () {
      const { hst } = await loadFixture(deployHSTTokenFixture);
      expect(await hst.decimals()).to.equal(18);
    });

    it("should set owner correctly", async function () {
      const { hst, owner } = await loadFixture(deployHSTTokenFixture);
      expect(await hst.owner()).to.equal(owner.address);
    });
  });

  // ── Mint ────────────────────────────────────────────────────────────────────
  describe("Mint", function () {
    it("owner can mint to any address", async function () {
      const { hst, owner, alice } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("1000", 18);

      await expect(hst.mint(alice.address, amount, "Test mint"))
        .to.emit(hst, "TokensMinted")
        .withArgs(alice.address, amount, "Test mint");

      expect(await hst.balanceOf(alice.address)).to.equal(amount);
    });

    it("non-owner cannot mint", async function () {
      const { hst, alice, bob } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("1000", 18);

      await expect(
        hst.connect(alice).mint(bob.address, amount, "Hack attempt")
      ).to.be.revertedWith("Ownable: caller is not the owner");
    });

    it("cannot mint to zero address", async function () {
      const { hst } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("1000", 18);

      await expect(
        hst.mint(ethers.ZeroAddress, amount, "Zero mint")
      ).to.be.revertedWith("HSTToken: mint to zero address");
    });

    it("cannot mint zero amount", async function () {
      const { hst, alice } = await loadFixture(deployHSTTokenFixture);

      await expect(
        hst.mint(alice.address, 0n, "Zero amount")
      ).to.be.revertedWith("HSTToken: amount must be > 0");
    });
  });

  // ── Voting Power (ERC20Votes) ────────────────────────────────────────────────
  describe("Voting Power & Delegation", function () {
    it("new holder has 0 voting power before self-delegation", async function () {
      const { hst, owner, alice } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("500000", 18);
      await hst.transfer(alice.address, amount);

      // Chưa delegate → voting power = 0
      expect(await hst.getVotes(alice.address)).to.equal(0n);
    });

    it("holder gains voting power after self-delegation", async function () {
      const { hst, owner, alice } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("500000", 18);
      await hst.transfer(alice.address, amount);

      // Self-delegate
      await hst.connect(alice).delegate(alice.address);
      expect(await hst.getVotes(alice.address)).to.equal(amount);
    });

    it("delegation transfers voting power but NOT tokens", async function () {
      const { hst, owner, alice, bob } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("1000000", 18);
      await hst.transfer(alice.address, amount);
      await hst.connect(alice).delegate(alice.address);

      // Alice uỷ quyền cho Bob
      await hst.connect(alice).delegate(bob.address);

      expect(await hst.getVotes(bob.address)).to.equal(amount);   // Bob có voting power
      expect(await hst.getVotes(alice.address)).to.equal(0n);      // Alice mất voting power
      expect(await hst.balanceOf(alice.address)).to.equal(amount); // Token vẫn của Alice
    });

    it("getPastVotes returns balance at snapshot block", async function () {
      const { hst, owner, alice } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("1000000", 18);

      await hst.transfer(alice.address, amount);
      await hst.connect(alice).delegate(alice.address);

      // Lấy block hiện tại làm snapshot
      const snapshotBlock = await ethers.provider.getBlockNumber();

      // Mine thêm 1 block để snapshot hợp lệ
      await ethers.provider.send("evm_mine", []);

      // Transfer thêm AFTER snapshot → không ảnh hưởng snapshot
      const extra = ethers.parseUnits("500000", 18);
      await hst.transfer(alice.address, extra);

      const votesAtSnapshot = await hst.getPastVotes(alice.address, snapshotBlock);
      expect(votesAtSnapshot).to.equal(amount); // Chỉ tính tại snapshot block
    });
  });

  // ── Burn ────────────────────────────────────────────────────────────────────
  describe("Burn", function () {
    it("owner can burn tokens", async function () {
      const { hst, owner, alice } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("100000", 18);
      await hst.transfer(alice.address, amount);

      const supplyBefore = await hst.totalSupply();
      await expect(hst.burn(alice.address, amount))
        .to.emit(hst, "TokensBurned")
        .withArgs(alice.address, amount);

      expect(await hst.totalSupply()).to.equal(supplyBefore - amount);
      expect(await hst.balanceOf(alice.address)).to.equal(0n);
    });

    it("non-owner cannot burn", async function () {
      const { hst, alice, bob } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("1000", 18);

      await expect(
        hst.connect(alice).burn(bob.address, amount)
      ).to.be.revertedWith("Ownable: caller is not the owner");
    });
  });

  // ── Helper views ────────────────────────────────────────────────────────────
  describe("View helpers", function () {
    it("getVotingPowerAt returns correct past votes", async function () {
      const { hst, owner, alice } = await loadFixture(deployHSTTokenFixture);
      const amount = ethers.parseUnits("2000000", 18);
      await hst.transfer(alice.address, amount);
      await hst.connect(alice).delegate(alice.address);

      const block = await ethers.provider.getBlockNumber();
      await ethers.provider.send("evm_mine", []);

      expect(await hst.getVotingPowerAt(alice.address, block)).to.equal(amount);
    });

    it("getTotalSupplyAt returns correct past total supply", async function () {
      const { hst, TOTAL_SUPPLY, alice } = await loadFixture(deployHSTTokenFixture);
      const block = await ethers.provider.getBlockNumber();
      await ethers.provider.send("evm_mine", []);

      expect(await hst.getTotalSupplyAt(block)).to.equal(TOTAL_SUPPLY);
    });
  });

});