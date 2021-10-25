================================
A wallet by Hyperledger Sawtooth
================================

Blockchain based wallet.


------------------------
HELP
------------------------

Supported operations: create, transfer, deposit, withdraw, purge and query.

::
    usage: Sawlet [-h] [-c]
           name {create,transfer,deposit,withdraw,purge,query} ...

           A wallet by Hyperledger Sawtooth

           positional arguments:
               name                Provide the account name.
               {create,transfer,deposit,withdraw,purge,query}
                                   All supported operations for the account.
               create              Create a new account, if account is already created, load it.
               transfer            Transfer money from source to destination account.
               deposit             Deposit money.
               withdraw            Withdraw money.
               purge               Purge an account. Note that the account is only purged
                                   at current block, it is still visible from previous
                                   blocks due to immutability of blockchain.
               query               Query account.

           optional arguments:
               -h, --help            show this help message and exit
               -c, --check           Check the balance while loading the account.
