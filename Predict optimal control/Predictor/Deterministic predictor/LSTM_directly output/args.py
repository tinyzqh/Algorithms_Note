import argparse
import torch


def args_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--epochs', type=int, default=100, help='input dimension')
    parser.add_argument('--input_size', type=int, default=8, help='input dimension')
    parser.add_argument('--seq_len', type=int, default=50, help='seq len')
    parser.add_argument('--output_size', type=int, default=10, help='output dimension')
    parser.add_argument('--hidden_size', type=int, default=64, help='hidden size')
    parser.add_argument('--num_layers', type=int, default=10, help='num layers')
    parser.add_argument('--lr', type=float, default=0.0008, help='learning rate')
    parser.add_argument('--batch_size', type=int, default=256, help='batch size')
    parser.add_argument('--optimizer', type=str, default='adam', help='type of optimizer')
    parser.add_argument('--device', default=torch.device("mps"))
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='weight decay')
    parser.add_argument('--bidirectional', type=bool, default=True, help='LSTM direction')
    parser.add_argument('--step_size', type=int, default=10, help='step size')
    parser.add_argument('--gamma', type=float, default=0.1, help='gamma')

    args = parser.parse_args()

    return args