// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "./HSTToken.sol";
import "./IdentityVerifier.sol";

contract ShareholderRegistry is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant SUPER_ADMIN_ROLE    = keccak256("SUPER_ADMIN");
    bytes32 public constant REGISTRY_ADMIN_ROLE = keccak256("REGISTRY_ADMIN");
    bytes32 public constant AUDITOR_ROLE        = keccak256("AUDITOR");

    struct Shareholder {
        address  wallet;
        bytes32  identityHash;
        uint256  lockUntil;
        uint256  registeredAt;
        bool     isActive;
        uint8    tier;
        bool     kycVerified;
    }

    HSTToken           public immutable hstToken;
    IdentityVerifier   public           identityVerifier;
    bool               public           requireKYC = false;

    mapping(address => Shareholder) public registry;
    address[] public shareholderList;
    uint256   public totalShareholders;
    uint256   public activeShareholders;

    uint256 public constant TIER3_THRESHOLD = 3000;
    uint256 public constant TIER2_THRESHOLD = 1000;
    uint256 public constant TIER1_THRESHOLD = 100;

    event ShareholderAdded(address indexed wallet, uint256 initialTokens, uint8 tier, bytes32 identityHash, bool kycVerified);
    event ShareholderDeactivated(address indexed wallet, string reason, uint256 lockUntil);
    event ShareholderReactivated(address indexed wallet);
    event IdentityVerifierSet(address verifier);
    event KYCRequirementChanged(bool required);

    constructor(address _hstToken, address _superAdmin) {
        hstToken = HSTToken(_hstToken);
        _grantRole(DEFAULT_ADMIN_ROLE,  _superAdmin);
        _grantRole(SUPER_ADMIN_ROLE,    _superAdmin);
        _grantRole(REGISTRY_ADMIN_ROLE, _superAdmin);
    }

    function setIdentityVerifier(address _verifier) external onlyRole(SUPER_ADMIN_ROLE) {
        identityVerifier = IdentityVerifier(_verifier);
        emit IdentityVerifierSet(_verifier);
    }

    function setRequireKYC(bool _require) external onlyRole(SUPER_ADMIN_ROLE) {
        requireKYC = _require;
        emit KYCRequirementChanged(_require);
    }

    // [A] Thêm cổ đông với KYC thật
    function addShareholderWithKYC(
        address wallet,
        uint256 initialTokens,
        uint8   tier,
        IdentityVerifier.KYCLevel minKYCLevel
    ) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused nonReentrant {
        require(wallet != address(0), "Registry: zero address");
        require(!registry[wallet].isActive, "Registry: already registered");
        require(initialTokens > 0, "Registry: tokens must be > 0");
        require(address(identityVerifier) != address(0), "Registry: IdentityVerifier not set");
        require(identityVerifier.isKYCValid(wallet, minKYCLevel), "Registry: wallet does not have valid KYC");

        bytes32 identityHash  = identityVerifier.getVerifiedIdentityHash(wallet);
        uint8   assignedTier  = (tier == 255) ? _calculateTier(initialTokens) : tier;

        registry[wallet] = Shareholder({
            wallet: wallet, identityHash: identityHash,
            lockUntil: 0, registeredAt: block.timestamp,
            isActive: true, tier: assignedTier, kycVerified: true
        });
        shareholderList.push(wallet);
        totalShareholders++;
        activeShareholders++;
        hstToken.mint(wallet, initialTokens, "Shareholder allocation (KYC verified)");
        emit ShareholderAdded(wallet, initialTokens, assignedTier, identityHash, true);
    }

    // [B] Thêm cổ đông không cần KYC (backward-compatible cho demo)
    function addShareholder(
        address wallet,
        bytes32 identityHash,
        uint256 initialTokens,
        uint8   tier
    ) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused nonReentrant {
        require(wallet != address(0), "Registry: zero address");
        require(!registry[wallet].isActive, "Registry: already registered");
        require(identityHash != bytes32(0), "Registry: missing identity hash");
        require(initialTokens > 0, "Registry: tokens must be > 0");
        require(!requireKYC, "Registry: KYC required - use addShareholderWithKYC");

        uint8 assignedTier = (tier == 255) ? _calculateTier(initialTokens) : tier;
        registry[wallet] = Shareholder({
            wallet: wallet, identityHash: identityHash,
            lockUntil: 0, registeredAt: block.timestamp,
            isActive: true, tier: assignedTier, kycVerified: false
        });
        shareholderList.push(wallet);
        totalShareholders++;
        activeShareholders++;
        hstToken.mint(wallet, initialTokens, "Initial shareholder allocation");
        emit ShareholderAdded(wallet, initialTokens, assignedTier, identityHash, false);
    }

    function canVote(address wallet) external view returns (bool) {
        Shareholder storage s = registry[wallet];
        if (!s.isActive)                    return false;
        if (s.lockUntil >= block.timestamp) return false;
        if (hstToken.balanceOf(wallet) == 0) return false;
        if (requireKYC && address(identityVerifier) != address(0)) {
            if (!identityVerifier.isKYCValid(wallet, IdentityVerifier.KYCLevel.BASIC)) return false;
        }
        return true;
    }

    function deactivateShareholder(address wallet, string calldata reason)
        external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused
    {
        require(registry[wallet].isActive, "Registry: already inactive");
        uint256 lockEnd = block.timestamp + 365 days;
        registry[wallet].isActive  = false;
        registry[wallet].lockUntil = lockEnd;
        activeShareholders--;
        emit ShareholderDeactivated(wallet, reason, lockEnd);
    }

    function reactivateShareholder(address wallet) external onlyRole(SUPER_ADMIN_ROLE) whenNotPaused {
        require(!registry[wallet].isActive, "Registry: already active");
        registry[wallet].isActive  = true;
        registry[wallet].lockUntil = 0;
        activeShareholders++;
        emit ShareholderReactivated(wallet);
    }

    function getShareholderInfo(address wallet) external view returns (Shareholder memory) {
        return registry[wallet];
    }

    function getAllShareholders() external view returns (address[] memory) {
        return shareholderList;
    }

    function getDynamicTier(address wallet) external view returns (uint8) {
        return _calculateTier(hstToken.balanceOf(wallet));
    }

    function pause()   external onlyRole(SUPER_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(SUPER_ADMIN_ROLE) { _unpause(); }

    function _calculateTier(uint256 tokenAmount) internal view returns (uint8) {
        uint256 ts = hstToken.totalSupply();
        if (ts == 0) return 0;
        uint256 bps = (tokenAmount * 10_000) / ts;
        if (bps >= TIER3_THRESHOLD) return 3;
        if (bps >= TIER2_THRESHOLD) return 2;
        if (bps >= TIER1_THRESHOLD) return 1;
        return 0;
    }
}
