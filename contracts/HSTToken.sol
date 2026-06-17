// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title HSTToken — Holding Share Token
 * ============================================================
 * VAI TRÒ VÀ CHỨC NĂNG CỦA TOKEN (Nhận xét thầy #1)
 * ============================================================
 *
 * HST (Holding Share Token) là token đại diện cho QUYỀN SỞ HỮU CỔ PHẦN
 * và QUYỀN BIỂU QUYẾT trong hệ thống quản trị DAO.
 *
 * ── 3 VAI TRÒ CHÍNH ──────────────────────────────────────────
 *
 * [1] CHỨNG NHẬN SỞ HỮU (Ownership Certificate)
 *     Mỗi 1 HST = 1 đơn vị cổ phần trong công ty.
 *     Tổng cung cố định 10,000,000 HST = 100% cổ phần.
 *     Cổ đông sở hữu 4,500,000 HST = nắm giữ 45% công ty.
 *     Không thể phát hành thêm sau khi phân bổ xong (supply cố định).
 *
 * [2] QUYỀN BIỂU QUYẾT (Voting Power)
 *     Token phải được "kích hoạt" qua delegate() để có voting power.
 *     Lý do tách biệt: không phải ai cũng muốn vote → tiết kiệm gas.
 *     Công thức tính trọng số (tuỳ chiến dịch):
 *       - LINEAR:    weight = số HST nắm giữ tại snapshotBlock
 *       - QUADRATIC: weight = √(số HST)  → bảo vệ cổ đông nhỏ
 *       - EQUAL:     weight = 1 (nếu có HST > 0) → 1 người 1 phiếu
 *
 * [3] CHỨNG MINH TƯ CÁCH (Eligibility Proof)
 *     ShareholderRegistry dùng số dư HST để xác định Tier cổ đông:
 *       Tier 3 (Sáng lập)  : ≥ 30% tổng cung (≥ 3,000,000 HST)
 *       Tier 2 (Chiến lược): ≥ 10% tổng cung (≥ 1,000,000 HST)
 *       Tier 1 (Tổ chức)   : ≥  1% tổng cung (≥   100,000 HST)
 *       Tier 0 (Nhỏ lẻ)    :  <  1% tổng cung
 *
 * ── TẠI SAO DÙNG ERC20Votes THAY VÌ ERC20 THƯỜNG ────────────
 *
 * ERC20 thường dùng balanceOf() để kiểm tra số dư HIỆN TẠI.
 * Vấn đề: kẻ xấu có thể mua token trước vote → vote → bán ngay.
 *
 * ERC20Votes lưu LỊCH SỬ số dư tại mỗi block (checkpoint).
 * Khi tạo campaign, hệ thống chụp snapshotBlock = block.number.
 * Khi vote, hệ thống tra getPastVotes(voter, snapshotBlock).
 * → Mua/bán token SAU snapshot KHÔNG ảnh hưởng quyền biểu quyết.
 *
 * ── ON-CHAIN vs OFF-CHAIN (Nhận xét thầy #4) ─────────────────
 *
 * ON-CHAIN (lưu trên blockchain, bất biến):
 *   - Tổng cung token (totalSupply)
 *   - Số dư token từng ví (balanceOf)
 *   - Lịch sử checkpoint voting power (getPastVotes)
 *   - Quyền sở hữu contract (owner)
 *
 * OFF-CHAIN (lưu ngoài blockchain):
 *   - Tên cổ đông thực tế (vd: "Nguyễn Văn A")
 *   - CCCD / giấy tờ định danh gốc
 *   - contract_addresses.json (địa chỉ contract để dashboard đọc)
 *   - Giao diện Streamlit dashboard
 * ============================================================
 */
contract HSTToken is ERC20Votes, Ownable {

    // ─── Hằng số ──────────────────────────────────────────────
    /// @notice Tổng cung cố định: 10,000,000 HST (đại diện 100% cổ phần)
    uint256 public constant TOTAL_INITIAL_SUPPLY = 10_000_000 * 10 ** 18;

    /// @notice Số decimals (18 = chuẩn ERC20, 1 HST = 10^18 đơn vị cơ bản)
    /// Ví dụ: 4,500,000 HST được lưu là 4_500_000 * 10^18 = 4.5 * 10^24

    // ─── Events ───────────────────────────────────────────────
    /// @notice Phát sinh khi mint token cho cổ đông mới
    event TokensMinted(address indexed to, uint256 amount, string reason);

    /// @notice Phát sinh khi đốt token (vd: thu hồi cổ phần)
    event TokensBurned(address indexed from, uint256 amount);

    // ─── Constructor ──────────────────────────────────────────
    /**
     * @notice Khởi tạo token, mint toàn bộ 10M HST cho initialOwner.
     * @dev initialOwner thường là deployer, sau đó sẽ burn hết và
     *      transfer ownership sang ShareholderRegistry để Registry
     *      mint lại đúng số cho từng cổ đông (xem setup_demo.js).
     *
     * Quy trình đầy đủ (ON-CHAIN):
     *   1. Deploy → 10M HST mint cho Admin
     *   2. Admin burn 10M → totalSupply = 0
     *   3. Transfer ownership → ShareholderRegistry
     *   4. Registry.addShareholder() mint đúng số cho từng cổ đông
     *
     * Mục đích: tránh lỗi "nhân đôi tổng cung" nếu không burn trước.
     */
    constructor(address initialOwner)
        ERC20("Holding Share Token", "HST")
        ERC20Permit("HSTToken")
    {
        transferOwnership(initialOwner);
        _mint(initialOwner, TOTAL_INITIAL_SUPPLY);
    }

    // ─── Hàm mint (chỉ Owner = Registry được gọi) ────────────
    /**
     * @notice Đúc token mới cho một địa chỉ.
     * @dev Chỉ Registry (owner) mới được gọi — sau khi transfer ownership.
     * @param to     Địa chỉ ví nhận token (= ví cổ đông)
     * @param amount Số lượng token (đơn vị wei, đã nhân 10^18)
     * @param reason Lý do mint (lưu trong event để audit)
     */
    function mint(
        address to,
        uint256 amount,
        string calldata reason
    ) external onlyOwner {
        require(to != address(0), "HSTToken: mint to zero address");
        require(amount > 0,       "HSTToken: amount must be > 0");
        _mint(to, amount);
        emit TokensMinted(to, amount, reason);
    }

    // ─── Hàm burn (chỉ Owner được gọi) ───────────────────────
    /**
     * @notice Đốt token từ một địa chỉ.
     * @dev Dùng trong bước khởi tạo để burn 10M ban đầu của Admin.
     */
    function burn(address from, uint256 amount) external onlyOwner {
        require(from != address(0), "HSTToken: burn from zero address");
        _burn(from, amount);
        emit TokensBurned(from, amount);
    }

    // ─── Hàm tiện ích đọc thông tin ──────────────────────────

    /**
     * @notice Lấy voting power của voter tại một block trong quá khứ.
     * @dev Wrapper của getPastVotes() — dùng trong GovernanceContract.
     * @param voter       Địa chỉ cần kiểm tra
     * @param blockNumber Block snapshot (thời điểm tạo campaign)
     * @return Voting power (= số HST đã delegate tại blockNumber)
     */
    function getVotingPowerAt(address voter, uint256 blockNumber)
        external view returns (uint256)
    {
        return getPastVotes(voter, blockNumber);
    }

    /**
     * @notice Lấy tổng cung tại một block trong quá khứ.
     * @dev Dùng để tính quorum: totalVoted / totalSupplyAtSnapshot.
     */
    function getTotalSupplyAt(uint256 blockNumber)
        external view returns (uint256)
    {
        return getPastTotalSupply(blockNumber);
    }

    /**
     * @notice Trả về thông tin tổng quan về token.
     * @dev Hàm này giúp Dashboard hiển thị thông tin token rõ ràng
     *      mà không cần gọi nhiều hàm riêng lẻ.
     * @return tokenName      Tên token ("Holding Share Token")
     * @return tokenSymbol    Ký hiệu ("HST")
     * @return tokenDecimals  Số decimals (18)
     * @return supply         Tổng cung hiện tại (đơn vị wei)
     * @return supplyHST      Tổng cung (đơn vị HST, đã chia 10^18)
     * @return ownerAddr      Địa chỉ owner hiện tại (= Registry sau khởi tạo)
     */
    function getTokenInfo() external view returns (
        string memory tokenName,
        string memory tokenSymbol,
        uint8         tokenDecimals,
        uint256       supply,
        uint256       supplyHST,
        address       ownerAddr
    ) {
        supply       = totalSupply();
        return (
            name(),
            symbol(),
            decimals(),
            supply,
            supply / 10**18,
            owner()
        );
    }

    /**
     * @notice Kiểm tra nhanh xem một địa chỉ đã delegate chưa.
     * @return isDelegated true nếu đã delegate (có voting power > 0)
     * @return vp          Voting power hiện tại
     */
    function getDelegationStatus(address voter) external view returns (
        bool    isDelegated,
        uint256 vp
    ) {
        vp = getVotes(voter);
        isDelegated = (vp > 0);
    }
}
