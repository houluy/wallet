from sawtooth_sdk.processor.core import TransactionProcessor
from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction

import json
import hashlib

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

    def apply(self, transaction, context):
        header = transaction.header
        payload = transaction.payload
        signature = transaction.signature
        context_id = transaction.context_id

        payload = json.loads(payload.decode())

        if payload["typ"] == "create":
            account_name = payload["name"]
            init_value = payload["balance"]
            account_address, dumped_init_value = self.create_account(account_name, init_value)
            print(account_address)
            data = {account_address: dumped_init_value}
            context.set_state(data, timeout=constant.TXTIMEOUT)
            logger.info(f"Account {payload['name']} with initial value {init_value} created.")
        elif payload["typ"] == "transfer":
            sender_address = payload["sender"]
            receiver_address = payload["receiver"]
            value = payload["amount"]
            sender, receiver = context.get_state([sender_address, receiver_address])
            print(sender, receiver)
            sender = json.loads(sender.data)
            receiver = json.loads(receiver.data)
            sender["balance"] -= value
            receiver["balance"] += value
            context.set_state({
                sender_address: json.dumps(sender).encode(),
                receiver_address: json.dumps(receiver).encode(),
            }, timeout=constant.TXTIMEOUT)
            logger.info(f"Transfer from {sender_address} to {receiver_address} with amount {value}  succeeded.")

    def create_account(self, name, balance=0):
        account_address_suffix = hashlib.sha512(name.encode()).hexdigest()[:constant.ADDRESS_SUFFIX_LEN]
        account_address = self._namespace_prefix + account_address_suffix
        init_value = {
            "name": name,
            "balance": balance,
        }
        return account_address, json.dumps(init_value).encode()


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

