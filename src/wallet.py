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
import pathlib
import time
import struct
import base64

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
        tx_dic = dict(
            family_name=self.family_name,
            family_version=self.family_version,
            inputs=inputs,
            outputs=outputs,
            signer_public_key=self.signer_public_key,
            batcher_public_key=self.signer_public_key,
            dependencies=[],
            nonce=str(random.randint(0, 1000000)),
            payload_sha512=sha512(payload).hexdigest(),
        )
        txn_header_bytes = TransactionHeader(**tx_dic).SerializeToString()
        transaction_id = self.signer.sign(txn_header_bytes)
        txn = Transaction(
            header=txn_header_bytes,
            header_signature=transaction_id,
            payload=payload,
        )
        return txn, transaction_id
    
    def generate_batch_list(self, *txns):
        """
        Return:
            @batch_sig: Batch ID
            @batch_list_bytes: Batch data
        """
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
        return batch_sig, batch_list_bytes

    def request_txs(self, batch_list_bytes):
        try:
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
        #try:
        #    print("Retrieving transaction receipt...")
        #    response = requests.get(status_link)
        #    print(response.text)
        #except HTTPError as e:
        #    print(e)

    def get_address(self, name):
        return self.family_prefix + sha512(name.encode()).hexdigest()[:constant.ADDRESS_SUFFIX_LEN]

    def transaction(func):
        def wrapper(self, *args, **kwargs):
            payload, inputs, outputs = func(self, *args, **kwargs)
            tx, txid = self.generate_transaction(payload, inputs, outputs)
            batch_id, batch_bytes = self.generate_batch_list(tx)
            self.request_txs(batch_bytes)
            return txid, batch_id
        return wrapper

    def receipt(func):
        def wrapper(self, *args, **kwargs):
            txid, batch_id = func(self, *args, **kwargs)
            status = None
            max_retry = 10
            ind = 0
            while status != "COMMITTED" and ind < max_retry:
                status = self.check_batch_status(batch_id)
                ind += 1
                time.sleep(0.5)
            return self.fetch_receipt(txid)
        return wrapper

    def check_batch_status(self, batch_id):
        batch_status_url = urllib.parse.urljoin(self.base_url, "batch_statuses")
        query_data = {"id": batch_id}
        response = requests.get(
            batch_status_url,
            params=query_data,
        )
        return response.json()["data"][0]["status"]
    
    @transaction
    def create_account(self, name, default_balance=0):
        op_dic = {
            "typ": "create",
            "name": name,
            "balance": default_balance,
        }
        inputs = outputs = self.get_address(name)
        return json.dumps(op_dic), [inputs], [outputs]

    @transaction
    def transfer_money(self, src, dst, amount):
        sender_addr = self.get_address(src.name)
        receiver_addr = self.get_address(dst.name)
        op_dic = {
            "typ": "transfer",
            "sender": src.name,
            "receiver": dst.name,
            "amount": amount,
        }
        inputs = outputs = [sender_addr, receiver_addr]
        return json.dumps(op_dic), inputs, outputs

    @receipt
    @transaction
    def get_balance(self, name):
        op_dic = {
            "typ": "query",
            "name": name,
            "key": "balance",
        }
        inputs = outputs = self.get_address(name)
        return json.dumps(op_dic), [inputs], []

    @transaction
    def deposit(self, name, amount):
        op_dic = {
            "typ": "change",
            "name": name,
            "amount": amount,
        }
        inputs = outputs = self.get_address(name)
        return json.dumps(op_dic), [inputs], [outputs]

    def withdraw(self, name, amount):
        return self.deposit(name, -amount)

    @transaction
    def purge(self, name):
        op_dic = {
            "typ": "purge",
            "name": name,
        }
        inputs = outputs = self.get_address(name)
        return json.dumps(op_dic), [inputs], [outputs]

    def fetch_receipt(self, txid):
        receipt_url = urllib.parse.urljoin(self.base_url, "receipts")
        params = {
            "id": txid,
        }
        response = requests.get(
            receipt_url,
            params=params,
        )
        return response.json()["data"]


class Wallet:
    def __init__(self, name):
        self.name = name
        self.cache_file = pathlib.Path(f"cache/{self.name}.json")
        self.oper = Operation()
        
    def create(self, balance=0, force=False):
        if self.cache_file.exists() and not force:  # An existing account
            attrs = self.load()
        else:  # A new account
            self.balance = balance
            try:
                self.oper.create_account(self.name, self.balance)
            except InvalidTransaction as e:
                logger.error(f"New account {self.name} fails to be created")
            self.cache()
            logger.info(f"New account {self.name} created with balance {self.balance}")

    def check_balance(self):
        balance = self.query_balance()
        if balance != self.balance:
            logger.info(f"Balance in cache (${self.balance}) is not same as in blockchain (${balance}). Re-Synchronizing...")
            self.balance = balance
            self.cache() 

    def auto_cache(func):
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            self.cache()
        return wrapper

    def query(self, key):
        query_func = f"query_{key}"
        value = getattr(self, query_func)()
        logger.info(f"Account {self.name} has {key} value of {value}")
        return value

    def query_balance(self):
        data = self.oper.get_balance(self.name)
        value_bytes = base64.b64decode(data[0]["data"][0])
        balance = struct.unpack("<I", value_bytes)[0]
        return balance
    
    @auto_cache
    def deposit(self, amount):
        self.oper.deposit(self.name, amount)
        self.balance += amount
        logger.info(f"Account {self.name} deposits ${amount}, new balance: ${self.balance}")

    @auto_cache
    def withdraw(self, amount):
        self.oper.withdraw(self.name, amount)
        self.balance -= amount
        logger.info(f"Account {self.name} withdraws ${amount}, new balance: ${self.balance}")

    @auto_cache
    def transfer(self, dst, amount):
        try:
            self.oper.transfer_money(self, dst, amount)
        except InvalidTransaction as e:
            logger.error("Transfer failed! Internal exception")
        except constant.OutOfBalanceException as e:
            logger.error(f"Account {self.name} does not have enough money ({amount})!")
        else:
            self.balance -= amount
            dst.balance += amount
            dst.cache()
            logger.info(f"Transfer ${amount} from {self.name} to {dst.name}, new balance: {self.name}:${self.balance}, {dst.name}:${dst.balance}")

    def purge(self):
        logger.info(f"NOTE: This will purge the account completely, all balance will be liquidated.")
        self.oper.purge(self.name)
        self.cache_file.unlink()
    
    def cache(self):
        attrs = {
            "balance": self.balance,
        }
        with open(self.cache_file, "w") as f:
            json.dump(attrs, f)

    def load(self, check=False):
        try:
            f = open(self.cache_file, "r")
            attrs = json.load(f)
        except (FileNotFoundError, EOFError, json.decoder.JSONDecodeError):
            logger.info(f"Account {self.name} does not exists or has been damaged in local cache, try to sychronize with blockchain.")
        else:
            logger.info(f"Loaded an exising account named {self.name}")
            self.balance = attrs["balance"]
            if check:
                self.check_balance()
                logger.info(f"Balance checked -- ${self.balance}!")
        finally:
            f.close()
        return attrs


