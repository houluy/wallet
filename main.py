from src.cli import parser


def main():
    args = parser.parse_args()
    args.func(args)
    #w1 = Wallet("houlu")
    #w2 = Wallet("guaguade", init_balance=100)
    #w2.transfer(w1, 10)

main()

