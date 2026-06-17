// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/**
 * @title VotingCertificate — Biên bản biểu quyết có chữ ký số
 * ============================================================
 * NHẬN XÉT THẦY #3: Bổ sung biên bản chữ ký số sau khi finalize
 * ============================================================
 *
 * Sau khi một chiến dịch biểu quyết kết thúc (finalize), hệ thống
 * tự động tạo ra một "biên bản điện tử" (Certificate) lưu trên
 * blockchain với đầy đủ thông tin:
 *   - Kết quả biểu quyết (PASS/DEFEAT)
 *   - Số phiếu FOR / AGAINST / ABSTAIN
 *   - Tỷ lệ tham gia (quorum achieved)
 *   - Hash của toàn bộ dữ liệu biểu quyết (chứng minh không bị sửa)
 *   - Chữ ký số của người finalize (msg.sender)
 *   - Timestamp chính xác
 *
 * ── ON-CHAIN vs OFF-CHAIN (Nhận xét thầy #4) ─────────────────
 *
 * ON-CHAIN (Contract này lưu):
 *   ✅ certificateHash  — Hash toàn bộ dữ liệu biểu quyết (bất biến)
 *   ✅ finalizedBy      — Địa chỉ ví người ký (xác thực danh tính)
 *   ✅ finalizedAt      — Timestamp lúc ký (không thể làm giả)
 *   ✅ result           — PASS hoặc DEFEAT (không thể sửa sau khi lưu)
 *   ✅ forVotes / againstVotes / abstainVotes (số liệu thực tế)
 *
 * OFF-CHAIN (App.py / Dashboard tạo và lưu):
 *   📄 File PDF biên bản (format đẹp, in được)
 *   📄 File JSON export đầy đủ chi tiết
 *   🔗 Link Polygonscan để verify (khi deploy lên testnet)
 *
 * ── CÁCH XÁC MINH TÍNH XÁC THỰC ─────────────────────────────
 *
 * Bất kỳ ai cũng có thể verify biên bản:
 *   1. Lấy certificateHash từ contract
 *   2. Tự tính lại hash từ dữ liệu gốc
 *   3. So sánh → nếu khớp = dữ liệu chưa bị chỉnh sửa
 *
 * Đây là ví dụ ánh xạ thực tế ra thực tế (Nhận xét thầy #2):
 *   Truyền thống: Thư ký họp ký biên bản giấy → dễ làm giả
 *   Blockchain:   Smart contract tự tạo hash → không thể làm giả
 * ============================================================
 */
contract VotingCertificate is AccessControl {
    using ECDSA for bytes32;

    bytes32 public constant CERTIFIER_ROLE = keccak256("CERTIFIER");

    // ─── Struct biên bản ──────────────────────────────────────
    struct Certificate {
        uint256 campaignId;        // ID chiến dịch
        string  campaignTitle;     // Tên chiến dịch
        bool    passed;            // Kết quả: true=PASS, false=DEFEAT

        uint256 forVotes;          // Tổng phiếu TÁN THÀNH (đã tính trọng số)
        uint256 againstVotes;      // Tổng phiếu PHẢN ĐỐI
        uint256 abstainVotes;      // Tổng phiếu TRẮNG
        uint256 totalParticipants; // Số cổ đông đã bỏ phiếu

        uint256 quorumBps;         // Ngưỡng quorum yêu cầu (basis points)
        uint256 participationBps;  // Tỷ lệ tham gia thực tế (basis points)
        uint256 passThreshold;     // Ngưỡng thông qua (basis points)
        uint256 forBps;            // Tỷ lệ FOR trong phiếu quyết định

        uint8   proposalType;      // 0=ROUTINE, 1=MAJOR, 2=MA
        uint8   mechanism;         // 0=LINEAR, 1=QUADRATIC, 2=EQUAL

        address finalizedBy;       // Địa chỉ ví người ký biên bản
        uint256 finalizedAt;       // Timestamp lúc finalize (Unix)
        uint256 snapshotBlock;     // Block snapshot dùng để tính phiếu

        bytes32 certificateHash;   // Hash toàn bộ dữ liệu biên bản
        bool    exists;            // Cờ kiểm tra tồn tại
    }

    // ─── Storage ──────────────────────────────────────────────
    /// @notice campaignId => Certificate
    mapping(uint256 => Certificate) public certificates;

    /// @notice Danh sách tất cả campaign đã có biên bản
    uint256[] public certifiedCampaigns;

    // ─── Events ───────────────────────────────────────────────
    /**
     * @notice Phát sinh khi biên bản được tạo.
     * @dev Event này là "chữ ký số" lưu vĩnh viễn trên blockchain.
     *      Block explorer (Ganache / Polygonscan) có thể xem được.
     */
    event CertificateIssued(
        uint256 indexed campaignId,
        string  campaignTitle,
        bool    passed,
        bytes32 certificateHash,
        address indexed finalizedBy,
        uint256 finalizedAt
    );

    // ─── Constructor ──────────────────────────────────────────
    constructor(address _admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(CERTIFIER_ROLE,     _admin);
    }

    // ─── Hàm tạo biên bản ─────────────────────────────────────
    /**
     * @notice Tạo biên bản chữ ký số sau khi chiến dịch finalize.
     * @dev Được gọi từ GovernanceContract.finalizeCampaign() hoặc
     *      từ Script/Dashboard sau khi finalize thành công.
     *
     * Ánh xạ thực tế (Nhận xét thầy #2):
     *   Trong họp ĐHCĐ truyền thống:
     *     → Thư ký đọc kết quả, Chủ tịch ký biên bản
     *   Trong hệ thống DAO này:
     *     → Smart contract tự tính kết quả, msg.sender "ký" bằng
     *       private key (ECDSA signature gắn với địa chỉ ví)
     *
     * @param campaignId        ID chiến dịch vừa finalize
     * @param campaignTitle     Tên chiến dịch
     * @param passed            Kết quả PASS/DEFEAT
     * @param forVotes          Tổng phiếu FOR
     * @param againstVotes      Tổng phiếu AGAINST
     * @param abstainVotes      Tổng phiếu ABSTAIN
     * @param totalParticipants Số cổ đông đã vote
     * @param quorumBps         Quorum yêu cầu (basis points)
     * @param participationBps  Tỷ lệ tham gia thực tế
     * @param passThreshold     Ngưỡng thông qua
     * @param forBps            Tỷ lệ FOR / (FOR+AGAINST)
     * @param proposalType      Loại đề xuất
     * @param mechanism         Cơ chế tính phiếu
     * @param snapshotBlock     Block snapshot
     */
    function issueCertificate(
        uint256 campaignId,
        string  calldata campaignTitle,
        bool    passed,
        uint256 forVotes,
        uint256 againstVotes,
        uint256 abstainVotes,
        uint256 totalParticipants,
        uint256 quorumBps,
        uint256 participationBps,
        uint256 passThreshold,
        uint256 forBps,
        uint8   proposalType,
        uint8   mechanism,
        uint256 snapshotBlock
    ) external onlyRole(CERTIFIER_ROLE) {
        require(campaignId > 0,                         "Cert: invalid campaign id");
        require(!certificates[campaignId].exists,       "Cert: already issued");
        require(bytes(campaignTitle).length > 0,        "Cert: title required");

        // ── Tạo certificateHash ──────────────────────────────
        // Hash toàn bộ dữ liệu quan trọng → bất kỳ thay đổi nào
        // cũng tạo ra hash khác → dễ phát hiện giả mạo
        bytes32 certHash = keccak256(abi.encodePacked(
            campaignId,
            campaignTitle,
            passed,
            forVotes,
            againstVotes,
            abstainVotes,
            passThreshold,
            participationBps,
            msg.sender,       // Địa chỉ ký
            block.timestamp   // Thời điểm ký
        ));

        // ── Lưu biên bản on-chain ────────────────────────────
        certificates[campaignId] = Certificate({
            campaignId:        campaignId,
            campaignTitle:     campaignTitle,
            passed:            passed,
            forVotes:          forVotes,
            againstVotes:      againstVotes,
            abstainVotes:      abstainVotes,
            totalParticipants: totalParticipants,
            quorumBps:         quorumBps,
            participationBps:  participationBps,
            passThreshold:     passThreshold,
            forBps:            forBps,
            proposalType:      proposalType,
            mechanism:         mechanism,
            finalizedBy:       msg.sender,
            finalizedAt:       block.timestamp,
            snapshotBlock:     snapshotBlock,
            certificateHash:   certHash,
            exists:            true
        });

        certifiedCampaigns.push(campaignId);

        // ── Phát sinh event (chữ ký số on-chain) ─────────────
        emit CertificateIssued(
            campaignId,
            campaignTitle,
            passed,
            certHash,
            msg.sender,
            block.timestamp
        );
    }

    // ─── Hàm xác minh biên bản ────────────────────────────────
    /**
     * @notice Xác minh tính toàn vẹn của biên bản.
     * @dev Tính lại hash từ dữ liệu gốc và so sánh với hash đã lưu.
     *      Nếu khớp → biên bản chưa bị chỉnh sửa.
     *
     * @return isValid      true nếu hash khớp (biên bản hợp lệ)
     * @return storedHash   Hash đang lưu trên contract
     * @return computedHash Hash tính lại từ dữ liệu
     */
    function verifyCertificate(uint256 campaignId) external view returns (
        bool    isValid,
        bytes32 storedHash,
        bytes32 computedHash
    ) {
        Certificate storage cert = certificates[campaignId];
        require(cert.exists, "Cert: not found");

        computedHash = keccak256(abi.encodePacked(
            cert.campaignId,
            cert.campaignTitle,
            cert.passed,
            cert.forVotes,
            cert.againstVotes,
            cert.abstainVotes,
            cert.passThreshold,
            cert.participationBps,
            cert.finalizedBy,
            cert.finalizedAt
        ));

        storedHash = cert.certificateHash;
        isValid    = (computedHash == storedHash);
    }

    // ─── View helpers ─────────────────────────────────────────
    /**
     * @notice Lấy toàn bộ thông tin biên bản của một campaign.
     */
    function getCertificate(uint256 campaignId)
        external view returns (Certificate memory)
    {
        require(certificates[campaignId].exists, "Cert: not found");
        return certificates[campaignId];
    }

    /**
     * @notice Lấy danh sách tất cả campaign đã có biên bản.
     */
    function getAllCertifiedCampaigns()
        external view returns (uint256[] memory)
    {
        return certifiedCampaigns;
    }

    /**
     * @notice Kiểm tra nhanh campaign đã có biên bản chưa.
     */
    function hasCertificate(uint256 campaignId) external view returns (bool) {
        return certificates[campaignId].exists;
    }
}
