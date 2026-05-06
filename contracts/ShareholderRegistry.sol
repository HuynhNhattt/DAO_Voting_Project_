// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// OZ v4: ReentrancyGuard va Pausable nam trong /security/
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "./HSTToken.sol";

/**
 * @title ShareholderRegistry
 * @notice Quan ly danh sach co dong: them, vo hieu hoa, kiem tra tier.
 */
contract ShareholderRegistry is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant SUPER_ADMIN_ROLE    = keccak256("SUPER_ADMIN");
    bytes32 public constant REGISTRY_ADMIN_ROLE = keccak256("REGISTRY_ADMIN");
    bytes32 public constant AUDITOR_ROLE        = keccak256("AUDITOR");

    struct Shareholder {
        address wallet;
        bytes32 identityHash;
        uint256 lockUntil;
        uint256 registeredAt;
        bool    isActive;
        uint8   tier;
    }

    HSTToken public immutable hstToken;

    mapping(address => Shareholder) public registry;
    address[]                       public shareholderList;
    uint256                         public totalShareholders;
    uint256                         public activeShareholders;

    uint256 public constant TIER3_THRESHOLD = 3000;
    uint256 public constant TIER2_THRESHOLD = 1000;
    uint256 public constant TIER1_THRESHOLD = 100;

    event ShareholderAdded(address indexed wallet, uint256 initialTokens, uint8 tier, bytes32 identityHash);
    event ShareholderDeactivated(address indexed wallet, string reason, uint256 lockUntil);
    event ShareholderReactivated(address indexed wallet);
    event ShareholderTierUpdated(address indexed wallet, uint8 oldTier, uint8 newTier);

    // OZ v4: AccessControl, Pausable, ReentrancyGuard deu co constructor mac dinh
    constructor(address _hstToken, address _superAdmin) {
        require(_hstToken   != address(0), "Registry: invalid token address");
        require(_superAdmin != address(0), "Registry: invalid admin address");

        hstToken = HSTToken(_hstToken);

        _grantRole(DEFAULT_ADMIN_ROLE,  _superAdmin);
        _grantRole(SUPER_ADMIN_ROLE,    _superAdmin);
        _grantRole(REGISTRY_ADMIN_ROLE, _superAdmin);
    }

    function addShareholder(
        address wallet,
        bytes32 identityHash,
        uint256 initialTokens,
        uint8   tier
    ) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused nonReentrant {
        require(wallet != address(0),        "Registry: zero address");
        require(!registry[wallet].isActive,  "Registry: already registered");
        require(identityHash != bytes32(0),  "Registry: missing identity hash");
        require(initialTokens > 0,           "Registry: tokens must be > 0");

        uint8 assignedTier = (tier == 255) ? _calculateTier(initialTokens) : tier;
        require(assignedTier <= 3, "Registry: invalid tier");

        registry[wallet] = Shareholder({
            wallet:       wallet,
            identityHash: identityHash,
            lockUntil:    0,
            registeredAt: block.timestamp,
            isActive:     true,
            tier:         assignedTier
        });

        shareholderList.push(wallet);
        totalShareholders++;
        activeShareholders++;

        hstToken.mint(wallet, initialTokens, "Initial shareholder allocation");
        emit ShareholderAdded(wallet, initialTokens, assignedTier, identityHash);
    }

    function deactivateShareholder(
        address wallet,
        string calldata reason
    ) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused {
        require(registry[wallet].isActive,  "Registry: already inactive");
        require(bytes(reason).length > 0,    "Registry: reason required");

        uint256 lockEnd = block.timestamp + 365 days;
        registry[wallet].isActive  = false;
        registry[wallet].lockUntil = lockEnd;
        activeShareholders--;

        emit ShareholderDeactivated(wallet, reason, lockEnd);
    }

    function reactivateShareholder(address wallet)
        external onlyRole(SUPER_ADMIN_ROLE) whenNotPaused
    {
        require(!registry[wallet].isActive,         "Registry: already active");
        require(registry[wallet].registeredAt > 0,  "Registry: not registered");

        registry[wallet].isActive  = true;
        registry[wallet].lockUntil = 0;
        activeShareholders++;

        emit ShareholderReactivated(wallet);
    }

    function pause()   external onlyRole(SUPER_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(SUPER_ADMIN_ROLE) { _unpause(); }

    function canVote(address wallet) external view returns (bool) {
        Shareholder storage s = registry[wallet];
        return (
            s.isActive &&
            s.lockUntil < block.timestamp &&
            hstToken.balanceOf(wallet) > 0
        );
    }

    function getDynamicTier(address wallet) external view returns (uint8) {
        return _calculateTier(hstToken.balanceOf(wallet));
    }

    function getAllShareholders() external view returns (address[] memory) {
        return shareholderList;
    }

    function getShareholderInfo(address wallet)
        external view returns (Shareholder memory)
    {
        return registry[wallet];
    }

    function _calculateTier(uint256 tokenAmount) internal view returns (uint8) {
        uint256 totalSupply = hstToken.totalSupply();
        if (totalSupply == 0) return 0;
        uint256 bps = (tokenAmount * 10_000) / totalSupply;
        if (bps >= TIER3_THRESHOLD) return 3;
        if (bps >= TIER2_THRESHOLD) return 2;
        if (bps >= TIER1_THRESHOLD) return 1;
        return 0;
    }
}
