# AltLayer Check-Claim-Send

## Overview

Claim your altlayer airdrop and send to input wallet

## Requirements

- Python 3.10/3.11

## Getting Started

1. **Set Up Your Private Keys**

   - In the file named `private_keys.txt` insert your EVM private keys with each key on a separate line.

2. **Set Up Your ERC-20 recipient addresses**

   - In the file named `recipients.txt` insert your erc-20 recipient addresses.

4. **Configure the Application**

   - Open the `settings.py` file in the project directory.
   - You can configure:
     - ETH max gwei
     - Sleep between transactions
     - Telegram Token and Chat to report

## Abilities

- Waits for desired ETH gwei and perform the transaction in low gas
- Loges everything to console and telegram

## Running the Application


```bash
pip install -r requirements 
python main.py
```
