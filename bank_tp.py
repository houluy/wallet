from sawtooth_sdk.processor.core import TransactionProcessor
from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction

from src.exceptions import *

import json
import hashlib
from collections.abc import MutableSequence
import struct

import constant
import logging

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
fmt = "%(asctime)s - %(levelname)s -- %(message)s"
handler.setFormatter(logging.Formatter(fmt))
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class TransferTransactionHandler(TransactionHandler):
    def __init__(self):
        self._family_name = "bank"
        self._namespace_prefix = hashlib.sha512(self._family_name.encode()).hexdigest()[:constant.ADDRESS_PREFIX_LEN]

    @property
    def family_name(self):
        return self._family_name

    @property
    def family_versions(self):
        return ["1.1"]

    @property
    def namespaces(self):
        return [self._namespace_prefix]

    def create(self, payload, context):
        account_name = payload["name"]
        balance = payload["balance"]
        account_address = self.get_address(account_name)
        init_value = {
            "name": account_name,
            "balance": balance,
        }
        data = {account_address: json.dumps(init_value).encode()}
        context.set_state(data, timeout=constant.TXTIMEOUT)
        logger.info(f"Account {account_name} with initial balance {balance} created.")

    def transfer(self, payload, context):
        sender_address = payload["sender"]
        receiver_address = payload["receiver"]
        amount = payload["amount"]
        sender = context.get_state([sender_address])[0]
        sender = json.loads(sender.data)
        sender_balance = sender["balance"]
        if sender_balance < amount:
            raise OutOfBalanceError(f"Account {sender.name} does not have enough money (${sender_balance}) to transfer (${amount}). ")
        receiver = context.get_state([receiver_address])[0]
        receiver = json.loads(receiver.data)
        sender["balance"] -= amount
        receiver["balance"] += amount
        context.set_state({
            sender_address: json.dumps(sender).encode(),
            receiver_address: json.dumps(receiver).encode(),
        }, timeout=constant.TXTIMEOUT)
        logger.info(f"Transfer from {sender_address} to {receiver_address} with amount {amount} succeeded.")

    def change(self, payload, context):
        account_name = payload["name"]
        amount = payload["amount"]
        account_address, account_data = self.get_data_by_name(account_name, context)
        balance = account_data["balance"]
        if amount >= 0:
            abs_amount = amount
            operation = "Deposit"
            prep = "to"
        elif amount < 0:
            abs_amount = abs(amount)
            if abs_amount > balance:
                raise OutOfBalanceError(f"Account {account_name} does not have enough money (${balance}) to withdraw (${abs_amount}). ")
            operation = "Withdraw"
            prep = "from"
        account_data["balance"] += amount
        data = {
            account_address: json.dumps(account_data).encode(),
        }
        context.set_state(data, timeout=constant.TXTIMEOUT)
        logger.info(f"{operation} amount {abs_amount} {prep} account {account_name} succeeded.")

    def query(self, payload, context):
        account_name = payload["name"]
        key = payload["key"]
        account_address, account_data = self.get_data_by_name(account_name, context)
        try:
            print(account_data)
            value = account_data[key]
        except KeyError:
            raise InvalidTransaction(f"Key {key} does not exist in account {account_name}.")
        else:
            value_bytes = struct.pack("<I", value)
            print(value_bytes)
            context.add_receipt_data(value_bytes, timeout=constant.TXTIMEOUT)
        logger.info(f"Query {key} from {account_name} got value {value}")

    def purge(self, payload, context):
        account_name = payload["name"]
        account_address = self.get_address(account_name)
        context.delete_state([account_address], timeout=constant.TXTIMEOUT)
        logger.info(f"Account {account_name} is purged successfully!")

    def dispatch(self, operation, payload, context):
        "Dispatch transaction operations to instance methods and call with parameters @payload and @context."
        return getattr(self, operation)(payload, context)

    def get_data_by_name(self, name, context):
        """
        Return:
            %address: address of the name
            %data:    target data
        """
        address = self.get_address(name)
        return address, self.get_data(address, context)

    def get_data(self, addresses, context):
        if isinstance(addresses, MutableSequence):
            data = context.get_state(addresses)
            return [json.loads[i.data] for i in data]
        else:
            data = context.get_state([addresses])[0].data
            print(addresses, data)
            return json.loads(data)

    def get_address(self, name):
        return self._namespace_prefix + hashlib.sha512(name.encode()).hexdigest()[:constant.ADDRESS_SUFFIX_LEN]

    def apply(self, transaction, context):
        try:
            header = transaction.header
            payload = transaction.payload
            signature = transaction.signature
            context_id = transaction.context_id
            payload = json.loads(payload.decode())
            operation = payload["typ"]
            self.dispatch(operation, payload, context)
        except Exception as e:
            print(e)


def install_tp():
    url = "tcp://127.0.0.1:4004"
    processor = TransactionProcessor(url=url)
    handler = TransferTransactionHandler()
    processor.add_handler(handler)
    try:
        print("Start")
        processor.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        print("Stop")
        if processor is not None:
            processor.stop()


install_tp()

