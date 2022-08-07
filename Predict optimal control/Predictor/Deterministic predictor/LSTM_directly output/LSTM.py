import copy
import os
import sys
from itertools import chain

from matplotlib import pyplot as plt
from scipy.interpolate import make_interp_spline

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

import torch
from torch import nn
from torch.optim.lr_scheduler import StepLR
from tqdm import tqdm
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

from models import LSTM, BiLSTM

device = torch.device("mps")


def get_val_loss(args, model, Val):
    model.eval()
    loss_function = nn.MSELoss().to(args.device)
    val_loss = []
    for (seq, label) in tqdm(Val):
        with torch.no_grad():
            seq = seq.to(args.device)
            label = label.to(args.device)
            y_pred = model(seq)
            loss = loss_function(y_pred, label)
            val_loss.append(loss.cpu().item())

    return np.mean(val_loss)


def train(args, Dtr, Val, path):
    input_size, hidden_size, num_layers = args.input_size, args.hidden_size, args.num_layers
    output_size = args.output_size
    if args.bidirectional:
        model = BiLSTM(input_size, hidden_size, num_layers, output_size, batch_size=args.batch_size).to(device)
    else:
        model = LSTM(input_size, hidden_size, num_layers, output_size, batch_size=args.batch_size).to(device)

    loss_function = nn.MSELoss().to(device)
    if args.optimizer == 'adam':
        optimizer = torch.optim.Adam(model.parameters(), lr=args.lr,
                                     weight_decay=args.weight_decay)
    else:
        optimizer = torch.optim.SGD(model.parameters(), lr=args.lr,
                                    momentum=0.9, weight_decay=args.weight_decay)
    scheduler = StepLR(optimizer, step_size=args.step_size, gamma=args.gamma)
    # training
    min_epochs = 5
    best_model = None
    min_val_loss = 5
    print('training......')
    for epoch in tqdm(range(args.epochs)):
        train_loss = []
        for (seq, label) in tqdm(Dtr):
            seq = seq.to(device)
            label = label.to(device)
            y_pred = model(seq)
            loss = loss_function(y_pred, label)
            train_loss.append(loss.item())
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        scheduler.step()
        # validation
        val_loss = get_val_loss(args, model, Val)
        if epoch + 1 > min_epochs and val_loss < min_val_loss:
            min_val_loss = val_loss
            best_model = copy.deepcopy(model)

        print('epoch {:03d} train_loss {:.8f} val_loss {:.8f}'.format(epoch, np.mean(train_loss), val_loss))
        model.train()

    state = {'models': best_model.state_dict()}
    torch.save(state, path)


def sub_test(args, Dte, path, m, n):
    pred = []
    y = []
    print('loading models...')
    input_size, hidden_size, num_layers = args.input_size, args.hidden_size, args.num_layers
    output_size = args.output_size
    if args.bidirectional:
        model = BiLSTM(input_size, hidden_size, num_layers, output_size, batch_size=args.batch_size).to(device)
    else:
        model = LSTM(input_size, hidden_size, num_layers, output_size, batch_size=args.batch_size).to(device)
    # models = LSTM(input_size, hidden_size, num_layers, output_size, batch_size=args.batch_size).to(device)
    model.load_state_dict(torch.load(path,map_location='cpu')['models'])
    model.eval()
    print('predicting...')
    for (seq, target) in tqdm(Dte):
        target = list(chain.from_iterable(target.data.tolist()))
        y.extend(target)
        seq = seq.to(device)
        with torch.no_grad():
            y_pred = model(seq)
            y_pred = list(chain.from_iterable(y_pred.data.tolist()))
            pred.extend(y_pred)

    y, pred = np.array(y), np.array(pred)
    y = (m - n) * y + n
    pred = (m - n) * pred + n

    if len(pred) != 0:
        # print('mae:', mean_absolute_error(y, pred))
        # print('rmse:', np.sqrt(mean_squared_error(y, pred)))
        # if np.sqrt(mean_squared_error(y, pred))<=2:
        #     plot(y, pred)
        rmse=np.sqrt(mean_squared_error(y, pred))
    else:
        rmse=0
    return rmse




    # plot


def test(args, Dtes, path, ms, ns):
    Rmse=[]
    for Dte, m, n in zip(Dtes, ms, ns):
        rmse=sub_test(args, Dte, path, m, n)
        if rmse!=0:
            Rmse.append(rmse)
    print('能计算出的Rmse预测个数：',np.array(Rmse).shape)
    print('测试集个数:',np.array(Dtes).shape)
    plt.hist(Rmse,rwidth=0.5)
    plt.show()




def plot(y, pred):
    # plot
    x = [i for i in range(1, len(y) + 1)]
    # print(len(y))
    x_smooth = np.linspace(np.min(x), np.max(x), len(y) * 3)
    y_smooth = make_interp_spline(x, y)(x_smooth)
    plt.plot(x_smooth, y_smooth, c='green', marker='*', ms=1, alpha=0.75, label='true')

    y_smooth = make_interp_spline(x, pred)(x_smooth)
    plt.plot(x_smooth, y_smooth, c='red', marker='o', ms=1, alpha=0.75, label='pred')
    plt.grid(axis='y')
    plt.legend()
    #plt.savefig(f'{p}'+'.png')
    plt.cla()
    #plt.show()
