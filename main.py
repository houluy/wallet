from src.wallet import Wallet

def main():
    w1 = Wallet("houlu")
    w2 = Wallet("guaguade", init_balance=100)
    w2.transfer(w1, 10)

main()

