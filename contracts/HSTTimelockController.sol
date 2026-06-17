// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title HSTTimelockController
 * Kế thừa OpenZeppelin TimelockController với hằng số delay
 * theo ProposalType — dùng bởi GovernanceContract.
 *
 * ROUTINE → ROUTINE_DELAY = 2 ngày
 * MAJOR   → MAJOR_DELAY   = 7 ngày
 * MA      → MA_DELAY      = 14 ngày
 */
contract HSTTimelockController is TimelockController {

    uint256 public constant ROUTINE_DELAY = 2 days;
    uint256 public constant MAJOR_DELAY   = 7 days;
    uint256 public constant MA_DELAY      = 14 days;

    constructor(
        address[] memory proposers,
        address[] memory executors,
        address          admin
    )
        TimelockController(ROUTINE_DELAY, proposers, executors, admin)
    {}
}
