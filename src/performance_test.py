""" Simple stress test for evm compatible bc"""
import json
import logging
import os
import random
import sys
import time
from pathlib import Path

from locust import HttpUser, task, between
from web3 import Web3

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define the base directory dynamically
BASE_DIR = Path(__file__).resolve().parent
ABI_DIR = BASE_DIR / "abi"

# Resolve paths
wallets_path = Path(os.getenv("WALLETS_FILE", BASE_DIR / "wallets.json"))
config_path = Path(os.getenv("CONFIG_FILE", BASE_DIR / "config.json"))
loctus_host = os.getenv("LOCUST_TARGET_HOST", "http://localhost")

# Load all required files in a single try-except block
try:
    with open(config_path, encoding="utf-8") as file:
        config = json.load(file)
    logger.info("✅ Loaded config")

    with open(wallets_path, encoding="utf-8") as file:
        wallets = json.load(file)
    logger.info("✅ Loaded wallets")

    with open(ABI_DIR / "UniswapV2Factory.json", encoding="utf-8") as f:
        factory_abi = json.load(f)
    logger.info("✅ Loaded UniswapV2Factory ABI")

    with open(ABI_DIR / "UniswapV2Router02.json", encoding="utf-8") as f:
        router_abi = json.load(f)
    logger.info("✅ Loaded UniswapV2Router02 ABI")

    with open(ABI_DIR / "UniswapV2Pair.json", encoding="utf-8") as f:
        pair_abi = json.load(f)
    logger.info("✅ Loaded UniswapV2Pair ABI")

except Exception as e:
    logger.error(f"❌ ERROR: Failed to load required files: {e}")
    sys.exit(1)


# Convert contract addresses to checksum format
def get_checksum_address(address):
    """Convert an Ethereum address to checksum format."""
    return Web3.to_checksum_address(address)


# Connect to Blockchain
web3 = Web3(Web3.HTTPProvider(config["network"]["rpc_url"]))

# Initialize Uniswap Contracts
factory_contract = web3.eth.contract(
    address=get_checksum_address(config["contracts"]["factory"]), abi=factory_abi
)
uniswap_router = web3.eth.contract(
    address=get_checksum_address(config["contracts"]["router"]), abi=router_abi
)


def get_pair_address(token_a, token_b):
    """Fetch the pair address for two tokens and check liquidity."""
    try:
        pair_address = factory_contract.functions.getPair(
            get_checksum_address(token_a),
            get_checksum_address(token_b)
        ).call()
        if pair_address == "0x0000000000000000000000000000000000000000":
            logger.warning(f"🚨 Pair {token_a} - {token_b} does not exist!")
            return None

        logger.info(f"✅ Found Pair at: {pair_address}")

        # Initialize Pair Contract
        pair_contract = web3.eth.contract(address=pair_address, abi=pair_abi)
        reserves = pair_contract.functions.getReserves().call()

        # Ensure liquidity exists
        if reserves[0] == 0 or reserves[1] == 0:
            logger.warning(f"🚨 Pair {token_a} - {token_b} has NO liquidity!")
            return None

        logger.info(f"✅ Pair {token_a} - {token_b} has liquidity. Reserves: {reserves}")
        return pair_address
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        return None


def get_token_balance(wallet_address, token_address):
    """Check balance of a token for a wallet."""
    token_contract = web3.eth.contract(address=get_checksum_address(token_address), abi=pair_abi)
    try:
        balance = token_contract.functions.balanceOf(wallet_address).call()
        return balance
    except Exception as e:
        logger.error(f"❌ ERROR fetching balance for {token_address}: {e}")
        return 0


