# -*- coding: utf-8 -*-
"""
@author: Optimization
"""
from gurobipy import *
import xlrd
import xlwt
import sys
from datetime import *
from xlrd import xldate_as_tuple

def ReadData(Orders, Logistics, LogisticsNum):
    data = xlrd.open_workbook("订单信息.xlsx")
    table = data.sheets()[0]
    nrows = table.nrows #行数
    ncols = table.ncols #列数
    for i in range(1,nrows):
        row = []
        for j in range(1,ncols):
            cell = table.cell_value(i,j)
            if table.cell(i,j).ctype == 3:
                date = datetime(*xldate_as_tuple(cell, 0))
                cell = date.strftime('%Y/%m/%d')
                row.append(cell)
            else:
                row.append(cell)
                
        d1 = datetime(int(row[3][0:4]), int(row[3][5:7]), int(row[3][8:]))
        d2 = datetime(int(row[4][0:4]), int(row[4][5:7]), int(row[4][8:]))     
        row.append((d2-d1).days+1)
        row.append(0)
        Orders[table.cell_value(i,0)] = row

    for i in Orders.keys():
        group = [i]
        for j in Orders.keys():
            if i!=j and Orders[i][2] == Orders[j][2] and \
                        Orders[i][3] == Orders[j][3] and \
                        Orders[i][4] == Orders[j][4]:
                group.append(j)
        Orders[i].append(group)
       
    data = xlrd.open_workbook("物流供应商信息.xlsx")
    for i in range(LogisticsNum):
        Logistic = {}
        table = data.sheets()[i]
        nrows = table.nrows #行数
        for j in range(0,nrows):
            row = table.row_values(j) 
            Logistic[row[0]] = row[1:]
        Logistics[i] = Logistic
      
    #print (Logistics)
#挑选报价最便宜的供应商    
def SingleOrder(Orders, index, Logistics, LTL, FTL, FTLRatio):
    print ("Single Order.")
    mincost = 999999
    Vehicleindex = -1000
    LogisticSelect = -1000
    LTLAvailable = -1000     #零担
    FTLAvailable = []        #整车
    
    for i in range(len(LTL)):              #确定零担可用车型
         if Orders[index][1] < LTL[i]:    
             LTLAvailable = i
             break
             
    for i in range(len(FTL)):              #确认整车可用车型
         if  FTL[i]*FTLRatio <= Orders[index][1] and Orders[index][1] <= FTL[i]:
             FTLAvailable.append(i)
 
    if LTLAvailable != -1000 or len(FTLAvailable) != 0:
        for LNum in Logistics.keys():
            if Orders[index][2] in Logistics[LNum].keys() and\
               Orders[index][5] >= Logistics[LNum][Orders[index][2]][7]:   # 确认物流供应商配送该点和时间合理
                if LTLAvailable != -1000:   #确认零担车辆
                    for i in range(LTLAvailable, len(LTL)):
                        if Logistics[LNum][Orders[index][2]][i+1] != '' and\
                           Orders[index][1]*Logistics[LNum][Orders[index][2]][i+1] < mincost:   #报价不为空且低于目前最小报价
                           LogisticSelect = LNum
                           Vehicleindex = i+1
                           mincost = Orders[index][1]*Logistics[LNum][Orders[index][2]][i+1]
                           
                if len(FTLAvailable) != 0:  #确认整车车辆
                    for i in range(len(FTLAvailable)):
                        for j in range(3):
                            if Logistics[LNum][Orders[index][2]][8+FTLAvailable[i]*3+j] != '' and\
                               Logistics[LNum][Orders[index][2]][8+FTLAvailable[i]*3+j] < mincost:   #报价不为空且低于目前最小报价
                               LogisticSelect = LNum
                               Vehicleindex = FTLAvailable[i]*3+8+j
                               mincost = Logistics[LNum][Orders[index][2]][8+FTLAvailable[i]*3+j] 
    
    
    if Vehicleindex != -1000 and LogisticSelect != -1000 and mincost != 99999:   #是否发现安排方法
        Orders[index][6] = 1                      #指示订单是否安排好
        Orders[index].append(LogisticSelect)      #选择的物流供应商
        Orders[index].append(Logistics[LogisticSelect]['南京到'][Vehicleindex])    #具体车型
        if Vehicleindex < 8:
            Orders[index].append('零担')          #零担
        else:
            Orders[index].append('整车')          #整车
        Orders[index].append(mincost)             #配送费用
    else:
        Orders[index][6] = 1
        Orders[index].append('') 
        Orders[index].append('') 
        Orders[index].append('') 
        Orders[index].append('') 
            
