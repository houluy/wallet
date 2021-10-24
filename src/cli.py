import argparse
from src.wallet import Wallet

def create(args):
    name = args.name
    balance = args.balance
    new_wallet = Wallet(name=name)
    new_wallet.create(balance=balance, force=args.new)

def transfer(args):
    src = args.src
    dst = args.dst
    amount = args.amount
    src_wallet = Wallet(name=src)
    dst_wallet = Wallet(name=dst)
    src_wallet.transfer(dst_wallet, amount)

def deposit(args):
    name = args.name
    amount = args.amount
    wallet = Wallet(name=name)
    wallet.deposit(amount)

def withdraw(args):
    name = args.name
    amount = args.amount
    wallet = Wallet(name=name)
    wallet.withdraw(amount)

def purge(args):
    name = args.name
    wallet = Wallet(name=name)
    wallet.purge()

def query(args):
    name = args.name
    key = args.key
    wallet = Wallet(name=name)
    wallet.query()


parser = argparse.ArgumentParser(description="A wallet by Hyperledger Sawtooth", prog="Sawlet")

subparsers = parser.add_subparsers(help="sub-command help")

create_parser = subparsers.add_parser("create", help="Create a new account, if account is already created, load it.")

create_parser.add_argument("name", type=str, help="Provide the account name.")
create_parser.add_argument("-b", "--balance", type=int, help="Assign the number of balance, default to %(default)s.", default=0) 
create_parser.add_argument("-n", "--new", action="store_true", help="Force to create a new account, ignoring existing one.")
create_parser.set_defaults(func=create)

transfer_parser = subparsers.add_parser("transfer", help="Transfer money from source to destination account.")

transfer_parser.add_argument("src", type=str, help="Source account name")
transfer_parser.add_argument("dst", type=str, help="Destination account name")
transfer_parser.add_argument("amount", type=int, help="Amount of money")
transfer_parser.set_defaults(func=transfer)

deposit_parser = subparsers.add_parser("deposit", help="Deposit money.")

deposit_parser.add_argument("name", type=str, help="Name of the account.")
deposit_parser.add_argument("amount", type=int, help="Amount of the money.")
deposit_parser.set_defaults(func=deposit)

withdraw_parser = subparsers.add_parser("withdraw", help="Withdraw money.")

withdraw_parser.add_argument("name", type=str, help="Name of the account.")
withdraw_parser.add_argument("amount", type=int, help="Amount of the money.")
withdraw_parser.set_defaults(func=withdraw)

purge_parser = subparsers.add_parser("purge", help=("Purge an account. Note that the account is only purged at current block, it is still "
    "visible from previous blocks due to immutability of blockchain."))

purge_parser.add_argument("name", type=str, help="Name of the account.")
purge_parser.set_defaults(func=purge)

query_parser = subparsers.add_parser("query", help="Query account.")

query_parser.add_argument("name", type=str, help="Name of the account.")
query_parser.set_defaults(func=query)

