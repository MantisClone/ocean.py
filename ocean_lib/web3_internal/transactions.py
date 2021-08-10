#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
import time
from typing import Optional, Union

from enforce_typing import enforce_types
from eth_account.messages import SignableMessage

from ocean_lib.web3_internal.utils import get_network_timeout
from ocean_lib.web3_internal.wallet import Wallet
from web3.datastructures import AttributeDict
from web3.main import Web3


@enforce_types
def sign_hash(msg_hash: SignableMessage, wallet: Wallet) -> str:
    """
    This method use `personal_sign`for signing a message. This will always prepend the
    `\x19Ethereum Signed Message:\n32` prefix before signing.

    :param msg_hash:
    :param wallet: Wallet instance
    :return: signature
    """
    s = wallet.sign(msg_hash)
    return s.signature.hex()


def send_dummy_transactions(
    block_number: int, block_confirmations: int, from_wallet: Wallet, to_address: str
):
    if not Web3.isChecksumAddress(to_address):
        to_address = Web3.toChecksumAddress(to_address)

    web3 = from_wallet.web3

    while web3.eth.block_number < block_number + block_confirmations:
        tx = {
            "from": from_wallet.address,
            "to": to_address,
            "value": Web3.toWei(0.001, "ether"),
            "chainId": web3.eth.chain_id,
        }
        tx["gas"] = web3.eth.estimate_gas(tx)
        raw_tx = from_wallet.sign_tx(tx)
        web3.eth.send_raw_transaction(raw_tx)
        time.sleep(2.5)


@enforce_types
def send_ether(
    from_wallet: Wallet, to_address: str, ether_amount: Union[int, float, str]
) -> AttributeDict:
    if not Web3.isChecksumAddress(to_address):
        to_address = Web3.toChecksumAddress(to_address)

    web3 = from_wallet.web3

    tx = {
        "from": from_wallet.address,
        "to": to_address,
        "value": Web3.toWei(ether_amount, "ether"),
        "chainId": web3.eth.chain_id,
    }
    tx["gas"] = web3.eth.estimate_gas(tx)
    raw_tx = from_wallet.sign_tx(tx)
    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    block_confirmations = int(os.getenv("BLOCK_CONFIRMATIONS"))
    if tx["chainId"] == 1337:
        send_dummy_transactions(
            receipt.blockNumber, block_confirmations, from_wallet, to_address
        )
    else:
        while web3.eth.block_number < receipt.blockNumber + block_confirmations:
            time.sleep(get_network_timeout(tx["chainId"]))
    return web3.eth.get_transaction_receipt(tx_hash)


@enforce_types
def cancel_or_replace_transaction(
    from_wallet: Wallet,
    nonce_value: Optional[Union[str, int]] = None,
    gas_price: Optional[int] = None,
    gas_limit: Optional[int] = None,
) -> AttributeDict:
    web3 = from_wallet.web3
    tx = {
        "from": from_wallet.address,
        "to": from_wallet.address,
        "value": 0,
        "chainId": web3.eth.chain_id,
    }
    gas = gas_limit if gas_limit is not None else web3.eth.estimate_gas(tx)
    tx["gas"] = gas + 1
    raw_tx = from_wallet.sign_tx(tx, fixed_nonce=nonce_value, gas_price=gas_price)
    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    block_confirmations = int(os.getenv("BLOCK_CONFIRMATIONS"))
    if tx["chainId"] == 1337:
        send_dummy_transactions(
            receipt.blockNumber, block_confirmations, from_wallet, from_wallet.address
        )
    else:
        while web3.eth.block_number < receipt.blockNumber + block_confirmations:
            time.sleep(get_network_timeout(tx["chainId"]))
    return web3.eth.get_transaction_receipt(tx_hash)