def MultiOrders(Orders, index, Logistics, LTL, FTL, FTLRatio):
    print ('Multi-Orders.')
    LTLAvailable = {}  #可用的零担车型
    FTLAvailable = {}  #可用的整车车型
    OrdersOpt = {}
    for i in range(len(Orders[index][7])):
        OrdersOpt [Orders[index][7][i]] = -1
        for j in range(len(LTL)):
             if Orders[Orders[index][7][i]][1] < LTL[j]:
                 LTLAvailable[Orders[index][7][i]] = j
                 break
             
        for j in range(len(FTL)):
             if FTLRatio*FTL[j]<= Orders[Orders[index][7][i]][1] and Orders[Orders[index][7][i]][1] <= FTL[j]:
                 FTLAvailable[Orders[index][7][i]] = j
                 break
             
                
    XINDEX = {}
    PVM = {}
    W = {}   #载重量集合
    for i in LTLAvailable.keys():
        for p in Logistics.keys():
            if Orders[i][2] in Logistics[p].keys() and\
               Orders[i][5] >= Logistics[p][Orders[i][2]][7]:   # 确认物流供应商配送该点和零担时间合理
                   for v in range(LTLAvailable[i], len(LTL)):
                       if Logistics[p][Orders[i][2]][v+1] != '':
                           OrdersOpt[i] = 1
                           for m in range(len(Orders[index][7])):
                               XINDEX[i, p, v+1, m+1] = Orders[i][1]*Logistics[p][Orders[i][2]][v+1]
                               W[i, p, v+1, m+1] = Orders[i][1]
                               PVM[p, v+1, m+1] = LTL[v]
    
    for i in FTLAvailable.keys():
        for p in Logistics.keys():
            if Orders[i][2] in Logistics[p].keys() and\
               Orders[i][5] >= Logistics[p][Orders[i][2]][7]:   # 确认物流供应商配送该点和零担时间合理
                   for v in range(FTLAvailable[i], len(FTL)):
                       for j in range(3):
                           if Logistics[p][Orders[i][2]][8+v*3+j] != '':
                               OrdersOpt[i] = 1
                               for m in range(len(Orders[index][7])):
                                   XINDEX[i, p, 8+v*3+j, m+1] = Logistics[p][Orders[i][2]][8+v*3+j]
                                   W[i, p, 8+v*3+j, m+1] = Orders[i][1]
                                   PVM[p, 8+v*3+j, m+1] = FTL[v]
    modelindex = -1
    for i in range(len(Orders[index][7])):
        if OrdersOpt[Orders[index][7][i]] == -1:    #该订单没有可用供应商
           Orders[Orders[index][7][i]][6] = 1
           Orders[Orders[index][7][i]].append('')
           Orders[Orders[index][7][i]].append('')
           Orders[Orders[index][7][i]].append('')
           Orders[Orders[index][7][i]].append('')
        else:                                       #该订单有可用车型
            modelindex = 1
            
    if modelindex == 1:
        model = Model()
        x = model.addVars(XINDEX.keys(), obj=XINDEX, vtype=GRB.BINARY, name='x')
        y = model.addVars(PVM.keys(), vtype=GRB.BINARY, name='y')
        
        #Constraint 1: all orders have to be delivered.
        for i in OrdersOpt.keys():
            if OrdersOpt[i] == 1:
                model.addConstr(x.sum(i, '*', '*', '*') == 1)
      
        #Constraint 2: the capacity limitation of the m-th truck which is used.
        for i in PVM.keys():
            if i[1] < 8:
                model.addConstr(x.prod(W,'*',i[0], i[1], i[2]) <= PVM[i]*y[i])
            else:
                model.addConstr(x.prod(W,'*',i[0], i[1], i[2]) >= FTLRatio*PVM[i]*y[i])
                model.addConstr(x.prod(W,'*',i[0], i[1], i[2]) <= PVM[i]*y[i])
        
        #Constraint 3: the m-th truck of v-type of logistics provider p is used
        for i in PVM.keys():
            model.addConstr(x.sum('*', i[0], i[1], i[2]) <= len(Orders[index][7])*y[i])
        
        #model.setParam(GRB.Param.LogToConsole, 0)    
        model.setParam(GRB.Param.TimeLimit, 10) 
        model.optimize()  
                  
        for i in XINDEX.keys():
            if x[i].x != 0:
                Orders[i[0]][6] = 1
                Orders[i[0]].append(i[1])
                Orders[i[0]].append(Logistics[p]['南京到'][i[2]])
                if i[2] < 8:
                    Orders[i[0]].append('零担')
                    Orders[i[0]].append(Orders[i[0]][1]*Logistics[i[1]][Orders[i[0]][2]][i[2]])
                else:
                    Orders[i[0]].append('整车') 
                    Orders[i[0]].append(Logistics[i[1]][Orders[i[0]][2]][i[2]])
                
                
                for j in XINDEX.keys():
                    if x[j].x != 0 and i[0] != j[0] and i[1] == j[1] and i[2] == j[2] and i[3] == j[3]:
                        Orders[i[0]].append(j[0]) 

