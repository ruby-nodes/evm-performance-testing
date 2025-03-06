""" wallets utils """
import json
import logging

from web3 import Web3

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load Configuration
with open("config.json") as file:
    config = json.load(file)

# Connect to Testnet
web3 = Web3(Web3.HTTPProvider(config["network"]["rpc_url"]))

# Load Wallets
with open("wallets.json") as file:
    wallets = json.load(file)


def check_wallet_balance():
    """Check and display balance for all wallets."""
    for wallet in wallets:
        balance = web3.eth.get_balance(wallet["address"])
        logger.info(f"Wallet {Web3.to_checksum_address((wallet['address']))} "
                    f"has {web3.from_wei(balance, 'ether')} {config['network']['token_name']}")


def find_funded_wallet():
    """Find a wallet with sufficient funds (≥ 0.5.)"""
    for wallet in wallets:
        balance = web3.eth.get_balance(wallet["address"])
        if balance >= web3.to_wei(0.5, 'ether'):
            return wallet
    logger.info(f"⚠️ No funded wallet found with ≥ 0.5 {config['network']['token_name']}.")
    return None


def redistribute_tokens():
    """Distribute tokens from a funded wallet to others."""
    funded_wallet = find_funded_wallet()
    if not funded_wallet:
        return

    sender_address = funded_wallet["address"]
    sender_private_key = funded_wallet["private_key"]
    sender_balance = web3.eth.get_balance(sender_address)

    # Filter out wallets with zero balance (excluding sender)
    recipients = [w for w in wallets
                  if w["address"] != sender_address
                  and web3.eth.get_balance(w["address"]) == 0]

    if not recipients:
        logger.info("✅ No wallets require redistribution.")
        return

    gas_price = web3.to_wei(50, 'gwei')  # Static gas price for testnet
    gas_limit = 21000  # Standard gas limit for transfers
    total_gas_cost = len(recipients) * gas_price * gas_limit
    available_balance = sender_balance - total_gas_cost

    if available_balance <= 0:
        logger.info(f"⚠️ Not enough {config['network']['token_name']} to cover gas fees.")
        return

    # Distribute available token fairly
    amount_per_wallet = available_balance // len(recipients)

    logger.info(f"🔹 Redistributing {web3.from_wei(available_balance, 'ether')} "
                f"{config['network']['token_name']} to {len(recipients)} wallets.")

    for recipient in recipients:
        tx = {
            "to": recipient["address"],
            "value": amount_per_wallet,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": web3.eth.get_transaction_count(sender_address),
            "chainId": config["network"]["chain_id"],
        }

        signed_txn = web3.eth.account.sign_transaction(tx, sender_private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        logger.info(f"✅ Sent {web3.from_wei(amount_per_wallet, 'ether')} "
                    f"{config['network']['token_name']} "
                    f"to {recipient['address']} | TX: {tx_hash.hex()}")


def generate_wallets():
    """Generate 10 wallets and save them to wallets.json."""
    new_wallets = []
    for _ in range(10):
        account = web3.eth.account.create()
        new_wallets.append({"address": account.address, "private_key": account._private_key.hex()})

    with open("wallets.json", "w") as f:
        json.dump(new_wallets, f, indent=4)

    logger.info("✅ 10 Wallets Generated and Saved to wallets.json")


if __name__ == "__main__":
    generate_wallets()
    check_wallet_balance()
    redistribute_tokens()
    check_wallet_balance()  # Verify after redistribution
