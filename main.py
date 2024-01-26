import json
import random
import re
import time
import ast
import requests
from eth_account.messages import encode_defunct
from eth_typing import HexStr
from eth_utils import remove_0x_prefix
from fake_useragent import UserAgent
from loguru import logger
from web3 import Web3
from typing import Union
import telebot

from settings import ALTLAYER_CLAIM_CONTRACT, ETH_RPC, MAX_GWEI, ALTLAYER_TOKEN_CONTRACT, SLEEP_BETWEEN_ACCOUNTS, \
    STR_DONE, STR_CANCEL, TG_TOKEN, TG_ID


def decimal_to_int(qty, decimal):
    return float(qty / 10 ** decimal)


def get_claim_transaction_details(address):
    ua = UserAgent()
    headers = {
        "accept": "text/x-component",
        "accept-language": "en-US,en;q=0.9,ru;q=0.8",
        "content-type": "text/plain;charset=UTF-8",
        "next-action": "6817e8f24aae7e8aed1d5226e9b368ab8c1ded5d",
        "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(homePage)%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
        "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        'user-agent': ua.random,
        "Referer": 'https://airdrop.altlayer.io/',
        "Origin": 'https://airdrop.altlayer.io/'
    }

    while True:
        try:
            response = requests.post('https://airdrop.altlayer.io/', data=json.dumps([address]), headers=headers)
            if response.status_code != 200:
                raise Exception(f'received non-200 code - {response.status_code}')
            amount_match = re.search(r'"amount":"([^"]+)"', response.text)
            proof_match = re.search(r'"proof":\s*\[([^]]+)]', response.text)
            if not proof_match or not amount_match:
                raise Exception(f"[{address}] not eligible")
            amount = amount_match.group(1)
            proof = proof_match.group(1)
            proof = f'[{proof}]'
            list_proof = ast.literal_eval(proof)
            return int(amount), list_proof

        except Exception as e:
            reason = str(e)
            logger.error(e)
            if "not eligible" in reason:
                raise e


def to_bytes(data: Union[bytes, HexStr]) -> bytes:
    if isinstance(data, bytes):
        return data
    return bytes.fromhex(remove_0x_prefix(data))


def claim():
    contract_address = Web3.to_checksum_address(ALTLAYER_CLAIM_CONTRACT)
    with open('data/abi.json', 'r') as f:
        abi = json.load(f)

    for private_key in private_keys:
        recipient = RECIPIENTS_WALLETS[private_key]
        tg_messages = []

        web3 = Web3(Web3.HTTPProvider(ETH_RPC))
        contract = web3.eth.contract(address=contract_address, abi=abi)
        account = web3.eth.account.from_key(private_key=private_key)

        module_str = f'{account.address} | ALT claim'

        try:
            try:
                amount, proof = get_claim_transaction_details(account.address)
                human_amount = decimal_to_int(amount, 18)
                module_str = f'{account.address} | {human_amount} ALT claim'
                logger.info(f"[{account.address}] claiming {human_amount} ALT")
            except Exception as e:
                continue
            msg = "By signing this message, you confirm and agree that:\n\n" \
                  "1. You do not reside in, are citizens of, are located in the United States of America or Canada, the People's Republic of China, or countries which are the subject of any sanctions administered or enforced by any country or government or international authority, including without limitation Cuba, North Korea, Timor-Leste, Cambodia, Republic of the Union of Myanmar, Lao People's Democratic Republic, Tanzania, Pakistan, Uganda, Mali, Afghanistan, Albania, Angola, Botswana, Chad, Central African Republic, Eritrea, the Republic of Guinea, Guinea-Bissau, Somalia, Zimbabwe, Democratic Republic of the Congo, Republic of the Congo, Ethiopia, Malawi, Mozambique, Madagascar, Crimea, Kyrgyzstan, Haiti, Bosnia and Herzegovina, Uzbekistan, Turkmenistan, Burundi, South Sudan, Sudan (north), Sudan (Darfur), Nicaragua, Vanuatu, the Republic of North Macedonia, the Lebanese Republic, Bahamas, Kosovo, Iran, Iraq, Liberia, Libya, Syrian Arab Republic, Tajikistan, Uzbekistan, Yemen, Belarus, Bolivia, Venezuela, the regions of Crimea, Donetsk, Kherson, Zaporizhzhia or Luhansk.\n\n" \
                  '2. You are not the subject of economic or trade sanctions administered or enforced by any governmental authority or otherwise designated on any list of prohibited or restricted parties (including the list maintained by the Office of Foreign Assets Control of the U.S. Department of the Treasury) (collectively, "Sanctioned Person").\n\n' \
                  '3. You do not intend to transact with any Restricted Person or Sanctioned Person; and\n\n' \
                  '4. You do not, and will not, use a VPN or any other privacy or anonymization tools or techniques to circumvent, or attempt to circumvent, any restrictions that apply to the Services.\n\n' \
                  "5. You have read our disclaimers: https://files.altlayer.io/tokenTnC.pdf and https://files.altlayer.io/airdrop_claim_ui_disclaimer.pdf in full."

            message_encoded = encode_defunct(text=msg)

            signed_message = account.sign_message(message_encoded)
            v = signed_message.v
            r = signed_message.r
            s = signed_message.s

            merkle_proof = []
            for p in proof:
                merkle_proof.append(to_bytes(p))

            wait_gas()

            transaction = contract.functions.claim(
                amount, merkle_proof, v, web3.to_bytes(r), web3.to_bytes(s)
            ).build_transaction(
                {
                    "chainId": web3.eth.chain_id,
                    "from": account.address,
                    "nonce": web3.eth.get_transaction_count(account.address),
                }
            )

            delta_range = [1.02, 1.05]
            delta = random.uniform(*delta_range)

            transaction['maxFeePerGas'] = int(transaction['maxFeePerGas'] * delta)
            transaction['maxPriorityFeePerGas'] = int(transaction['maxPriorityFeePerGas'] * delta)

            signed = account.sign_transaction(transaction)
            tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
            status = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=240).status

            if status == 1:
                logger.success(f'https://etherscan.io/tx/{tx_hash.hex()}')
                tg_messages.append(f'{STR_DONE} {module_str}\nhttps://etherscan.io/tx/{tx_hash.hex()}')
                logger.info(f'will now transfer to specified recipient address - {recipient}')
                transfer(account, recipient, amount, tg_messages)
            else:
                raise Exception(f'claim ALT - transaction has failed')
        except Exception as e:
            logger.error(e)
            tg_messages.append(f'{STR_CANCEL}{module_str} | {e}')

        send_msg(tg_messages)
        time.sleep(random.randint(*SLEEP_BETWEEN_ACCOUNTS))