def OutputResult(Orders):
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('订单配送方案')
    worksheet.write(0, 0, label = '订单编号')
    worksheet.write(0, 1, label = 'N/W (T)净重')
    worksheet.write(0, 2, label = 'G/W (T)毛重')
    worksheet.write(0, 3, label = '预计提货日期')
    worksheet.write(0, 4, label = '期望到达日期')
    worksheet.write(0, 5, label = '目的地')
    worksheet.write(0, 6, label = '物流商')
    worksheet.write(0, 7, label = '使用车型')
    worksheet.write(0, 8, label = '运输方式')
    worksheet.write(0, 9, label = '组合订单编号')
    worksheet.write(0, 10, label = '费用')
    
    for i in Orders.keys():
        worksheet.write(int(i), 0, label=i)
        worksheet.write(int(i), 1, label=Orders[i][0])
        worksheet.write(int(i), 2, label=Orders[i][1])
        worksheet.write(int(i), 3, label=Orders[i][3])
        worksheet.write(int(i), 4, label=Orders[i][4])
        worksheet.write(int(i), 5, label=Orders[i][2])
        if Orders[i][8] != '':
            worksheet.write(int(i), 6, label='物流商'+str(int(Orders[i][8])+1))
            worksheet.write(int(i), 7, label=Orders[i][9])
            worksheet.write(int(i), 8, label=Orders[i][10])
            if Orders[i][10]=='整车' and len(Orders[i])>12:
                count = 0
                for j in range(12, len(Orders[i])):
                    if i < Orders[i][j]:
                        count += 1
                if count == len(Orders[i])-12:
                    worksheet.write(int(i), 10, label=Orders[i][11])
                else:
                    worksheet.write(int(i), 10, label=0)                  
            else:
                worksheet.write(int(i), 10, label=Orders[i][11])
                
            if len(Orders[i])>12:
                temp =[] 
                for j in range(12, len(Orders[i])):
                    temp.append(int(Orders[i][j]))
                worksheet.write(int(i), 9, label=str(temp))
            else:
                worksheet.write(int(i), 9, label='')
                    
        else:
            worksheet.write(int(i), 6, label='——')
            worksheet.write(int(i), 7, label='——')
            worksheet.write(int(i), 8, label='——')
            worksheet.write(int(i), 9, label='')
            worksheet.write(int(i), 10, label='')           
    workbook.save('订单配送方案.xls')
try:
    FTLRatio = 0.9
    Orders = {}
    Logistics = {}
    LTL = [0.5, 3, 5, 10, 20, 1000]        #零担载重
    FTL = [2, 5, 10, 15, 20, 25, 30, 32]   #整车车型载重
    ReadData(Orders, Logistics, 2)
    for i in Orders.keys():
        if Orders[i][6] == 0 and len(Orders[i][7]) == 1:
            SingleOrder(Orders, i, Logistics, LTL, FTL, FTLRatio)
        elif Orders[i][6] == 0 and len(Orders[i][7]) != 1:
            MultiOrders(Orders, i, Logistics, LTL, FTL, FTLRatio)              
    OutputResult(Orders)
    print('处理完成。')
    
except GurobiError as exception:
    print('Error code ' + str(exception.errno) + ": " + str(exception))

except AttributeError:
    print('Encountered an attribute error')