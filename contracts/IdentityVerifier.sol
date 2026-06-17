// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title IdentityVerifier — KYC xác thực danh tính on-chain
 * ══════════════════════════════════════════════════════════════
 * Giải quyết vấn đề: identityHash hiện tại là hash giả
 *   keccak256("DEMO_CCCD_0_0x...") → không có giá trị thực tế
 *
 * Giải pháp: 3 bước KYC thực tế
 *
 *   [OFF-CHAIN] Người dùng gửi CCCD/hộ chiếu
 *       ↓
 *   [OFF-CHAIN] Admin xác minh giấy tờ thật
 *       ↓
 *   [OFF-CHAIN] Admin ký KYC proof bằng private key
 *       ↓
 *   [ON-CHAIN]  Người dùng submit proof lên contract
 *       ↓
 *   [ON-CHAIN]  Contract verify chữ ký Admin → lưu identityHash
 *
 * ── TẠI SAO DÙNG CHỮ KÝ ADMIN THAY VÌ LƯU TRỰC TIẾP? ────────
 *
 *   Nếu Admin tự gọi addShareholder() → Admin phải online 24/7,
 *   tốn gas, bottleneck.
 *
 *   Với Admin Signature pattern:
 *     Admin ký off-chain (miễn phí, nhanh)
 *     Người dùng tự submit on-chain (trả gas của mình)
 *     Contract verify chữ ký → không cần Admin online
 *
 * ── DỮ LIỆU ON-CHAIN vs OFF-CHAIN ────────────────────────────
 *
 *   ON-CHAIN (lưu trong contract này):
 *     ✅ identityHash = keccak256(realName + nationalId + dob)
 *        → Không lộ thông tin cá nhân, vẫn verify được
 *     ✅ kycLevel: 0=Chưa KYC, 1=Cơ bản, 2=Nâng cao, 3=Đầy đủ
 *     ✅ verifiedAt: thời điểm KYC được xác nhận
 *     ✅ expiresAt: KYC hết hạn khi nào (tránh CCCD hết hạn)
 *     ✅ kycHash: hash của toàn bộ KYC data (audit trail)
 *
 *   OFF-CHAIN (Admin giữ, không lưu blockchain):
 *     📄 Ảnh CCCD / hộ chiếu gốc
 *     📄 Tên thật, số CCCD, ngày sinh
 *     📄 Kết quả xác minh (approved/rejected)
 * ══════════════════════════════════════════════════════════════
 */
