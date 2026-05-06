// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "./HSTToken.sol";
import "./ShareholderRegistry.sol";

/**
 * @title GovernanceContract
 * @notice Core contract xu ly toan bo logic bieu quyet:
 *         - Tao/quan ly chien dich (Campaign)
 *         - Linear / Quadratic / Equal voting
 *         - Commit-Reveal scheme (bo phieu kin)
 *         - Finalize & kiem tra ket qua
 */
contract GovernanceContract is AccessControl, ReentrancyGuard, Pausable {
    using Math for uint256;

    // Roles
    bytes32 public constant SUPER_ADMIN_ROLE      = keccak256("SUPER_ADMIN");
    bytes32 public constant CAMPAIGN_MANAGER_ROLE = keccak256("CAMPAIGN_MANAGER");
    bytes32 public constant AUDITOR_ROLE          = keccak256("AUDITOR");

    // Enums
    enum VoteOption      { FOR, AGAINST, ABSTAIN }
    enum VotingMechanism { LINEAR, QUADRATIC, EQUAL }
    enum ProposalType    { ROUTINE, MAJOR, MA }
    enum CampaignStatus  { DRAFT, ACTIVE, COMMIT, REVEAL, TALLYING, EXECUTED, DEFEATED, CANCELLED }

    // Structs
    struct Campaign {
        uint256  id;
        string   title;
        string   description;
        address  proposer;
        ProposalType    proposalType;
        VotingMechanism mechanism;
        CampaignStatus  status;

        uint256 createdAt;
        uint256 snapshotBlock;

        uint256 votingStart;
        uint256 votingDeadline;

        uint256 commitDeadline;
        uint256 revealStart;
        uint256 revealDeadline;
        bool    isCommitReveal;

        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;

        uint256 passThreshold;
        uint256 quorumBps;
    }

    struct Ballot {
        VoteOption option;
        uint256    weight;
        uint256    timestamp;
    }

    // State Variables
    HSTToken            public immutable hstToken;
    ShareholderRegistry public immutable registry;

    uint256 public campaignCounter;

    mapping(uint256 => Campaign) public campaigns;
    mapping(uint256 => mapping(address => bool))   public hasVoted;
    mapping(uint256 => mapping(address => Ballot)) public ballots;
    mapping(uint256 => mapping(address => bytes32)) public commitments;

    // Constants
    uint256 public constant ROUTINE_PASS_BPS   = 5000;
    uint256 public constant ROUTINE_QUORUM_BPS = 1000;
    uint256 public constant ROUTINE_VOTE_DAYS  = 7 days;

    uint256 public constant MAJOR_PASS_BPS     = 6600;
    uint256 public constant MAJOR_QUORUM_BPS   = 2000;
    uint256 public constant MAJOR_VOTE_DAYS    = 14 days;

    uint256 public constant MA_PASS_BPS        = 7500;
    uint256 public constant MA_QUORUM_BPS      = 3000;
    uint256 public constant MA_VOTE_DAYS       = 21 days;

    uint256 public constant COMMIT_DURATION    = 7 days;
    uint256 public constant REVEAL_DURATION    = 3 days;

    // Events
    event CampaignCreated(
        uint256 indexed campaignId,
        string  title,
        uint8   proposalType,
        uint8   mechanism,
        address proposer
    );
    event CampaignCancelled(uint256 indexed campaignId, string reason);
    event VoteCast(
        uint256 indexed campaignId,
        address indexed voter,
        uint8   option,
        uint256 weight
    );
    event VoteCommitted(uint256 indexed campaignId, address indexed voter);
    event VoteRevealed(
        uint256 indexed campaignId,
        address indexed voter,
        uint8   option,
        uint256 weight
    );
    event CampaignFinalized(
        uint256 indexed campaignId,
        bool    passed,
        uint256 forVotes,
        uint256 againstVotes,
        uint256 abstainVotes
    );

    // Constructor
    constructor(address _hstToken, address _registry, address _superAdmin) {
        require(_hstToken   != address(0), "Gov: invalid token");
        require(_registry   != address(0), "Gov: invalid registry");
        require(_superAdmin != address(0), "Gov: invalid admin");

        hstToken = HSTToken(_hstToken);
        registry = ShareholderRegistry(_registry);

        _grantRole(DEFAULT_ADMIN_ROLE,    _superAdmin);
        _grantRole(SUPER_ADMIN_ROLE,      _superAdmin);
        _grantRole(CAMPAIGN_MANAGER_ROLE, _superAdmin);
    }

    // Campaign Management

    /**
     * @notice Tao chien dich bieu quyet moi.
     */
    function createCampaign(
        string    calldata title,
        string    calldata description,
        ProposalType       proposalType,
        VotingMechanism    mechanism,
        bool               useCommitReveal
    )
        external
        onlyRole(CAMPAIGN_MANAGER_ROLE)
        whenNotPaused
        returns (uint256 campaignId)
    {
        require(bytes(title).length > 0,       "Gov: title required");
        require(bytes(description).length > 0, "Gov: description required");

        campaignId = ++campaignCounter;

        (uint256 passThreshold, uint256 quorumBps, uint256 voteDuration) =
            _getProposalParams(proposalType);

        Campaign storage c = campaigns[campaignId];
        c.id            = campaignId;
        c.title         = title;
        c.description   = description;
        c.proposer      = msg.sender;
        c.proposalType  = proposalType;
        c.mechanism     = mechanism;
        c.createdAt     = block.timestamp;
        c.snapshotBlock = block.number;
        c.passThreshold = passThreshold;
        c.quorumBps     = quorumBps;
        c.isCommitReveal = useCommitReveal;

        if (useCommitReveal) {
            c.status         = CampaignStatus.COMMIT;
            c.commitDeadline = block.timestamp + COMMIT_DURATION;
            c.revealStart    = block.timestamp + COMMIT_DURATION;
            c.revealDeadline = block.timestamp + COMMIT_DURATION + REVEAL_DURATION;
            c.votingDeadline = c.revealDeadline;
        } else {
            c.status        = CampaignStatus.ACTIVE;
            c.votingStart   = block.timestamp;
            c.votingDeadline = block.timestamp + voteDuration;
        }

        emit CampaignCreated(
            campaignId, title,
            uint8(proposalType), uint8(mechanism),
            msg.sender
        );
    }

    /**
     * @notice Huy chien dich (chi khi chua co ai bo phieu).
     */
    function cancelCampaign(
        uint256 campaignId,
        string calldata reason
    ) external onlyRole(CAMPAIGN_MANAGER_ROLE) whenNotPaused {
        Campaign storage c = campaigns[campaignId];
        require(
            c.status == CampaignStatus.ACTIVE || c.status == CampaignStatus.COMMIT,
            "Gov: cannot cancel"
        );
        require(
            c.forVotes == 0 && c.againstVotes == 0 && c.abstainVotes == 0,
            "Gov: votes already cast"
        );
        c.status = CampaignStatus.CANCELLED;
        emit CampaignCancelled(campaignId, reason);
    }

    // Standard Voting

    /**
     * @notice Bo phieu cho mot chien dich dang ACTIVE.
     */
    function castVote(
        uint256    campaignId,
        VoteOption option
    ) external whenNotPaused nonReentrant {
        Campaign storage c = campaigns[campaignId];

        require(c.status == CampaignStatus.ACTIVE,  "Gov: campaign not active");
        require(block.timestamp < c.votingDeadline,  "Gov: voting ended");
        require(!hasVoted[campaignId][msg.sender],    "Gov: already voted");
        require(registry.canVote(msg.sender),         "Gov: not eligible to vote");

        uint256 weight = getEffectiveWeight(campaignId, msg.sender);
        require(weight > 0, "Gov: no voting power");

        _recordVote(campaignId, msg.sender, option, weight);
        emit VoteCast(campaignId, msg.sender, uint8(option), weight);
    }

    // Commit-Reveal Voting

    /**
     * @notice Phase 1 - Gui hash commit (bo phieu kin).
     */
    function commitVote(
        uint256 campaignId,
        bytes32 voteHash
    ) external whenNotPaused nonReentrant {
        Campaign storage c = campaigns[campaignId];

        require(c.isCommitReveal,                                  "Gov: not commit-reveal");
        require(c.status == CampaignStatus.COMMIT,                 "Gov: not in commit phase");
        require(block.timestamp < c.commitDeadline,                "Gov: commit phase ended");
        require(commitments[campaignId][msg.sender] == bytes32(0), "Gov: already committed");
        require(registry.canVote(msg.sender),                       "Gov: not eligible");
        require(voteHash != bytes32(0),                            "Gov: empty hash");

        commitments[campaignId][msg.sender] = voteHash;
        emit VoteCommitted(campaignId, msg.sender);
    }

    /**
     * @notice Phase 2 - Reveal phieu bau thuc te.
     */
    function revealVote(
        uint256    campaignId,
        VoteOption option,
        bytes32    salt
    ) external whenNotPaused nonReentrant {
        Campaign storage c = campaigns[campaignId];

        require(c.isCommitReveal,                   "Gov: not commit-reveal");
        require(c.status == CampaignStatus.REVEAL,  "Gov: not in reveal phase");
        require(block.timestamp >= c.revealStart,   "Gov: reveal not started");
        require(block.timestamp < c.revealDeadline, "Gov: reveal phase ended");
        require(!hasVoted[campaignId][msg.sender],   "Gov: already revealed");

        bytes32 expectedHash = keccak256(
            abi.encodePacked(uint8(option), salt, msg.sender)
        );
        require(
            commitments[campaignId][msg.sender] == expectedHash,
            "Gov: hash mismatch - invalid reveal"
        );
        require(
            commitments[campaignId][msg.sender] != bytes32(0),
            "Gov: no commitment found"
        );

        uint256 weight = getEffectiveWeight(campaignId, msg.sender);
        require(weight > 0, "Gov: no voting power");

        _recordVote(campaignId, msg.sender, option, weight);
        emit VoteRevealed(campaignId, msg.sender, uint8(option), weight);
    }

    /**
     * @notice Chuyen chien dich sang giai doan REVEAL.
     */
    function transitionToReveal(
        uint256 campaignId
    ) external onlyRole(CAMPAIGN_MANAGER_ROLE) {
        Campaign storage c = campaigns[campaignId];
        require(c.isCommitReveal,                    "Gov: not commit-reveal");
        require(c.status == CampaignStatus.COMMIT,   "Gov: not in commit phase");
        require(block.timestamp >= c.commitDeadline, "Gov: commit not ended");
        c.status = CampaignStatus.REVEAL;
    }

    // Finalize Campaign

    /**
     * @notice Ket thuc chien dich va xac dinh ket qua.
     */
    function finalizeCampaign(
        uint256 campaignId
    ) external nonReentrant {
        Campaign storage c = campaigns[campaignId];
        require(
            c.status == CampaignStatus.ACTIVE || c.status == CampaignStatus.REVEAL,
            "Gov: cannot finalize"
        );
        require(block.timestamp >= c.votingDeadline, "Gov: voting still active");

        c.status = CampaignStatus.TALLYING;

        bool passed = _checkResult(campaignId);
        c.status = passed ? CampaignStatus.EXECUTED : CampaignStatus.DEFEATED;

        emit CampaignFinalized(
            campaignId, passed,
            c.forVotes, c.againstVotes, c.abstainVotes
        );
    }

    // Weight Calculation

    /**
     * @notice Tinh trong so bieu quyet theo co che da chon.
     */
    function getEffectiveWeight(
        uint256 campaignId,
        address voter
    ) public view returns (uint256 weight) {
        uint256 rawBalance = hstToken.getPastVotes(
            voter,
            campaigns[campaignId].snapshotBlock
        );

        VotingMechanism mechanism = campaigns[campaignId].mechanism;

        if (mechanism == VotingMechanism.QUADRATIC) {
            return Math.sqrt(rawBalance);
        } else if (mechanism == VotingMechanism.EQUAL) {
            return rawBalance > 0 ? 1 : 0;
        } else {
            return rawBalance;
        }
    }

    // View Functions

    function getVoteCounts(
        uint256 campaignId
    ) external view returns (uint256 forVotes, uint256 againstVotes, uint256 abstainVotes) {
        Campaign storage c = campaigns[campaignId];
        return (c.forVotes, c.againstVotes, c.abstainVotes);
    }

    function getBallot(
        uint256 campaignId,
        address voter
    ) external view returns (Ballot memory) {
        return ballots[campaignId][voter];
    }

    function getCampaign(
        uint256 campaignId
    ) external view returns (Campaign memory) {
        return campaigns[campaignId];
    }

    function getParticipationRate(
        uint256 campaignId
    ) external view returns (uint256 bps) {
        Campaign storage c = campaigns[campaignId];
        uint256 totalAtSnapshot = hstToken.getPastTotalSupply(c.snapshotBlock);
        if (totalAtSnapshot == 0) return 0;

        uint256 totalVoted = c.forVotes + c.againstVotes + c.abstainVotes;
        return (totalVoted * 10_000) / totalAtSnapshot;
    }

    // Emergency Controls
    function pause()   external onlyRole(SUPER_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(SUPER_ADMIN_ROLE) { _unpause(); }

    // Internal

    function _getProposalParams(ProposalType pType)
        internal pure
        returns (uint256 passThreshold, uint256 quorumBps, uint256 voteDuration)
    {
        if (pType == ProposalType.MAJOR) {
            return (MAJOR_PASS_BPS, MAJOR_QUORUM_BPS, MAJOR_VOTE_DAYS);
        } else if (pType == ProposalType.MA) {
            return (MA_PASS_BPS, MA_QUORUM_BPS, MA_VOTE_DAYS);
        } else {
            return (ROUTINE_PASS_BPS, ROUTINE_QUORUM_BPS, ROUTINE_VOTE_DAYS);
        }
    }

    function _recordVote(
        uint256    campaignId,
        address    voter,
        VoteOption option,
        uint256    weight
    ) internal {
        hasVoted[campaignId][voter] = true;
        ballots[campaignId][voter]  = Ballot(option, weight, block.timestamp);

        Campaign storage c = campaigns[campaignId];
        if (option == VoteOption.FOR)          c.forVotes     += weight;
        else if (option == VoteOption.AGAINST) c.againstVotes += weight;
        else                                   c.abstainVotes += weight;
    }

    function _checkResult(uint256 campaignId) internal view returns (bool) {
        Campaign storage c = campaigns[campaignId];
        uint256 totalAtSnapshot = hstToken.getPastTotalSupply(c.snapshotBlock);
        if (totalAtSnapshot == 0) return false;

        uint256 totalVoted = c.forVotes + c.againstVotes + c.abstainVotes;

        uint256 participationBps = (totalVoted * 10_000) / totalAtSnapshot;
        if (participationBps < c.quorumBps) return false;

        uint256 decisiveVotes = c.forVotes + c.againstVotes;
        if (decisiveVotes == 0) return false;

        uint256 forBps = (c.forVotes * 10_000) / decisiveVotes;
        return forBps > c.passThreshold;
    }
}
