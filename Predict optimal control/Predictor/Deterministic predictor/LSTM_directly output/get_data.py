import os
import random

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

device = torch.device("mps")

def setup_seed(seed):
    os.environ['PYTHONHASHSEED'] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True


def load_data(file_name):
    """
    :return: dataframe
    """
    df = pd.read_csv('data/' + file_name, encoding='gbk')
    df.fillna(df.mean(), inplace=True)
    # print(df)
    # 归一化并返回速度的最值
    columns = df.columns
    M, N = 0, 0
    for i in range(2, 10):
        m, n = np.max(df[columns[i]]), np.min(df[columns[i]])
        if i == 5:
            M, N = m, n
        if m > 0 and m != n:
            df[columns[i]] = (df[columns[i]] - n) / (m - n)
        else:
            continue

    # print(df)
    return df, M, N


class MyDataset(Dataset):
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __len__(self):
        return len(self.data)


# Multiple outputs data processing.
def nn_seq(args, file_names):
    seq_len = args.seq_len
    B = args.batch_size
    num = args.output_size

    def process(dataset, batch_size, step_size, shuffle, flag):
        # vel = dataset[dataset.columns[5]]
        # vel = vel.tolist()
        dataset = dataset.values.tolist()
        seq = []
        for i in range(0, len(dataset) - seq_len - num, step_size):
            train_seq = []
            train_label = []

            for j in range(i, i + seq_len):
                x = []
                for c in range(2, 10):
                    x.append(dataset[j][c])
                train_seq.append(x)

            for j in range(i + seq_len, i + seq_len + num):
                train_label.append(dataset[j][5])

            train_seq = torch.FloatTensor(train_seq)
            train_label = torch.FloatTensor(train_label).view(-1)
            seq.append((train_seq, train_label))

        if flag == 'train' or flag == 'val':
            return seq

        seq = MyDataset(seq)
        seq = DataLoader(dataset=seq, batch_size=batch_size, shuffle=shuffle, num_workers=0, drop_last=False)

        return seq

    ms, ns = [], []
    train_seqs, val_seqs = [], []
    Dtes = []
    print('data processing...')
    for file_name in tqdm(file_names):
        data, m, n = load_data(file_name)
        # split
        train = data[:int(len(data) * 0.7)]
        val = data[int(len(data) * 0.7):int(len(data) * 0.8)]
        test = data[int(len(data) * 0.8):len(data)]
        ms.append(m)
        ns.append(n)
        train_seq = process(train, B, step_size=1, shuffle=True, flag='train')
        val_seq = process(val, B, step_size=1, shuffle=True, flag='val')
        Dte = process(test, B, step_size=num, shuffle=False, flag='test')
        train_seqs.extend(train_seq)
        val_seqs.extend(val_seq)
        Dtes.append(Dte)

    Dtr = MyDataset(train_seqs)
    Dtr = DataLoader(dataset=Dtr, batch_size=B, shuffle=True, num_workers=0, drop_last=False)
    Val = MyDataset(val_seqs)
    Val = DataLoader(dataset=Val, batch_size=B, shuffle=True, num_workers=0, drop_last=False)

    return Dtr, Val, Dtes, ms, ns


if __name__ == '__main__':
    load_data('1.csv')