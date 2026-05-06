// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title HSTToken - Holding Share Token
 * @notice ERC-20 token dai dien quyen so huu va bieu quyet trong DAO.
 *         Ke thua ERC20Votes de co san snapshot + delegation.
 */
contract HSTToken is ERC20Votes, Ownable {
    uint256 public constant TOTAL_INITIAL_SUPPLY = 10_000_000 * 10 ** 18;

    event TokensMinted(address indexed to, uint256 amount, string reason);
    event TokensBurned(address indexed from, uint256 amount);

    // OZ v4: Ownable() khong nhan argument; ERC20Permit thay the EIP712
    constructor(address initialOwner)
        ERC20("Holding Share Token", "HST")
        ERC20Permit("HSTToken")
    {
        transferOwnership(initialOwner);
        _mint(initialOwner, TOTAL_INITIAL_SUPPLY);
    }

    function mint(
        address to,
        uint256 amount,
        string calldata reason
    ) external onlyOwner {
        require(to != address(0), "HSTToken: mint to zero address");
        require(amount > 0, "HSTToken: amount must be > 0");
        _mint(to, amount);
        emit TokensMinted(to, amount, reason);
    }

    function burn(address from, uint256 amount) external onlyOwner {
        require(from != address(0), "HSTToken: burn from zero address");
        _burn(from, amount);
        emit TokensBurned(from, amount);
    }

    function getVotingPowerAt(address voter, uint256 blockNumber)
        external view returns (uint256)
    {
        return getPastVotes(voter, blockNumber);
    }

    function getTotalSupplyAt(uint256 blockNumber)
        external view returns (uint256)
    {
        return getPastTotalSupply(blockNumber);
    }
}
