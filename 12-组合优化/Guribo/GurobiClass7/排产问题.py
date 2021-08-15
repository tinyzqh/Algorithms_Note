# -*- coding: utf-8 -*-
"""
@author: ZHU LANJIAN
"""

from gurobipy import *
import xlrd, xlsxwriter, datetime, math
from xlrd import xldate_as_datetime
from collections import OrderedDict

def ReadData(DataPath, Production):
    print ("ReadData !")
    data = xlrd.open_workbook(DataPath)
    table = data.sheets()[0]        # Matrixdata
    nrows = table.nrows           
    for i in range(1,nrows):
        row = table.row_values(i)   
        if i not in Production.keys():
            Production[i-1] = row[:]
            
            
def BuildModel(Production, workingHours, workingHoursLimt, weighted1, weighted2, weighted3, bestX, bestY, bestE, bestU, bestV, bestW):
    xindex = {}    #第t天生产第i种产品的数量
    yindex = {}    #第t天是否生产第i种产品
    Nindex = {}    #整数值，保证生产产品数量是材料批量的整数倍
    Eindex = {}    #第t天生产的第i种产品调用了第j种产品的货架数量
    Uindex = {}    #第t天单班生产
    Vindex = {}    #第t天双班生产
    Windex = {}    #第t天加班时间
    
    for t in range(7):
        Uindex[t] = 0
        Vindex[t] = 0
        Windex[t] = 0
        for i in range(len(Production)):
            xindex[i,t] = 1/Production[i][2]
            yindex[i,t] = 0
            Nindex[i,t] = 0
            for j in range(len(Production)):
                if i!=j and Production[i][1] == Production[j][1]:
                    Eindex[i,j,t] = 0

    try:
        m = Model()
        x = m.addVars(xindex.keys(), vtype=GRB.INTEGER, name='x')                    #变量x_{it}
        y = m.addVars(yindex.keys(), obj=weighted2, vtype=GRB.BINARY, name='y')      #变量y_{it}
        z = m.addVar(obj=1, vtype=GRB.CONTINUOUS, name='z')                          #变量z
        e = m.addVars(Eindex.keys(), vtype=GRB.INTEGER, name='e')                    #变量e_{ijt}
        n = m.addVars(Nindex.keys(), vtype=GRB.INTEGER, name='n')                    #变量n_{it}
        u = m.addVars(Uindex.keys(), obj=weighted3, vtype=GRB.BINARY, name='u')      #变量u_{t}
        v = m.addVars(Vindex.keys(), obj=2*weighted3, vtype=GRB.BINARY, name='v')    #变量v_{t}
        w = m.addVars(Windex.keys(), obj=weighted1, vtype=GRB.CONTINUOUS, name='w')  #变量w_{t}
        
        #(1)	工时大于0.9
        for i in xindex.keys():
                m.addConstr(x[i] >= 0.9*Production[i[0]][2]*y[i])
                m.addConstr(x[i] <= (workingHoursLimt+1)*Production[i[0]][2]*y[i])
        
        #(2)  每天的工时不超过 workingHoursLimt 小时
        for t in range(7):
            m.addConstr(x.prod(xindex, '*', t) <= 0.5*u[t]*workingHoursLimt+v[t]*workingHoursLimt)
            
            
        #(3)  生产产品数量要为原料批量的整数倍
        for i in xindex.keys():
            m.addConstr(x[i] == Production[i[0]][3]*n[i])
               
    
        #(4)(5)  每天产品库存数量不超过料架数量，且不得低于安全库存
        for i in xindex.keys():
            expr = LinExpr()
            for j in range(i[1]+1):
                expr += x[i[0], j] - Production[i[0]][6+j]
                
            m.addConstr(Production[i[0]][5] + expr <= Production[i[0]][3]*10 + e.sum(i[0],'*', i[1]) - e.sum('*', i[0], i[1]))
            m.addConstr(Production[i[0]][5] + expr >= Production[i[0]][7+j]*Production[i[0]][4])
        
        #(6) 某产品能被调用料架的数量不能超过对应的料架数
        for t in range(7):
            for i in range(len(Production)):
                m.addConstr(e.sum('*', i, t)<=Production[i][3]*10)
            
        #(7)  Z值表示产品日库存最大值
        for t in range(7):
            expr = LinExpr()
            for i in range(len(Production)):
                expr += Production[i][6]
                for j in range(t+1):
                    expr += x[i,j] - Production[i][7+j]
            m.addConstr(z >= expr)
            
        #(8)(9)(10)
        for t in range(7):
            m.addConstr(y.sum('*',t) >= u[t])
            m.addConstr(y.sum('*',t) >= v[t])
            m.addConstr(u[t] + v[t]  <= 1)
            m.addConstr(y.sum('*',t) <= 10000*u[t] + 10000*v[t])
            
        #(11)  加班时间
        for t in range(7):
            m.addConstr(x.prod(xindex, '*', t) - workingHours*u[t] - 2*workingHours*v[t] <= w[t])
        
        m.optimize()
        
        #获得优化结果
        for i in xindex.keys():
            bestX[i] = x[i].x
            bestY[i] = y[i].x

        for i in Uindex.keys():
            bestU[i] = u[i].x
            bestV[i] = v[i].x
            bestW[i] = w[i].x
            
        for i in Eindex.keys():
            bestE[i] = e[i].x
                
    except GurobiError as exception:
        print('Error code ' + str(exception.errno) + ": " + str(exception))

    except AttributeError:
        print('Encountered an attribute error')
        
