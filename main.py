import json
import re

import requests
from fake_useragent import UserAgent
from loguru import logger


def decimalToInt(qty, decimal):
    return float(qty / 10**decimal)
def main():
    sum = 0
    for address in addresses:
        ua = UserAgent()
        headers = {
            "accept": "text/x-component",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "content-type": "text/plain;charset=UTF-8",
            "next-action": "67fc7bba70928774c5305f604afe585929202b77",
            "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(homePage)%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            'user-agent': ua.random,
            "Referer": 'https://94c87e96-000a-4740-bc01-0ca9abbb7bca-stg-airdrop.alt.technology/'
        }

        while True:
            try:
                response = requests.post('https://94c87e96-000a-4740-bc01-0ca9abbb7bca-stg-airdrop.alt.technology/', data=json.dumps([address]), headers=headers)
                if response.status_code != 200:
                    raise Exception(f'received non-200 code - {response.status_code}')
                amount_match = re.search(r'"amount":"([^"]+)"', response.text)
                if amount_match:
                    amount = amount_match.group(1)
                    human_amount = decimalToInt(int(amount), 18)
                    logger.success(f"[{address}] Amount:{human_amount}")
                    sum += human_amount
                else:
                    logger.warning(f"[{address}] not eligible")
                break
            except Exception as e:
                logger.error(e)

    logger.success(f'total drop amount is {sum} ALT')

if __name__ == '__main__':
    with open(f'addresses.txt') as f: addresses = f.read().splitlines()
    main()
