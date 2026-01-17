import sys
import time
from web3 import Web3
from eth_utils import keccak, to_hex
from web3._utils.events import get_event_data
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Persistent session for HTTP requests
session = requests.Session()
token_address = "0x79bbf4508b1391af3a0f4b30bb5fc4aa9ab0e07c"
pool_address = "0x825c43f12b4cfb9a858ede9400adb0240d8e3f44"

# -------------------------------------------------------------------
# 1. Configuration & Connection
# -------------------------------------------------------------------
rpc_url = "https://rpc.soniclabs.com"  # Adjust if needed
web3 = Web3(Web3.HTTPProvider(rpc_url))
if not web3.is_connected():
    raise Exception("Failed to connect to the node")

# Your account details
account_address = Web3.to_checksum_address("")
private_key = ""  # Replace with your private key

# -------------------------------------------------------------------
# 2. Combined ABI for addLiquidity & removeLiquidity (Non‑Native)
# -------------------------------------------------------------------
combined_abi = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "contract IERC20", "name": "tokenX", "type": "address"},
                    {"internalType": "contract IERC20", "name": "tokenY", "type": "address"},
                    {"internalType": "uint256", "name": "binStep", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountX", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountY", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountXMin", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountYMin", "type": "uint256"},
                    {"internalType": "uint256", "name": "activeIdDesired", "type": "uint256"},
                    {"internalType": "uint256", "name": "idSlippage", "type": "uint256"},
                    {"internalType": "int256[]", "name": "deltaIds", "type": "int256[]"},
                    {"internalType": "uint256[]", "name": "distributionX", "type": "uint256[]"},
                    {"internalType": "uint256[]", "name": "distributionY", "type": "uint256[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "address", "name": "refundTo", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "internalType": "struct ILBRouter.LiquidityParameters",
                "name": "liquidityParameters",
                "type": "tuple"
            }
        ],
        "name": "addLiquidity",
        "outputs": [
            {"internalType": "uint256", "name": "amountXAdded", "type": "uint256"},
            {"internalType": "uint256", "name": "amountYAdded", "type": "uint256"},
            {"internalType": "uint256", "name": "amountXLeft", "type": "uint256"},
            {"internalType": "uint256", "name": "amountYLeft", "type": "uint256"},
            {"internalType": "uint256[]", "name": "depositIds", "type": "uint256[]"},
            {"internalType": "uint256[]", "name": "liquidityMinted", "type": "uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenX", "type": "address"},
            {"internalType": "address", "name": "tokenY", "type": "address"},
            {"internalType": "uint16", "name": "binStep", "type": "uint16"},
            {"internalType": "uint256", "name": "amountXMin", "type": "uint256"},
            {"internalType": "uint256", "name": "amountYMin", "type": "uint256"},
            {"internalType": "uint256[]", "name": "ids", "type": "uint256[]"},
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "removeLiquidity",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

POOL_CONTRACT_ADDRESS = Web3.to_checksum_address("0x67803fe6d76409640efDC9b7ABcD2c6c2E7cBa48")
pool_contract = web3.eth.contract(address=POOL_CONTRACT_ADDRESS, abi=combined_abi)

# -------------------------------------------------------------------
# 3. Token Contracts & Minimal ERC‑20 ABI
# -------------------------------------------------------------------
# Replace these with the actual token addresses
tokenX_address = Web3.to_checksum_address("0x79bbf4508b1391af3a0f4b30bb5fc4aa9ab0e07c")
tokenY_address = Web3.to_checksum_address("0x29219dd400f2Bf60E5a23d13Be72B486D4038894")

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

tokenX_contract = web3.eth.contract(address=tokenX_address, abi=ERC20_ABI)
tokenY_contract = web3.eth.contract(address=tokenY_address, abi=ERC20_ABI)

# -------------------------------------------------------------------
# 4. ERC-1155 Event Decoding
# -------------------------------------------------------------------
def decode_transaction_logs(tx_hash):
    """
    Decodes and prints all logs and their data from a transaction receipt.
    """
    try:
        # Fetch the transaction receipt
        receipt = web3.eth.get_transaction_receipt(tx_hash)
        if receipt is None:
            logging.error("Transaction receipt not found.")
            return None

        # Print raw logs for debugging
        logs = receipt.get("logs", [])
        logging.info(f"Raw logs in receipt: {logs}")

        # Decode each log
        for log in logs:
            # Extract topics and data
            topics = log.get("topics", [])
            data = log.get("data", "")

            # Convert topics to hex
            topics_hex = [Web3.to_hex(topic) for topic in topics]
            logging.info(f"Topics: {topics_hex}")
            logging.info(f"Data: {data}")

            # Try to decode the log using common event ABIs
            if topics_hex:
                event_signature = topics_hex[0]
                logging.info(f"Event signature: {event_signature}")

                # Try to decode as ERC-20 Transfer event
                if event_signature == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef":
                    event_abi = {
                        "anonymous": False,
                        "inputs": [
                            {"indexed": True, "name": "from", "type": "address"},
                            {"indexed": True, "name": "to", "type": "address"},
                            {"indexed": False, "name": "value", "type": "uint256"}
                        ],
                        "name": "Transfer",
                        "type": "event"
                    }
                    try:
                        decoded_event = get_event_data(web3.codec, event_abi, log)
                        logging.info(f"Decoded ERC-20 Transfer event: {decoded_event}")
                    except Exception as e:
                        logging.error(f"Error decoding ERC-20 Transfer event: {e}")

                # Try to decode as ERC-1155 TransferSingle event
                elif event_signature == "0xc3d58168c5c52e9b77f9dc59a2ec214a7b449e537c0c99e92ed8d2605f3d19b":
                    event_abi = {
                        "anonymous": False,
                        "inputs": [
                            {"indexed": True, "name": "operator", "type": "address"},
                            {"indexed": True, "name": "from", "type": "address"},
                            {"indexed": True, "name": "to", "type": "address"},
                            {"indexed": False, "name": "id", "type": "uint256"},
                            {"indexed": False, "name": "value", "type": "uint256"}
                        ],
                        "name": "TransferSingle",
                        "type": "event"
                    }
                    try:
                        decoded_event = get_event_data(web3.codec, event_abi, log)
                        logging.info(f"Decoded ERC-1155 TransferSingle event: {decoded_event}")
                        return decoded_event
                    except Exception as e:
                        logging.error(f"Error decoding ERC-1155 TransferSingle event: {e}")

                # Try to decode as ERC-1155 TransferBatch event
                elif event_signature == "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb":
                    event_abi = {
                        "anonymous": False,
                        "inputs": [
                            {"indexed": True, "name": "operator", "type": "address"},
                            {"indexed": True, "name": "from", "type": "address"},
                            {"indexed": True, "name": "to", "type": "address"},
                            {"indexed": False, "name": "ids", "type": "uint256[]"},
                            {"indexed": False, "name": "values", "type": "uint256[]"}
                        ],
                        "name": "TransferBatch",
                        "type": "event"
                    }
                    try:
                        decoded_event = get_event_data(web3.codec, event_abi, log)
                        logging.info(f"Decoded ERC-1155 TransferBatch event: {decoded_event}")
                        return decoded_event
                    except Exception as e:
                        logging.error(f"Error decoding ERC-1155 TransferBatch event: {e}")

    except Exception as e:
        logging.error(f"Error decoding transaction logs: {e}")
        return None
BIN_STEP = 4  # 100 bps

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
def extract_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def get_token_price_in_pool(token_address, pool_address):
    """
    Fetches the USD price from Dexscreener for the specified token in a given pool.
    """
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        logging.info(f"Querying Dexscreener for token {token_address}")
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            logging.info(f"No pairs found for token {token_address}")
            return None
        
        # Search for the pair with the matching pool (pair) address
        target_pair = next(
            (pair for pair in pairs if pair.get("pairAddress", "").lower() == pool_address.lower()),
            None
        )
        
        if target_pair is None:
            logging.info(f"Pool with address {pool_address} not found for token {token_address}")
            return None
        
        # Extract the USD price from the matched pool
        price_raw = target_pair.get("priceUsd")
        price = extract_float(price_raw)
        if price == 0:
            logging.info(f"No valid priceUsd found for token {token_address} in pool {pool_address}")
            return None
        
        return price
    except Exception as e:
        logging.error(f"Error querying Dexscreener for token {token_address} in pool {pool_address}: {e}")
        return None

def calculate_price_range(current_price, bin_step, is_token_x):
    """
    Calculates the price range based on the current price and bin step.
    Returns a tuple of (min_price, max_price) for the three-bin range.
    """
    bin_step_factor = bin_step / 10000  # Convert bps to a factor (e.g., 100 bps = 0.01)
    
    if is_token_x:
        # For Token X: current price and next two higher bins
        min_price = current_price
        max_price = current_price
    else:
        # For Token Y: current price and next two lower bins
        min_price = current_price 
        max_price = current_price
    
    return (min_price, max_price)

def monitor_price_and_remove_liquidity(deposit_ids, liquidity_minted, liquidity_parameters, initial_price, is_token_x):
    """
    Monitors the price and removes liquidity if it moves out of the specified three-bin range.
    """
    # Calculate the price range based on the initial price and bin step
    min_price, max_price = calculate_price_range(initial_price, BIN_STEP, is_token_x)
    logging.info(f"Price range - Min: {min_price}, Max: {max_price}")

    while True:
        # Fetch the current price
        current_price = get_token_price_in_pool(token_address, pool_address)
        if current_price is None:
            logging.error("Failed to fetch current price. Retrying in 1 minute...")
            time.sleep(60)
            continue

        logging.info(f"Current price: {current_price}")

        # Check if price is out of range
        if current_price < min_price or current_price > max_price:
            logging.info("Price moved out of range. Removing liquidity...")
            remove_liquidity(deposit_ids, liquidity_minted, liquidity_parameters)
            break

        # Wait for 1 minute before checking the price again
        time.sleep(60)


def remove_liquidity(deposit_ids, liquidity_minted, liquidity_parameters):
    """
    Removes liquidity from the pool.
    """
    try:
        nonce = web3.eth.get_transaction_count(account_address)
        if liquidity_parameters["amountX"] > liquidity_parameters["amountY"]:
            remove_amountXMin = 0
            remove_amountYMin = 0
        else:
            remove_amountXMin = 0
            remove_amountYMin = 0
        new_deadline = int(time.time()) + 15 * 60

        remove_tx = pool_contract.functions.removeLiquidity(
            liquidity_parameters["tokenX"],
            liquidity_parameters["tokenY"],
            liquidity_parameters["binStep"],
            remove_amountXMin,
            remove_amountYMin,
            deposit_ids,
            liquidity_minted,
            account_address,
            new_deadline
        ).build_transaction({
            "from": account_address,
            "gas": 3000000,
            "gasPrice": web3.to_wei("100", "gwei"),
            "nonce": nonce,
        })
        signed_remove_tx = web3.eth.account.sign_transaction(remove_tx, private_key=private_key)
        remove_tx_hash = web3.eth.send_raw_transaction(signed_remove_tx.raw_transaction)

        # Fixed logging statement
        logging.info(f"Remove Liquidity Transaction sent. Hash: {remove_tx_hash.hex()}")

        remove_receipt = web3.eth.wait_for_transaction_receipt(remove_tx_hash)
        logging.info(f"Remove Liquidity Transaction Receipt: {remove_receipt}")
    except Exception as e:
        logging.error(f"Error in removeLiquidity: {e}")
        sys.exit(1)


# -------------------------------------------------------------------
# 5. Main Flow: Add then Remove Liquidity
# -------------------------------------------------------------------
def main():
    # Check token balances
    try:
        balance_tokenX = tokenX_contract.functions.balanceOf(account_address).call()
        balance_tokenY = tokenY_contract.functions.balanceOf(account_address).call()
    except Exception as e:
        print("Error fetching token balances:", e)
        sys.exit(1)

    print("TokenX balance:", balance_tokenX)
    print("TokenY balance:", balance_tokenY)
    if balance_tokenX == 0 and balance_tokenY == 0:
        print("Both token balances are 0. Exiting.")
        sys.exit(1)

    # Choose the token with the higher balance
    if balance_tokenX >= balance_tokenY:
        amountX = balance_tokenX
        amountY = 0
        deltaIds = [0]
        distributionX = [10**18]  # 100% allocation (in 1e18 scale)
        distributionY = [0]
    else:
        amountX = 0
        amountY = balance_tokenY
        deltaIds = [0]
        distributionX = [0]
        distributionY = [10**18]

    # Common liquidity parameters (adjust as needed)
    binStep = 4
    amountXMin = 0
    amountYMin = 0
    activeIdDesired = 8324368  # Adjust per protocol requirements
    idSlippage = 400
    to_address = account_address
    refundTo_address = account_address
    deadline = int(time.time()) + 15 * 60  # current time + 15 minutes

    liquidity_parameters = {
        "tokenX": tokenX_address,
        "tokenY": tokenY_address,
        "binStep": binStep,
        "amountX": amountX,
        "amountY": amountY,
        "amountXMin": amountXMin,
        "amountYMin": amountYMin,
        "activeIdDesired": activeIdDesired,
        "idSlippage": idSlippage,
        "deltaIds": deltaIds,
        "distributionX": distributionX,
        "distributionY": distributionY,
        "to": to_address,
        "refundTo": refundTo_address,
        "deadline": deadline,
    }

    # Add liquidity
        # Add Liquidity
    try:
        nonce = web3.eth.get_transaction_count(account_address)
        add_tx = pool_contract.functions.addLiquidity(liquidity_parameters).build_transaction({
            "from": account_address,
            "gas": 2000000,
            "gasPrice": web3.to_wei("60", "gwei"),
            "nonce": nonce,
        })
        signed_add_tx = web3.eth.account.sign_transaction(add_tx, private_key=private_key)
        add_tx_hash = web3.eth.send_raw_transaction(signed_add_tx.raw_transaction)
        print("Add Liquidity Transaction sent. Hash:", add_tx_hash.hex())

        add_receipt = web3.eth.wait_for_transaction_receipt(add_tx_hash)
        print("Transaction Receipt:", add_receipt)
        print("Transaction Status:", add_receipt.status)
        print("Logs in Receipt:", add_receipt.logs)

        if add_receipt.status == 0:
            print("Transaction failed. Check gas limit, gas price, or contract logic.")
            sys.exit(1)

        # Decode transaction logs to extract deposit IDs and liquidity minted
        decoded_event = decode_transaction_logs(add_tx_hash)
        if decoded_event:
            if "id" in decoded_event["args"]:
                deposit_ids = [decoded_event["args"]["id"]]
                liquidity_minted = [decoded_event["args"]["value"]]
            elif "ids" in decoded_event["args"]:
                deposit_ids = decoded_event["args"]["ids"]
                liquidity_minted = decoded_event["args"]["values"]
            else:
                print("Failed to extract deposit IDs and liquidity minted from the decoded event.")
                sys.exit(1)
        else:
            print("Failed to decode transaction logs.")
            sys.exit(1)

        print("Decoded LiquidityAdded event:")
        print("Deposit IDs:", deposit_ids)
        print("Liquidity Minted:", liquidity_minted)

    except Exception as e:
        print(f"Error in addLiquidity: {e}")
        sys.exit(1)

    # Decode transaction logs to extract deposit IDs and liquidity minted
    decoded_event = decode_transaction_logs(add_tx_hash)
    if decoded_event:
        if "id" in decoded_event["args"]:
            deposit_ids = [decoded_event["args"]["id"]]
            liquidity_minted = [decoded_event["args"]["value"]]
        elif "ids" in decoded_event["args"]:
            deposit_ids = decoded_event["args"]["ids"]
            liquidity_minted = decoded_event["args"]["values"]
        else:
            print("Failed to extract deposit IDs and liquidity minted from the decoded event.")
            sys.exit(1)
    else:
        print("Failed to decode transaction logs.")
        sys.exit(1)

    print("Decoded LiquidityAdded event:")
    print("Deposit IDs:", deposit_ids)
    print("Liquidity Minted:", liquidity_minted)

    # Remove liquidity
    initial_price = get_token_price_in_pool(token_address, pool_address)
    if initial_price is None:
        logging.error("Failed to fetch initial price. Exiting.")
        sys.exit(1)

    # Determine if liquidity was added with Token X or Token Y
    is_token_x = liquidity_parameters["amountX"] > liquidity_parameters["amountY"]

    # Start monitoring the price
    monitor_price_and_remove_liquidity(deposit_ids, liquidity_minted, liquidity_parameters, initial_price, is_token_x)


if __name__ == "__main__":
    while True:
        main()
        time.sleep(2)