================================
A wallet by Hyperledger Sawtooth
================================

Blockchain based wallet.


------------------------
HELP
------------------------

Supported operations: create, transfer, deposit and withdraw.

::

    usage: Sawlet [-h] {create,transfer,deposit,withdraw} ...

    A wallet by Hyperledger Sawtooth

    positional arguments:
        {create,transfer,deposit,withdraw}
    sub-command help
        create              Create a new account, if account is already created,
                            load it.
        transfer            Transfer money from source to destination account.
        deposit             Deposit money.
        withdraw            Withdraw money.

    optional arguments:
        -h, --help            show this help message and exit


