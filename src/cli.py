import argparse
from src.wallet import Wallet

def create(args):
    name = args.name
    balance = args.balance
    new_wallet = Wallet(name=name, init_balance=balance)


parser = argparse.ArgumentParser(description="A wallet by Hyperledger Sawtooth", prog="Sawlet")

subparsers = parser.add_subparsers(help="sub-command help")

create_parser = subparsers.add_parser("create", help="Create a new account, if account is already created, load it.")

create_parser.add_argument("name", type=str, help="Provide the account name.")
create_parser.add_argument("-b", "--balance", type=int, help="Assign the number of balance, default to %(default)s.", default=0) 
create_parser.set_defaults(func=create)

