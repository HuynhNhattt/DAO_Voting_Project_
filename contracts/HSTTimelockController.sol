// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title HSTTimelockController
 * @notice Trì hoãn thực thi đề xuất sau khi biểu quyết thông qua.
 *         Thời gian mặc định = ROUTINE_DELAY (2 ngày).
 *         Governance contract sẽ queue với delay tuỳ theo ProposalType.
 *
 *  Routine → 2 ngày
 *  Major   → 7 ngày
 *  M&A     → 14 ngày
 */
contract HSTTimelockController is TimelockController {
    uint256 public constant ROUTINE_DELAY = 2 days;
    uint256 public constant MAJOR_DELAY   = 7 days;
    uint256 public constant MA_DELAY      = 14 days;

    /**
     * @param proposers  Danh sách địa chỉ được phép queue (GovernanceContract)
     * @param executors  Danh sách địa chỉ được phép execute (address(0) = anyone)
     * @param admin      Admin ban đầu (sau khi setup xong nên revoke role này)
     */
    constructor(
        address[] memory proposers,
        address[] memory executors,
        address          admin
    )
        TimelockController(
            ROUTINE_DELAY, // minDelay mặc định
            proposers,
            executors,
            admin
        )
    {}
}
