require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/**
 * hardhat.config.js
 * ══════════════════════════════════════════════════════════════
 * POLYGON AMOY TESTNET — Cấu hình triển khai thực tế
 * ══════════════════════════════════════════════════════════════
 *
 * Để deploy lên Amoy:
 *   1. Tạo file .env (xem .env.example)
 *   2. Lấy MATIC test miễn phí tại: https://faucet.polygon.technology
 *   3. Chạy: npx hardhat run scripts/setup_demo.js --network amoy
 *
 * Sau khi deploy, contract có thể xem tại:
 *   https://amoy.polygonscan.com/address/<CONTRACT_ADDRESS>
 */

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
    },
  },

  networks: {
    // ── Ganache UI (local — dùng để dev) ──────────────────────
    ganache: {
      url:      "http://127.0.0.1:7545",
      chainId:  1337,
      accounts: process.env.GANACHE_PRIVATE_KEYS
        ? process.env.GANACHE_PRIVATE_KEYS.split(",").map(k => k.trim())
        : [],
    },

    // ── Hardhat in-process (dùng cho test) ────────────────────
    hardhat: {
      chainId: 31337,
      mining:  { auto: true, interval: 0 },
      accounts: { count: 10, accountsBalance: "10000000000000000000000" },
    },

    // ── Polygon Amoy Testnet ───────────────────────────────────
    // ChainID: 80002
    // Explorer: https://amoy.polygonscan.com
    // Faucet  : https://faucet.polygon.technology
    // RPC     : https://rpc-amoy.polygon.technology
    amoy: {
      url:     process.env.AMOY_RPC_URL || "https://rpc-amoy.polygon.technology",
      chainId: 80002,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
      gasPrice: "auto",
      // Timeout cao hơn vì testnet đôi khi chậm
      timeout: 120000,
    },
  },

  // ── Verify contract trên Polygonscan ──────────────────────────
  // Sau khi deploy, chạy:
  //   npx hardhat verify --network amoy <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>
  etherscan: {
    apiKey: {
      polygonAmoy: process.env.POLYGONSCAN_API_KEY || "",
    },
    customChains: [
      {
        network: "polygonAmoy",
        chainId: 80002,
        urls: {
          apiURL:     "https://api-amoy.polygonscan.com/api",
          browserURL: "https://amoy.polygonscan.com",
        },
      },
    ],
  },

  gasReporter: {
    enabled:       process.env.REPORT_GAS === "true",
    currency:      "USD",
    token:         "MATIC",
    outputFile:    "gas-report.txt",
    noColors:      true,
  },

  paths: {
    sources:   "./contracts",
    tests:     "./test",
    cache:     "./cache",
    artifacts: "./artifacts",
  },
};