def OutputResult(Production, workingHours, bestX, bestY, bestE, bestU, bestV, bestW):
    hours = [0]*7
    overtime = [0]*7
    inventory = [0]*7
    week = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    workbook = xlsxwriter.Workbook('案例1 结果.xlsx')
    
    #####################################
    worksheet = workbook.add_worksheet('排产方案')
    worksheet.write(0, 0, '产品编号')
    for t in range(7):
        if bestU[t] == 1:
            week[t] += '（单班）'
            worksheet.write(0, t + 1, week[t])
            overtime[t] = workingHours
        elif bestV[t] == 1:
            week[t] += '（双班）'
            worksheet.write(0, t + 1, week[t])
            overtime[t] = 2*workingHours
        else:
            week[t] += '（---）'
            worksheet.write(0, t + 1, week[t])
    
    rows = 1
    for i in range(len(Production)):
        worksheet.write(rows, 0, Production[i][0])
        for t in range(7):
            worksheet.write(rows, t + 1, bestX[i,t])
        rows += 1
        
    #####################################
    worksheet = workbook.add_worksheet('生产工时')
    worksheet.write(0, 0, '产品编号')
    for t in range(7):
        worksheet.write(0, t + 1, week[t])
        
    rows = 1
    for i in range(len(Production)):
        worksheet.write(rows, 0, Production[i][0])
        for t in range(7):
            worksheet.write(rows, t + 1, bestX[i,t]/Production[i][2])
            hours[t] += bestX[i,t]/Production[i][2]
        rows += 1
        
    worksheet.write(rows, 0, '工作时间')
    worksheet.write(rows+1, 0, '加班时间')
    for t in range(7):
        worksheet.write(rows, t+1, hours[t])
        if overtime[t] < hours[t]:
            worksheet.write(rows+1, t+1, hours[t] - overtime[t]) 
        else:
            worksheet.write(rows+1, t+1, 0) 
    
    #####################################            
    worksheet = workbook.add_worksheet('产品库存')
    worksheet.write(0, 0, '产品编号')
    for t in range(7):
        worksheet.write(0, t + 1, week[t])
        
    rows = 1
    for i in range(len(Production)):
        sumInventory = Production[i][5]
        worksheet.write(rows, 0, Production[i][0])
        for t in range(7):
            sumInventory += bestX[i,t] - Production[i][7+t]
            inventory[t] += sumInventory
            worksheet.write(rows, t + 1, sumInventory)
        rows += 1
        
    worksheet.write(rows, 0, '库存合计')
    for t in range(7):
        worksheet.write(rows, t+1, inventory[t])
    
    workbook.close()  
            
try:
    DataPath = '案例1 数据.xlsx'                     #数据
    Production = OrderedDict()
    bestX = {}
    bestY = {}
    bestZ = {}
    bestE = {}
    bestU = {}
    bestV = {}
    bestW = {}
   
    weighted1 = 1                                   #加班所占权重
    weighted2 = 1                                   #更换模具次数所占的权重
    weighted3 = 1                                   #班次所占的权重
    workingHours = 8                                #工作时长
    workingHoursLimt = 20                           #最长工作时间

    ReadData(DataPath, Production)
    BuildModel(Production, workingHours, workingHoursLimt, weighted1, weighted2, weighted3, bestX, bestY, bestE, bestU, bestV, bestW)
    OutputResult(Production, workingHours, bestX, bestY, bestE, bestU, bestV, bestW)
    print ('Over.')

except GurobiError as exception:
    print('Error code ' + str(exception.errno) + ": " + str(exception))

except AttributeError:
    print('Encountered an attribute error')