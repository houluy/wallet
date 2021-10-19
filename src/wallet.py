from sawtooth_signing import create_context, CryptoFactory
from hashlib import sha512
from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader, Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader, Batch, BatchList
from sawtooth_sdk.processor.exceptions import InvalidTransaction

import json
import requests
import urllib
from urllib.error import HTTPError
import random
import logging

import constant

logger = logging.getLogger(__name__)


class Operation:
    def __init__(self, version="1.1"):
        self.family_name = "bank"
        self.family_prefix = sha512(self.family_name.encode()).hexdigest()[:constant.ADDRESS_PREFIX_LEN]
        self.family_version = version
        context = create_context('secp256k1')
        private_key = context.new_random_private_key()
        self.signer = CryptoFactory(context).new_signer(private_key)
        self.signer_public_key = self.signer.get_public_key().as_hex()
        self.base_url = "http://127.0.0.1:8008" 

    def generate_transaction(self, payload, inputs=None, outputs=None):
        payload = payload.encode()
        txn_header_bytes = TransactionHeader(
            family_name=self.family_name,
            family_version=self.family_version,
            inputs=inputs,
            outputs=inputs,
            signer_public_key=self.signer_public_key,
            batcher_public_key=self.signer_public_key,
            dependencies=[],
            nonce=str(random.randint(0, 1000000)),
            payload_sha512=sha512(payload).hexdigest(),
        ).SerializeToString()
        transaction_id = self.signer.sign(txn_header_bytes)
        txn = Transaction(
            header=txn_header_bytes,
            header_signature=transaction_id,
            payload=payload,
        )
        logger.debug(txn)
        return txn
    
    def generate_batch_list(self, *txns):
        batch_header_bytes = BatchHeader(
            signer_public_key=self.signer_public_key,
            transaction_ids=[txn.header_signature for txn in txns],
        ).SerializeToString()

        batch_sig = self.signer.sign(batch_header_bytes)
        batch = Batch(
            header=batch_header_bytes,
            header_signature=batch_sig,
            transactions=txns,
        )
        batch_list_bytes = BatchList(batches=[batch]).SerializeToString()
        return batch_list_bytes

    def request_txs(self, batch_list_bytes):
        try:
            print("Sending request...")
            batch_url = urllib.parse.urljoin(self.base_url, "batches")
            response = requests.post(
                batch_url,
                data=batch_list_bytes,
                headers={"Content-Type": "application/octet-stream"},
            )
        except HTTPError as e:
            print(e)
        else:
            res_js = response.json()
            status_link = res_js["link"]
        try:
            print("Retrieving transaction receipt...")
            response = requests.get(status_link)
            print(response.text)
        except HTTPError as e:
            print(e)

    def get_address(self, name):
        return self.family_prefix + sha512(name.encode()).hexdigest()[:constant.ADDRESS_SUFFIX_LEN]

    def transaction(func):
        def wrapper(self, *args, **kwargs):
            payload, inputs, outputs = func(self, *args, **kwargs)
            logger.debug(f"payload: {payload}, inputs: {inputs}, outputs: {outputs}")
            tx = self.generate_transaction(payload, inputs, outputs)
            batch_bytes = self.generate_batch_list(tx)
            self.request_txs(batch_bytes)
        return wrapper

    @transaction
    def create_account(self, name, default_balance=0):
        op_dic = {
            "typ": "create",
            "name": name,
            "balance": default_balance,
        }
        inputs = self.get_address(name)
        return json.dumps(op_dic), [inputs], []

    @transaction
    def transfer_money(self, src, dst, amount):
        sender_addr = self.get_address(src.name)
        receiver_addr = self.get_address(dst.name)
        op_dic = {
            "typ": "transfer",
            "sender": sender_addr,
            "receiver": receiver_addr,
            "amount": amount,
        }
        inputs = [sender_addr, receiver_addr]
        return json.dumps(op_dic), inputs, []

    @transaction
    def get_balance(self, name):
        op_dic = {
            "typ": "query",
            "name": name,
            "key": "balance",
        }
        inputs = self.get_address(name)
        return json.dumps(op_dic), [inputs], []


class Wallet:
    def __init__(self, name, init_balance=0):
        self.name = name
        self.oper = Operation()
        self.init_balance = init_balance
        try:
            self.oper.create_account(self.name, self.init_balance)
        except InvalidTransaction as e:
            logger.error(f"New account {self.name} fails to be created")
        
    def transfer(self, dst, amount):
        try:
            self.oper.transfer_money(self, dst, amount)
        except InvalidTransaction as e:
            logger.error("Transfer failed! Internal exception")
        except constant.OutOfBalanceException as e:
            logger.error(f"Account {self.name} does not have enough money ({amount})!")
        else:
            logger.info(f"Transfer {amount} from {self.name} to {dst}")

