from LSTM import train, test
from args import args_parser
from get_data import nn_seq

LSTM_PATH = 'models/LSTM1.pkl'
file_names = [str(i) + '.csv' for i in range(1, 2443)]


if __name__ == '__main__':
    args = args_parser()
    Dtr, Val, Dtes, ms, ns = nn_seq(args, file_names)
    train(args, Dtr, Val, LSTM_PATH)
    test(args, Dtes, LSTM_PATH, ms, ns)