def send_msg(messages):
    try:
        if messages and TG_ID and TG_TOKEN:
            messages.insert(0, 'ALT CLAIM & SEND')
            str_send = '\n'.join(messages)
            bot = telebot.TeleBot(TG_TOKEN)
            bot.send_message(TG_ID, str_send, parse_mode='html')

    except Exception as error:
        logger.error(error)


def transfer(account, recipient, amount, tg_messages):
    with open('data/erc20.json', "r") as file:
        abi = json.load(file)

    web3 = Web3(Web3.HTTPProvider(ETH_RPC))

    token_address = Web3.to_checksum_address(ALTLAYER_TOKEN_CONTRACT)
    token_contract = web3.eth.contract(token_address, abi=abi)

    module_str = f'{account.address} | {decimal_to_int(amount, 18)} ALT transfer => {recipient}'
    wait_gas()
    try:
        contract_txn = token_contract.functions.transfer(
            Web3.to_checksum_address(recipient),
            amount
        ).build_transaction(
            {
                'from': account.address,
                'chainId': web3.eth.chain_id,
                'nonce': web3.eth.get_transaction_count(account.address),
            }
        )
        delta_range = [1.02, 1.05]
        delta = random.uniform(*delta_range)

        contract_txn['maxFeePerGas'] = int(contract_txn['maxFeePerGas'] * delta)
        contract_txn['maxPriorityFeePerGas'] = int(contract_txn['maxPriorityFeePerGas'] * delta)

        signed = account.sign_transaction(contract_txn)
        tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
        status = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180).status

        if status == 1:
            logger.success(f'https://etherscan.io/tx/{tx_hash.hex()}')
            tg_messages.append(f'{STR_DONE} {module_str}\nhttps://etherscan.io/tx/{tx_hash.hex()}')
            return
        else:
            raise Exception(f'transfer ALT has failed')

    except Exception as error:
        logger.error(error)
        tg_messages.append(f'{STR_CANCEL}{module_str} | {error}')
        return False


def get_gas():
    try:
        w3 = Web3(Web3.HTTPProvider(ETH_RPC))
        gas_price = w3.eth.gas_price
        gwei = w3.from_wei(gas_price, 'gwei')
        return gwei
    except Exception as error:
        logger.error(error)


def wait_gas():
    logger.info("Get GWEI")
    while True:
        try:
            gas = get_gas()
            if gas > MAX_GWEI:
                logger.info(f'Current GWEI: {gas} > {MAX_GWEI}')
                time.sleep(60)
            else:
                logger.success(f"GWEI is normal | current: {gas} < {MAX_GWEI}")
                break
        except Exception as e:
            logger.warning(e)
            time.sleep(10)


if __name__ == '__main__':
    with open(f'recipients.txt') as f: recipient_addresses = f.read().splitlines()
    with open(f'private_keys.txt') as f: private_keys = f.read().splitlines()
    RECIPIENTS_WALLETS = dict(zip(private_keys, recipient_addresses))
    random.shuffle(private_keys)
    claim()
