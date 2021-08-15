# -*- coding: utf-8 -*-
"""
@author: ZHU LANJIAN
"""

from gurobipy import *
import xlrd, xlsxwriter, datetime, math
from xlrd import xldate_as_datetime
from collections import OrderedDict

def ReadData(DataPath, Unit):
    print ("ReadData !")
    data = xlrd.open_workbook(DataPath)
    table = data.sheets()[0]        # Matrixdata
    nrows = table.nrows           
    for i in range(1,nrows):
        row = table.row_values(i)   
        if i not in Unit.keys():
            index1 = row[1].find(':')
            index2 = row[2].find(':')
            row[1] = [float(row[1][:index1]),float(row[1][index1+1:])]
            row[2] = [float(row[2][:index2]),float(row[2][index2+1:])]
            Unit[i] = row[:]
            
def BuildModel(Unit, groupNum, workingHours, weighted1, weighted2, weighted3, bestX, bestY, bestZ, bestU, bestV):
    xindex = {}    #班组k完成生产块i后紧接着完成生产块j
    yindex = {}    #班组k是否参与生产
    zindex = {}    #班组k的加班时间
   
    for k in range(groupNum):
        yindex[k] = 0
        zindex[k] = 0
        xindex[0,len(Unit)+1, k] = 0
        for i in Unit.keys():
            xindex[0,i,k] = 0
            xindex[i,len(Unit)+1,k] = Unit[i][5]
            for j in Unit.keys():
                if i != j and Unit[i][2][0]*60 + Unit[i][2][1] <= Unit[j][1][0]*60 + Unit[j][1][1] and Unit[i][4] == Unit[j][3]:
                    xindex[i,j,k] = Unit[i][5]
                    
    try:
        m = Model()
        x = m.addVars(xindex.keys(), vtype=GRB.BINARY, name='x')                     #变量x_{ijk}
        y = m.addVars(yindex.keys(), obj=weighted1, vtype=GRB.BINARY, name='y')      #变量y_{k}
        z = m.addVars(zindex.keys(), obj=weighted2, vtype=GRB.CONTINUOUS, name='z')  #变量z_{k}
        u = m.addVar(obj=weighted3, vtype=GRB.CONTINUOUS, name='u')                  #变量u
        v = m.addVar(obj=-weighted2, vtype=GRB.CONTINUOUS, name='v')                 #变量v
     
        #(1)	每一个生产块都被分配
        for i in Unit.keys():
            m.addConstr(x.sum(i,'*','*') == 1)
           
        #(2)  预处理，消减变量
        
        #(3)  班组是否参与生产
        for i in xindex.keys():
            if i[0]!=0 or i[1]!=len(Unit)+1:
                m.addConstr(x[i]<=y[i[2]])
        
        #(4)  生产块连接约束
        for k in range(groupNum):
            m.addConstr(x.sum(0, '*', k) == 1)
            m.addConstr(x.sum('*', len(Unit)+1, k) == 1)
            for i in Unit.keys():
                m.addConstr(x.sum(i, '*', k) == x.sum('*', i, k))
            
        #(5)(6)(7)最长和最短工作时间  加班时间
        for k in range(groupNum):
            m.addConstr(u >= x.prod(xindex, '*', '*', k))
            m.addConstr(v <= (1-y[k])*24 + x.prod(xindex, '*', '*', k))
            m.addConstr(z[k] >= x.prod(xindex, '*', '*', k)-8)
            
        
        #m.params.TimeLimit = 100
        m.optimize()
        #m.write('model.lp')
        
        #获得优化结果
        for i in xindex.keys():
            if x[i].x-0.5 > 0 and (i[0]!=0 or i[1]!= len(Unit)+1):
                bestX[i] = x[i].x
                
        for k in range(groupNum):
            bestY[k] = y[k].x
            bestZ[k] = z[k].x
            
        bestU[0] = u.x
        bestV[0] = v.x
         
    except GurobiError as exception:
        print('Error code ' + str(exception.errno) + ": " + str(exception))

    except AttributeError:
        print('Encountered an attribute error')

def OutputResult(Unit, workingHours, bestX, bestY, bestZ, bestU, bestV):
    groupSet = {}
    for i in bestX.keys():
        if i[2] not in groupSet.keys():
            groupSet[i[2]] = [(i[0], i[1])]
        else:
            groupSet[i[2]].append((i[0], i[1]))
                
    for i in groupSet.keys():
         count = 0
         while count<len(groupSet[i]):
             for j in range(count, len(groupSet[i])):
                if count==0:
                     if groupSet[i][j][0]==0:
                         groupSet[i][0], groupSet[i][j] = groupSet[i][j], groupSet[i][0]
                         break
                else:
                    index=count-1
                    if groupSet[i][index][1]==groupSet[i][count][0]:
                        break
                    else:
                        if groupSet[i][index][1]==groupSet[i][j][0]:
                            groupSet[i][count], groupSet[i][j] = groupSet[i][j], groupSet[i][count]  
             count+=1

    workbook = xlsxwriter.Workbook('案例2 结果.xlsx')
    
    #####################################
    worksheet = workbook.add_worksheet('排班方案')
    worksheet.write(0, 0, '班组编号')
    worksheet.write(0, 1, '生产时长')
    worksheet.write(0, 2, '加班时长')
    worksheet.write(0, 3, '生产块编号')
    
    rows = 1
    for i in groupSet.keys():
        worksheet.write(rows, 0, 'w'+str(i))
        time = 0
        strTemp = ''
        for j in range(len(groupSet[i])-1):
            time += Unit[groupSet[i][j][1]][5]
            if j != len(groupSet[i])-2:
                strTemp += Unit[groupSet[i][j][1]][0] + ','
            else:
                strTemp += Unit[groupSet[i][j][1]][0]
        worksheet.write(rows, 1, time)
        worksheet.write(rows, 2, bestZ[i])
        worksheet.write(rows, 3, strTemp)
        rows += 1
        
    worksheet.write(rows, 0, '最长生产工时')
    worksheet.write(rows, 1, bestU[0])
    worksheet.write(rows+1, 0, '最短生产工时')
    worksheet.write(rows+1, 1, bestV[0])
    
    workbook.close()  
try:
    DataPath = '案例2 数据.xlsx'                     #数据
    Unit = OrderedDict()
    bestX = {}
    bestY = {}
    bestZ = {}
    bestU = {}
    bestV = {}
   
    groupNum = 15                                   #班组数量
    weighted1 = 100                                 #班组数量所占权重
    weighted2 = 1                                   #加班所占权重
    weighted3 = 1                                   #最长与最短工作时间差所占权重
    workingHours = 8                                #工作时长
    
    ReadData(DataPath, Unit)
    BuildModel(Unit, groupNum, workingHours, weighted1, weighted2, weighted3, bestX, bestY, bestZ, bestU, bestV)
    OutputResult(Unit, workingHours, bestX, bestY, bestZ, bestU, bestV)
    print ('Over.')
    
except GurobiError as exception:
    print('Error code ' + str(exception.errno) + ": " + str(exception))

except AttributeError:
    print('Encountered an attribute error')