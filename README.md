# **EVM Blockchain Stress Testing with Locust**

This project provides a Locust-based stress testing system for the evn blockchain. It allows for both standalone testing and distributed testing using Docker and Docker Compose.

---

## **1️⃣ Setup Configuration & Wallets**

### **Create a Configuration File**
You need a `config.json` file with network settings, contract addresses, and transaction parameters.

You can create your own or use the provided `config.json` file in the `src/` directory.

```json
{
  "network": {
    "rpc_url": "https://testnet-rpc.monad.xyz",
    "chain_id": 10143,
    "token_name": "MON"
  },
  "contracts": {
    "router": "0xfb8e1c3b833f9e67a71c859a132cf783b645e436",
    "factory": "0x733e88f248b742db6c14c0b1713af5ad7fdd59d0",
    "weth": "0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37",
    "usdc": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea"
  },
  "transactions": {
    "gas_price": 50,
    "base_gas_limit": 21000,
    "swap_gas_limit": 200000
  },
  "pairs_to_swap": [
    ["weth", "usdc"],
    ["wmon", "usdc"]
  ]
}
```

---

### **Create a Wallets File**
The system requires a `wallets.json` file with test wallets.

Each wallet should have an address and private key:
```json
[
  {
    "address": "0xYourWalletAddress1",
    "private_key": "YourPrivateKey1"
  },
  {
    "address": "0xYourWalletAddress2",
    "private_key": "YourPrivateKey2"
  }
]
```
🚨 **Important:** Do **NOT** expose this file in public repositories.

---

## **2️⃣ Save Paths in `.env`**
To make the system flexible, define environment variables in a `.env` file:

```ini
# .env file
CONFIG_FILE=/app/config.json
WALLETS_FILE=/app/wallets.json
LOCUST_TARGET_HOST=http://localhost
```

This allows you to dynamically load custom configurations and wallet files when using Docker.

---

## **3️⃣ Run the System**

### **Standalone Mode (Single Locust Instance)**
To run Locust in standalone mode, build and run the Docker container:

```bash
docker build -t monad-locust .
docker run --rm --env-file .env -p 8089:8089 monad-locust
```

🔗 Open **[http://localhost:8089](http://localhost:8089)** to access the Locust UI.

---

### **Distributed Mode (Master + Workers)**
To run Locust in distributed mode using Docker Compose:

1. **Build the Docker image:**
```bash
docker build -t monad-locust .
```

2. **Start the system with multiple workers:**
```bash
docker-compose up --scale locust-worker=5
```

📌 This will:
- Start **1 Locust Master** (UI + Controller)
- Start **5 Locust Workers** (handling requests)

🔗 Open **[http://localhost:8089](http://localhost:8089)** to control the stress test.

---

## **4️⃣ Running with Custom Configuration**
If you want to use a different configuration and wallets file, provide paths in `.env` or override them in the command:

```bash
docker run --rm -p 8089:8089 -e CONFIG_FILE=/custom/config.json -e WALLETS_FILE=/custom/wallets.json monad-locust -e LOCUST_TARGET_HOST=http://my-custom-host monad-locust
```

---

## ✅ **Summary**
| Step | Action |
|------|--------|
| **1️⃣ Create Config & Wallets** | Prepare `config.json` and `wallets.json` |
| **2️⃣ Set Environment Variables** | Add `.env` file to define paths |
| **3️⃣ Run Locust in Standalone Mode** | Use `docker run --rm --env-file .env -p 8089:8089 monad-locust` |
| **4️⃣ Run Locust in Distributed Mode** | Use `docker-compose up --scale locust-worker=5` |

Now you can stress test Monad's blockchain efficiently! 🚀

