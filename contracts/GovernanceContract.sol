// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "./HSTToken.sol";
import "./ShareholderRegistry.sol";
import "./HSTTimelockController.sol";

// Interface để gọi VotingCertificate tránh circular import
interface IVotingCertificate {
    function issueCertificate(
        uint256 campaignId, string calldata campaignTitle, bool passed,
        uint256 forVotes, uint256 againstVotes, uint256 abstainVotes,
        uint256 totalParticipants, uint256 quorumBps, uint256 participationBps,
        uint256 passThreshold, uint256 forBps,
        uint8 proposalType, uint8 mechanism, uint256 snapshotBlock
    ) external;
    function hasCertificate(uint256 campaignId) external view returns (bool);
}


contract GovernanceContract is AccessControl, ReentrancyGuard, Pausable {
    using Math for uint256;

    bytes32 public constant SUPER_ADMIN_ROLE      = keccak256("SUPER_ADMIN");
    bytes32 public constant CAMPAIGN_MANAGER_ROLE = keccak256("CAMPAIGN_MANAGER");

    enum VoteOption      { FOR, AGAINST, ABSTAIN }
    enum VotingMechanism { LINEAR, QUADRATIC, EQUAL }
    enum ProposalType    { ROUTINE, MAJOR, MA }
    enum CampaignStatus  {
        DRAFT, ACTIVE, COMMIT, REVEAL, TALLYING,
        EXECUTED, DEFEATED, CANCELLED, QUEUED, EXECUTABLE
    }

    struct Campaign {
        uint256         id;
        string          title;
        string          description;
        address         proposer;
        ProposalType    proposalType;
        VotingMechanism mechanism;
        CampaignStatus  status;
        uint256         createdAt;
        uint256         snapshotBlock;
        uint256         votingStart;
        uint256         votingDeadline;
        uint256         commitDeadline;
        uint256         revealStart;
        uint256         revealDeadline;
        bool            isCommitReveal;
        uint256         forVotes;
        uint256         againstVotes;
        uint256         abstainVotes;
        uint256         passThreshold;
        uint256         quorumBps;
        bytes32         timelockOperationId;
        uint256         timelockEta;
        uint256         timelockDelay;
        bool            timelockQueued;
    }

    struct Ballot {
        VoteOption option;
        uint256    weight;
        uint256    timestamp;
    }

    HSTToken              public immutable hstToken;
    ShareholderRegistry   public immutable registry;
    HSTTimelockController public           timelock;
    IVotingCertificate    public           votingCertificate;

    uint256 public campaignCounter;

    mapping(uint256 => Campaign)                            public campaigns;
    mapping(uint256 => mapping(address => bool))            public hasVoted;
    mapping(uint256 => mapping(address => Ballot))          public ballots;
    mapping(uint256 => mapping(address => bytes32))         public commitments;
    mapping(uint256 => uint256)                             public participantCount;

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

    event CampaignCreated(uint256 indexed campaignId, string title, uint8 proposalType,
        uint8 mechanism, address proposer, uint256 snapshotBlock, uint256 votingDeadline);
    event CampaignCancelled(uint256 indexed campaignId, string reason);
    event VoteCast(uint256 indexed campaignId, address indexed voter,
        uint8 option, uint256 weight, uint8 mechanism);
    event VoteCommitted(uint256 indexed campaignId, address indexed voter);
    event VoteRevealed(uint256 indexed campaignId, address indexed voter, uint8 option, uint256 weight);
    event CampaignFinalized(uint256 indexed campaignId, bool passed,
        uint256 forVotes, uint256 againstVotes, uint256 abstainVotes,
        bool timelockQueued, uint256 eta);
    event TimelockQueued(uint256 indexed campaignId, bytes32 operationId, uint256 delay, uint256 eta);
    event DecisionExecuted(uint256 indexed campaignId, address indexed executor, uint256 executedAt);
    event TimelockSet(address timelock);

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

    function setTimelock(address _timelock) external onlyRole(SUPER_ADMIN_ROLE) {
        require(_timelock != address(0), "Gov: invalid timelock");
        timelock = HSTTimelockController(payable(_timelock));
        emit TimelockSet(_timelock);
    }

    function setCertificateContract(address _cert) external onlyRole(SUPER_ADMIN_ROLE) {
        require(_cert != address(0), "Gov: invalid cert");
        votingCertificate = IVotingCertificate(_cert);
    }

    // ── Campaign ──────────────────────────────────────────────
    function createCampaign(
        string    calldata title,
        string    calldata description,
        ProposalType       proposalType,
        VotingMechanism    mechanism,
        bool               useCommitReveal
    ) external onlyRole(CAMPAIGN_MANAGER_ROLE) whenNotPaused returns (uint256 campaignId) {
        require(bytes(title).length > 0,       "Gov: title required");
        require(bytes(description).length > 0, "Gov: description required");

        campaignId = ++campaignCounter;
        (uint256 passThreshold, uint256 quorumBps, uint256 voteDuration) = _getProposalParams(proposalType);

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
            c.status         = CampaignStatus.ACTIVE;
            c.votingStart    = block.timestamp;
            c.votingDeadline = block.timestamp + voteDuration;
        }

        emit CampaignCreated(campaignId, title, uint8(proposalType), uint8(mechanism),
            msg.sender, c.snapshotBlock, c.votingDeadline);
    }

    function cancelCampaign(uint256 campaignId, string calldata reason)
        external onlyRole(CAMPAIGN_MANAGER_ROLE) whenNotPaused
    {
        Campaign storage c = campaigns[campaignId];
        require(c.status == CampaignStatus.ACTIVE || c.status == CampaignStatus.COMMIT, "Gov: cannot cancel");
        require(c.forVotes == 0 && c.againstVotes == 0 && c.abstainVotes == 0, "Gov: votes already cast");
        c.status = CampaignStatus.CANCELLED;
        emit CampaignCancelled(campaignId, reason);
    }

    // ── Voting ────────────────────────────────────────────────
    function castVote(uint256 campaignId, VoteOption option)
        external whenNotPaused nonReentrant
    {
        Campaign storage c = campaigns[campaignId];
        require(c.status == CampaignStatus.ACTIVE,   "Gov: campaign not active");
        require(block.timestamp < c.votingDeadline,   "Gov: voting ended");
        require(!hasVoted[campaignId][msg.sender],     "Gov: already voted");
        require(registry.canVote(msg.sender),          "Gov: not eligible");

        uint256 weight = getEffectiveWeight(campaignId, msg.sender);
        require(weight > 0, "Gov: no voting power at snapshot");

        _recordVote(campaignId, msg.sender, option, weight);
        emit VoteCast(campaignId, msg.sender, uint8(option), weight, uint8(c.mechanism));
    }

    function commitVote(uint256 campaignId, bytes32 voteHash)
        external whenNotPaused nonReentrant
    {
        Campaign storage c = campaigns[campaignId];
        require(c.isCommitReveal,                                   "Gov: not commit-reveal");
        require(c.status == CampaignStatus.COMMIT,                  "Gov: not in commit phase");
        require(block.timestamp < c.commitDeadline,                 "Gov: commit ended");
        require(commitments[campaignId][msg.sender] == bytes32(0),  "Gov: already committed");
        require(registry.canVote(msg.sender),                        "Gov: not eligible");
        require(voteHash != bytes32(0),                             "Gov: empty hash");

        commitments[campaignId][msg.sender] = voteHash;
        emit VoteCommitted(campaignId, msg.sender);
    }

    function revealVote(uint256 campaignId, VoteOption option, bytes32 salt)
        external whenNotPaused nonReentrant
    {
        Campaign storage c = campaigns[campaignId];
        require(c.isCommitReveal,                    "Gov: not commit-reveal");
        require(c.status == CampaignStatus.REVEAL,   "Gov: not in reveal phase");
        require(block.timestamp >= c.revealStart,    "Gov: reveal not started");
        require(block.timestamp < c.revealDeadline,  "Gov: reveal ended");
        require(!hasVoted[campaignId][msg.sender],    "Gov: already revealed");
        require(commitments[campaignId][msg.sender] != bytes32(0), "Gov: no commitment");

        // FIX LỖI #1: hash phải bao gồm msg.sender để chống replay cross-wallet
        bytes32 expected = keccak256(abi.encodePacked(uint8(option), salt, msg.sender));
        require(commitments[campaignId][msg.sender] == expected, "Gov: hash mismatch");

        uint256 weight = getEffectiveWeight(campaignId, msg.sender);
        require(weight > 0, "Gov: no voting power at snapshot");

        _recordVote(campaignId, msg.sender, option, weight);
        emit VoteRevealed(campaignId, msg.sender, uint8(option), weight);
    }

    function transitionToReveal(uint256 campaignId) external onlyRole(CAMPAIGN_MANAGER_ROLE) {
        Campaign storage c = campaigns[campaignId];
        require(c.isCommitReveal,                    "Gov: not commit-reveal");
        require(c.status == CampaignStatus.COMMIT,   "Gov: not in commit phase");
        require(block.timestamp >= c.commitDeadline, "Gov: commit not ended");
        c.status = CampaignStatus.REVEAL;
    }

    // ── Finalize ──────────────────────────────────────────────
    // FIX LỖI #2: bỏ nonReentrant — hàm này gọi Timelock rồi Timelock
    // gọi lại _finalizeExecution(), nếu nonReentrant sẽ deadlock.
    function finalizeCampaign(uint256 campaignId) external {
        Campaign storage c = campaigns[campaignId];
        require(
            c.status == CampaignStatus.ACTIVE || c.status == CampaignStatus.REVEAL,
            "Gov: cannot finalize"
        );
        require(block.timestamp >= c.votingDeadline, "Gov: voting still active");

        // Đặt TALLYING trước để chặn gọi lại trong khi đang xử lý
        c.status = CampaignStatus.TALLYING;

        bool passed = _checkResult(campaignId);

        if (!passed) {
            c.status = CampaignStatus.DEFEATED;
            _tryIssueCertificate(campaignId, false);
            emit CampaignFinalized(campaignId, false, c.forVotes, c.againstVotes, c.abstainVotes, false, 0);
            return;
        }

        if (address(timelock) != address(0)) {
            _queueToTimelock(campaignId);
        } else {
            c.status = CampaignStatus.EXECUTED;
            _tryIssueCertificate(campaignId, true);
        }

        emit CampaignFinalized(campaignId, true, c.forVotes, c.againstVotes, c.abstainVotes,
            c.timelockQueued, c.timelockEta);
    }

    // Certificate được tạo sau finalize (DEFEATED) hoặc sau EXECUTED (khi không có Timelock)
    // Khi có Timelock, certificate nên tạo trong _finalizeExecution()
    function _tryIssueCertificate(uint256 campaignId, bool passed) internal {
        if (address(votingCertificate) == address(0)) return;
        Campaign storage c = campaigns[campaignId];
        uint256 total = hstToken.getPastTotalSupply(c.snapshotBlock);
        uint256 totalVoted = c.forVotes + c.againstVotes + c.abstainVotes;
        uint256 participationBps = total > 0 ? (totalVoted * 10_000) / total : 0;
        uint256 decisive = c.forVotes + c.againstVotes;
        uint256 forBps = decisive > 0 ? (c.forVotes * 10_000) / decisive : 0;
        try votingCertificate.issueCertificate(
            campaignId, c.title, passed,
            c.forVotes, c.againstVotes, c.abstainVotes,
            participantCount[campaignId],
            c.quorumBps, participationBps, c.passThreshold, forBps,
            uint8(c.proposalType), uint8(c.mechanism), c.snapshotBlock
        ) {} catch {}
    }

    function _queueToTimelock(uint256 campaignId) internal {
        Campaign storage c = campaigns[campaignId];
        uint256 delay = _getTimelockDelay(c.proposalType);

        bytes memory callData = abi.encodeWithSignature("_finalizeExecution(uint256)", campaignId);
        bytes32 salt          = bytes32(campaignId);

        // FIX LỖI #3: nếu Timelock từ chối (vd duplicate salt) thì fallback EXECUTED
        // không nên để contract kẹt ở TALLYING
        try timelock.schedule(address(this), 0, callData, bytes32(0), salt, delay) {
            bytes32 opId = timelock.hashOperation(address(this), 0, callData, bytes32(0), salt);
            c.timelockOperationId = opId;
            c.timelockEta         = block.timestamp + delay;
            c.timelockDelay       = delay;
            c.timelockQueued      = true;
            c.status              = CampaignStatus.QUEUED;
            emit TimelockQueued(campaignId, opId, delay, c.timelockEta);
        } catch {
            c.status = CampaignStatus.EXECUTED;
        }
    }

    function checkTimelockReady(uint256 campaignId) external {
        Campaign storage c = campaigns[campaignId];
        require(c.status == CampaignStatus.QUEUED,    "Gov: not queued");
        require(block.timestamp >= c.timelockEta,     "Gov: delay not passed");
        require(timelock.isOperationReady(c.timelockOperationId), "Gov: timelock not ready");
        c.status = CampaignStatus.EXECUTABLE;
    }

    // FIX LỖI #4: executeDecision cũng bỏ nonReentrant vì cùng lý do với finalizeCampaign
    function executeDecision(uint256 campaignId) external {
        Campaign storage c = campaigns[campaignId];
        require(
            c.status == CampaignStatus.QUEUED || c.status == CampaignStatus.EXECUTABLE,
            "Gov: not ready"
        );
        require(block.timestamp >= c.timelockEta, "Gov: delay not passed");
        require(c.timelockQueued,                  "Gov: not queued on timelock");

        bytes memory callData = abi.encodeWithSignature("_finalizeExecution(uint256)", campaignId);
        timelock.execute(address(this), 0, callData, bytes32(0), bytes32(campaignId));
        emit DecisionExecuted(campaignId, msg.sender, block.timestamp);
    }

    // Chỉ Timelock được gọi — đây là điểm "quyết định có hiệu lực"
    function _finalizeExecution(uint256 campaignId) external {
        require(msg.sender == address(timelock), "Gov: only timelock");
        Campaign storage c = campaigns[campaignId];
        require(
            c.status == CampaignStatus.QUEUED || c.status == CampaignStatus.EXECUTABLE,
            "Gov: invalid status"
        );
        c.status = CampaignStatus.EXECUTED;
        _tryIssueCertificate(campaignId, true);
    }

    // ── Voting weight ─────────────────────────────────────────
    function getEffectiveWeight(uint256 campaignId, address voter) public view returns (uint256) {
        uint256 raw = hstToken.getPastVotes(voter, campaigns[campaignId].snapshotBlock);
        VotingMechanism m = campaigns[campaignId].mechanism;
        if (m == VotingMechanism.QUADRATIC) return Math.sqrt(raw);
        if (m == VotingMechanism.EQUAL)     return raw > 0 ? 1 : 0;
        return raw;
    }

    // ── Views ─────────────────────────────────────────────────
    function getCampaign(uint256 campaignId) external view returns (Campaign memory) {
        return campaigns[campaignId];
    }

    function getBallot(uint256 campaignId, address voter) external view returns (Ballot memory) {
        return ballots[campaignId][voter];
    }

    function getParticipationRate(uint256 campaignId) external view returns (uint256) {
        Campaign storage c = campaigns[campaignId];
        uint256 total = hstToken.getPastTotalSupply(c.snapshotBlock);
        if (total == 0) return 0;
        return ((c.forVotes + c.againstVotes + c.abstainVotes) * 10_000) / total;
    }

    function getTimelockInfo(uint256 campaignId) external view returns (
        bool queued, uint256 eta, uint256 delayDays, bool isReady, bytes32 operationId
    ) {
        Campaign storage c = campaigns[campaignId];
        queued      = c.timelockQueued;
        eta         = c.timelockEta;
        delayDays   = c.timelockDelay / 1 days;
        isReady     = c.timelockQueued && block.timestamp >= c.timelockEta;
        operationId = c.timelockOperationId;
    }

    function pause()   external onlyRole(SUPER_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(SUPER_ADMIN_ROLE) { _unpause(); }

    // ── Internal ──────────────────────────────────────────────
    function _getProposalParams(ProposalType pType)
        internal pure returns (uint256 passThreshold, uint256 quorumBps, uint256 voteDuration)
    {
        if (pType == ProposalType.MAJOR) return (MAJOR_PASS_BPS, MAJOR_QUORUM_BPS, MAJOR_VOTE_DAYS);
        if (pType == ProposalType.MA)    return (MA_PASS_BPS,    MA_QUORUM_BPS,    MA_VOTE_DAYS);
        return (ROUTINE_PASS_BPS, ROUTINE_QUORUM_BPS, ROUTINE_VOTE_DAYS);
    }

    function _getTimelockDelay(ProposalType pType) internal view returns (uint256) {
        if (address(timelock) == address(0)) return 0;
        if (pType == ProposalType.MAJOR) return timelock.MAJOR_DELAY();
        if (pType == ProposalType.MA)    return timelock.MA_DELAY();
        return timelock.ROUTINE_DELAY();
    }

    function _recordVote(uint256 campaignId, address voter, VoteOption option, uint256 weight) internal {
        hasVoted[campaignId][voter] = true;
        ballots[campaignId][voter]  = Ballot(option, weight, block.timestamp);
        participantCount[campaignId]++;
        Campaign storage c = campaigns[campaignId];
        if      (option == VoteOption.FOR)     c.forVotes     += weight;
        else if (option == VoteOption.AGAINST) c.againstVotes += weight;
        else                                   c.abstainVotes += weight;
    }

    function _checkResult(uint256 campaignId) internal view returns (bool) {
        Campaign storage c = campaigns[campaignId];
        uint256 total = hstToken.getPastTotalSupply(c.snapshotBlock);
        if (total == 0) return false;

        uint256 totalVoted = c.forVotes + c.againstVotes + c.abstainVotes;
        // FIX LỖI #5: dùng basis points đúng cách — quorum tính trên totalSupply tại snapshot
        if ((totalVoted * 10_000) / total < c.quorumBps) return false;

        uint256 decisive = c.forVotes + c.againstVotes;
        if (decisive == 0) return false;

        // Dùng > thay vì >= để tránh edge case tie (50% không đủ nếu threshold là 5000)
        return (c.forVotes * 10_000) / decisive > c.passThreshold;
    }
}