contract IdentityVerifier is AccessControl, ReentrancyGuard {
    using ECDSA for bytes32;

    // ─── Roles ────────────────────────────────────────────────
    bytes32 public constant KYC_ADMIN_ROLE   = keccak256("KYC_ADMIN");
    bytes32 public constant KYC_SIGNER_ROLE  = keccak256("KYC_SIGNER");

    // ─── Enums ────────────────────────────────────────────────
    /**
     * KYC Level:
     *   NONE    — Chưa KYC
     *   BASIC   — Xác minh email + SĐT (Tier 0)
     *   STANDARD— Xác minh CCCD (Tier 0-1)
     *   FULL    — Xác minh CCCD + selfie + địa chỉ (Tier 2-3)
     */
    enum KYCLevel { NONE, BASIC, STANDARD, FULL }

    // ─── Structs ──────────────────────────────────────────────
    struct KYCRecord {
        address wallet;
        bytes32 identityHash;  // keccak256(realName + nationalId + dob)
        bytes32 kycHash;       // keccak256(toàn bộ KYC data + timestamp)
        KYCLevel level;
        uint256 verifiedAt;
        uint256 expiresAt;     // KYC hết hạn (tránh CCCD hết hạn)
        bool    isVerified;
        bool    isRevoked;
        string  country;       // Quốc gia (VN, US, ...)
    }

    // ─── State ────────────────────────────────────────────────
    mapping(address => KYCRecord) public kycRecords;
    mapping(bytes32 => bool)      public usedNonces;   // Chống replay
    mapping(bytes32 => address)   public hashToWallet; // Kiểm tra trùng identityHash

    uint256 public constant KYC_VALIDITY_PERIOD = 365 days; // KYC hợp lệ 1 năm
    uint256 public totalVerified;

    // ─── Events ───────────────────────────────────────────────
    /**
     * @dev KYCSubmitted — người dùng đã submit proof lên chain.
     *      Đây là bằng chứng on-chain rằng KYC đã được xác minh
     *      bởi Admin có thẩm quyền (KYC_SIGNER_ROLE).
     */
    event KYCSubmitted(
        address indexed wallet,
        bytes32 identityHash,
        KYCLevel level,
        uint256 verifiedAt,
        uint256 expiresAt
    );
    event KYCRevoked(address indexed wallet, string reason);
    event KYCRenewed(address indexed wallet, uint256 newExpiresAt);
    event KYCSignerUpdated(address indexed signer, bool active);

    // ─── Constructor ──────────────────────────────────────────
    constructor(address _admin, address _kycSigner) {
        require(_admin     != address(0), "KYC: invalid admin");
        require(_kycSigner != address(0), "KYC: invalid signer");

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(KYC_ADMIN_ROLE,     _admin);
        _grantRole(KYC_SIGNER_ROLE,    _kycSigner);
    }

    // ─── Submit KYC (người dùng gọi) ──────────────────────────
    /**
     * @notice Người dùng submit KYC proof để được xác minh.
     *
     * Flow thực tế:
     *   1. Người dùng upload CCCD lên hệ thống (OFF-CHAIN)
     *   2. Admin xác minh giấy tờ thật (OFF-CHAIN)
     *   3. Admin tạo signature: sign(identityHash + kycHash + level + nonce + wallet)
     *   4. Người dùng nhận signature từ Admin (OFF-CHAIN)
     *   5. Người dùng gọi submitKYC() với signature (ON-CHAIN)
     *   6. Contract verify signature → lưu KYC record
     *
     * @param identityHash  keccak256(tên thật + số CCCD + ngày sinh)
     * @param kycHash       keccak256(toàn bộ KYC data + timestamp)
     * @param level         Mức KYC (BASIC/STANDARD/FULL)
     * @param nonce         Số ngẫu nhiên, chống replay attack
     * @param country       Quốc tịch ("VN", "US", ...)
     * @param adminSignature Chữ ký của KYC_SIGNER (từ bước 3)
     */
    function submitKYC(
        bytes32  identityHash,
        bytes32  kycHash,
        KYCLevel level,
        bytes32  nonce,
        string calldata country,
        bytes calldata adminSignature
    ) external nonReentrant {
        require(!kycRecords[msg.sender].isVerified, "KYC: already verified");
        require(identityHash != bytes32(0),         "KYC: empty identity hash");
        require(kycHash      != bytes32(0),         "KYC: empty kyc hash");
        require(!usedNonces[nonce],                 "KYC: nonce already used");
        require(level != KYCLevel.NONE,             "KYC: invalid level");

        // Kiểm tra identityHash chưa được dùng bởi ví khác
        // (1 người không thể đăng ký 2 ví)
        require(
            hashToWallet[identityHash] == address(0) ||
            hashToWallet[identityHash] == msg.sender,
            "KYC: identity already registered to another wallet"
        );

        // ── Verify chữ ký Admin ───────────────────────────────
        // Message mà Admin đã ký off-chain:
        // keccak256(identityHash + kycHash + level + nonce + wallet + chainId)
        bytes32 messageHash = _buildKYCMessage(
            identityHash, kycHash, level, nonce, msg.sender
        );
        address recoveredSigner = messageHash.toEthSignedMessageHash().recover(adminSignature);
        require(
            hasRole(KYC_SIGNER_ROLE, recoveredSigner),
            "KYC: invalid admin signature"
        );

        // ── Lưu KYC record on-chain ───────────────────────────
        uint256 now_      = block.timestamp;
        uint256 expiresAt = now_ + KYC_VALIDITY_PERIOD;

        kycRecords[msg.sender] = KYCRecord({
            wallet:       msg.sender,
            identityHash: identityHash,
            kycHash:      kycHash,
            level:        level,
            verifiedAt:   now_,
            expiresAt:    expiresAt,
            isVerified:   true,
            isRevoked:    false,
            country:      country
        });

        usedNonces[nonce]              = true;
        hashToWallet[identityHash]     = msg.sender;
        totalVerified++;

        emit KYCSubmitted(msg.sender, identityHash, level, now_, expiresAt);
    }

    // ─── Admin: Revoke KYC ────────────────────────────────────
    /**
     * @notice Thu hồi KYC khi phát hiện gian lận hoặc CCCD hết hạn.
     * @dev Sau khi revoke, cổ đông không thể vote cho đến khi KYC lại.
     */
    function revokeKYC(address wallet, string calldata reason)
        external onlyRole(KYC_ADMIN_ROLE)
    {
        require(kycRecords[wallet].isVerified, "KYC: not verified");
        require(bytes(reason).length > 0,      "KYC: reason required");

        kycRecords[wallet].isVerified = false;
        kycRecords[wallet].isRevoked  = true;

        // Xóa mapping để identityHash có thể dùng lại (khi KYC lại)
        bytes32 idHash = kycRecords[wallet].identityHash;
        if (hashToWallet[idHash] == wallet) {
            delete hashToWallet[idHash];
        }

        totalVerified--;
        emit KYCRevoked(wallet, reason);
    }

    // ─── Gia hạn KYC ─────────────────────────────────────────
    /**
     * @notice Gia hạn KYC đã hết hạn — cần signature mới từ Admin.
     */
    function renewKYC(
        bytes32  newKycHash,
        bytes32  nonce,
        bytes calldata adminSignature
    ) external nonReentrant {
        KYCRecord storage rec = kycRecords[msg.sender];
        require(rec.identityHash != bytes32(0), "KYC: not registered");
        require(!rec.isRevoked,                  "KYC: revoked - submit new KYC");

        bytes32 renewMessage = keccak256(abi.encodePacked(
            "RENEW", rec.identityHash, newKycHash, nonce, msg.sender, block.chainid
        ));
        address recoveredSigner = renewMessage.toEthSignedMessageHash().recover(adminSignature);
        require(hasRole(KYC_SIGNER_ROLE, recoveredSigner), "KYC: invalid signature");
        require(!usedNonces[nonce], "KYC: nonce used");

        rec.kycHash   = newKycHash;
        rec.verifiedAt = block.timestamp;
        rec.expiresAt  = block.timestamp + KYC_VALIDITY_PERIOD;
        rec.isVerified = true;
        usedNonces[nonce] = true;

        emit KYCRenewed(msg.sender, rec.expiresAt);
    }

    // ─── View Functions ───────────────────────────────────────
    /**
     * @notice Kiểm tra ví có KYC hợp lệ không.
     * @param minLevel Mức KYC tối thiểu yêu cầu
     */
    function isKYCValid(address wallet, KYCLevel minLevel) external view returns (bool) {
        KYCRecord storage rec = kycRecords[wallet];
        return (
            rec.isVerified &&
            !rec.isRevoked &&
            block.timestamp < rec.expiresAt &&
            uint8(rec.level) >= uint8(minLevel)
        );
    }

    /**
     * @notice Lấy identityHash đã xác minh — dùng để gắn vào ShareholderRegistry.
     */
    function getVerifiedIdentityHash(address wallet) external view returns (bytes32) {
        require(kycRecords[wallet].isVerified, "KYC: not verified");
        return kycRecords[wallet].identityHash;
    }

    function getKYCRecord(address wallet) external view returns (KYCRecord memory) {
        return kycRecords[wallet];
    }

    function getKYCStatus(address wallet) external view returns (
        bool    isVerified,
        bool    isExpired,
        bool    isRevoked,
        KYCLevel level,
        uint256 expiresAt,
        uint256 daysUntilExpiry
    ) {
        KYCRecord storage rec = kycRecords[wallet];
        isVerified = rec.isVerified;
        isExpired  = block.timestamp >= rec.expiresAt && rec.expiresAt > 0;
        isRevoked  = rec.isRevoked;
        level      = rec.level;
        expiresAt  = rec.expiresAt;
        daysUntilExpiry = rec.expiresAt > block.timestamp
            ? (rec.expiresAt - block.timestamp) / 1 days
            : 0;
    }

    // ─── Internal ─────────────────────────────────────────────
    function _buildKYCMessage(
        bytes32  identityHash,
        bytes32  kycHash,
        KYCLevel level,
        bytes32  nonce,
        address  wallet
    ) internal view returns (bytes32) {
        return keccak256(abi.encodePacked(
            "KYC_VERIFY",
            identityHash,
            kycHash,
            uint8(level),
            nonce,
            wallet,
            block.chainid   // Chống cross-chain replay
        ));
    }
}
