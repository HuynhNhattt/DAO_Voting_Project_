require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true,
    },
  },

  networks: {
    //Ganache UI (port 7545)
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      accounts: process.env.GANACHE_PRIVATE_KEYS
        ? process.env.GANACHE_PRIVATE_KEYS.split(",").map((k) => k.trim())
        : [],
      gas: "auto",
      gasPrice: "auto",
    },

    //Ganache CLI (port 8545)
    ganache_cli: {
      url: "http://127.0.0.1:8545",
      chainId: 1337,
      accounts: process.env.GANACHE_PRIVATE_KEYS
        ? process.env.GANACHE_PRIVATE_KEYS.split(",").map((k) => k.trim())
        : [],
    },

    //Hardhat in-process (dùng cho test)
    hardhat: {
      chainId: 31337,
      mining: {
        auto: true,
        interval: 0,
      },
      accounts: {
        count: 10,
        accountsBalance: "10000000000000000000000", // 10,000 ETH mỗi account
      },
    },

    //Polygon Amoy Testnet (Phase 5)
    amoy: {
      url: process.env.AMOY_RPC_URL || "https://rpc-amoy.polygon.technology",
      chainId: 80002,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
  },

  //Gas reporting
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
    gasPrice: 20,
    token: "ETH",
    coinmarketcap: process.env.COINMARKETCAP_API_KEY || "",
    outputFile: "gas-report.txt",
    noColors: true,
  },

  //Sourcify / Etherscan verification
  etherscan: {
    apiKey: {
      polygonAmoy: process.env.POLYGONSCAN_API_KEY || "",
    },
    customChains: [
      {
        network: "polygonAmoy",
        chainId: 80002,
        urls: {
          apiURL: "https://api-amoy.polygonscan.com/api",
          browserURL: "https://amoy.polygonscan.com",
        },
      },
    ],
  },

  //Coverage
  solcover: {
    skipFiles: ["mocks/"],
  },

  //Paths
  paths: {
    sources:   "./contracts",
    tests:     "./test",
    cache:     "./cache",
    artifacts: "./artifacts",
  },
};