class BlockchainUser(HttpUser):
    """ User definition """
    host = loctus_host  # Dummy value (Locust requires this)
    wait_time = between(1, 5)  # Random wait time between tasks

    def on_start(self):
        """Assign a random wallet to each user and fetch initial balance."""
        # pylint: disable=attribute-defined-outside-init
        self.wallet = random.choice(wallets)
        self.address = self.wallet["address"]
        self.private_key = self.wallet["private_key"]
        self.update_wallet_status()

        logger.info(f"🔹 Wallet {self.address} "
                    f"has {web3.from_wei(self.balance, 'ether')} "
                    f"{config['network']['token_name']} available")

    def update_wallet_status(self):
        """Update nonce and balance dynamically."""
        # pylint: disable=attribute-defined-outside-init
        self.nonce = web3.eth.get_transaction_count(self.address)
        self.balance = web3.eth.get_balance(self.address)

    def sign_and_send(self, tx, name):
        """Sign and send the transaction, handling errors and logging to Locust."""
        signed_txn = web3.eth.account.sign_transaction(tx, self.private_key)
        start_time = time.perf_counter()

        try:
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            latency = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds

            # Update nonce and balance after transaction
            self.nonce += 1
            self.update_wallet_status()

            logger.info(f"✅ Transaction {tx_hash.hex()} confirmed in {latency:.2f}ms")

            # Log success in Locust
            self.environment.events.request.fire(
                request_type="Blockchain",
                name=name,
                response_time=latency,
                response_length=len(str(receipt)),
                exception=None,
            )

        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
            logger.error(f"❌ Error in {name}: {str(e)}")

            # Log failure in Locust
            self.environment.events.request.fire(
                request_type="Blockchain",
                name=name,
                response_time=latency,
                response_length=0,
                exception=e,
            )

    def get_random_recipient(self):
        """Select a random wallet with balance > 0."""
        recipients = [w for w in wallets
                      if w["address"] != self.address
                      and web3.eth.get_balance(w["address"]) > 0]
        if not recipients:
            logger.warning("⚠️ No eligible recipient found.")
            return None
        return random.choice(recipients)["address"]

    @task(1)
    def simple_transaction(self):
        """Send a simple token transfer."""
        if self.balance == 0:
            print(f"⚠️ Wallet {self.address} has zero balance. Skipping transaction.")
            return

        recipient = self.get_random_recipient()
        if recipient is None:
            return

        gas_price = web3.to_wei(config['transactions']['gas_price'], 'gwei')
        gas_limit = config['transactions']['base_gas_limit']
        total_gas_cost = gas_price * gas_limit
        available_balance = self.balance - total_gas_cost

        if available_balance <= 0:
            logger.warning(f"⚠️ Not enough {config['network']['token_name']} to cover gas fees.")
            return

        amount = available_balance // 2  # Send half
        tx = {
            "to": recipient,
            "value": amount,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": web3.eth.get_transaction_count(self.address),
            "chainId": config["network"]["chain_id"],
        }

        self.sign_and_send(tx, f"Simple {config['network']['token_name']} Transfer")

    @task(2)
    def swap_tokens(self):
        """Swap tokens dynamically based on config settings."""
        for pair in config["pairs_to_swap"]:
            token_a = config["contracts"][pair[0]]
            token_b = config["contracts"][pair[1]]

            if self.balance == 0:
                logger.warning(f"⚠️ Wallet {self.address} has zero balance. Skipping swap.")
                return

            # Ensure the pair exists and has liquidity
            pair_address = get_pair_address(token_a, token_b)
            if not pair_address:
                return

            # Check if wallet has enough TokenA to swap
            token_a_balance = get_token_balance(self.address, token_a)
            if token_a_balance == 0:
                logger.warning(f"⚠️ Wallet {self.address} has no {pair[0]} to swap.")
                return

            # Define transaction parameters
            amount_in = min(
                token_a_balance,
                web3.to_wei(random.uniform(0.001, 0.005), "ether")
            )  # Swap within limits
            gas_price = web3.to_wei(config['transactions']['gas_price'], 'gwei')
            gas_limit = config['transactions']['swap_gas_limit']
            deadline = int(time.time()) + 300  # 5 min deadline

            total_gas_cost = gas_price * gas_limit
            if self.balance <= total_gas_cost:
                logger.warning(f"⚠️ Not enough {config['network']['token_name']} "
                               f"to cover swap gas fees.")
                return

            path = [token_a, token_b]
            tx = uniswap_router.functions.swapExactTokensForTokens(
                amount_in,
                0,  # Minimum amount out (set to 0 for now, ideally should be slippage adjusted)
                path,
                self.address,
                deadline
            ).build_transaction({
                "from": self.address,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": web3.eth.get_transaction_count(self.address),
                "chainId": config["network"]["chain_id"],
            })

            self.sign_and_send(tx, f"Swap {pair[0]} for {pair[1]}")
