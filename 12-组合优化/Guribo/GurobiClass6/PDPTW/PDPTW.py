# -*- coding: utf-8 -*-
"""
@author: ZHU LANJIAN
"""
from gurobipy import *
import xlrd, xlsxwriter, datetime, math
from xlrd import xldate_as_datetime
from collections import OrderedDict

def ReadData(DataPath, Locations, Vehicles, Orders):
    print ("ReadData !")
    data = xlrd.open_workbook(DataPath)
    table = data.sheets()[0]        # Locations
    nrows = table.nrows
    count = 1             
    for i in range(1,nrows):
        row = table.row_values(i)   
        if row[0] not in Locations.keys():
            Locations[row[0]] = [count, row[1], row[2]]
            count += 1
            
    table = data.sheets()[1]        # Vehicles
    nrows = table.nrows  
    indicator = 0
    count = 1
    for i in range(1,nrows):
        row = table.row_values(i)
        if row[0] not in Vehicles.keys():
            if indicator == 0:
                d1 = xldate_as_datetime(row[3],0)
                d2 = xldate_as_datetime(row[4],0)
                if d2>d1:
                   EarliestDate = d1
                else:
                   EarliestDate = d2
                indicator = 1
            else:
                if d1<EarliestDate:
                    EarliestDate = d1            
                if d2<EarliestDate:
                    EarliestDate = d2
            Vehicles[row[0]]=[count, row[1], row[2], d1, d2, row[5], row[6], row[7], row[8], row[9], row[10]]
            count += 1
    
    
    count = 1    
    table = data.sheets()[2]        # Orders
    nrows = table.nrows    
    for i in range(1,nrows):
        row = table.row_values(i)
        if row[0] not in Orders.keys():
            pd1 = xldate_as_datetime(row[5],0)
            pd2 = xldate_as_datetime(row[6],0)
            dd1 = xldate_as_datetime(row[9],0)
            dd2 = xldate_as_datetime(row[10],0)
            Orders[row[0]]=[count, row[1], row[2], row[3], row[4], pd1, pd2, row[7], row[8], dd1, dd2]
            count += 1
            
    return EarliestDate
            
def preprocessing(Vehicles, Orders, EarliestDate):
    for i in Vehicles.keys():
       Vehicles[i][3] = (Vehicles[i][3]-EarliestDate).seconds
       Vehicles[i][4] = (Vehicles[i][4]-EarliestDate).seconds
    
    for i in Orders.keys():
        if Orders[i][5]>=EarliestDate:
            Orders[i][5] = (Orders[i][5]-EarliestDate).seconds
        else:
            Orders[i][5] = 0
        
        if Orders[i][6]>=EarliestDate:
            Orders[i][6] = (Orders[i][6]-EarliestDate).seconds
        else:
            Orders[i][6] = 0
            
        if Orders[i][9]>=EarliestDate:
            Orders[i][9] = (Orders[i][9]-EarliestDate).seconds
        else:
            Orders[i][9] = 0
        
        if Orders[i][10]>=EarliestDate:
            Orders[i][10] = (Orders[i][10]-EarliestDate).seconds
        else:
            Orders[i][10] = 0
            
        temp = []   
        for j in Vehicles.keys():
            if Vehicles[j][7].find(Orders[i][1])!=-1:
                temp.append(j)
        Orders[i][1] = temp
        
def CalculateDistance(lng1, lat1, lng2, lat2):
    RADIUS = 6378137
    PI = math.pi
    return 2*RADIUS*math.asin(math.sqrt(pow(math.sin(PI*(lat1 - lat2) / 360), 2) + math.cos(PI*lat1 / 180)*\
                                          math.cos(PI*lat2 / 180)*pow(math.sin(PI*(lng1 - lng2) / 360), 2)))
def ConstructDistanceMatrix(Locations, DistanceMatrix):
    for i in Locations.keys():
        for j in Locations.keys():
            DistanceMatrix[i, j] = CalculateDistance(Locations[i][2], Locations[i][1], Locations[j][2], Locations[j][1])
            
def BuildModel(Locations, Vehicles, Orders, DistanceMatrix, xsol, asol, qsol, wsol):
    xindex = {}
    aindex = {}
    qindex = {}
    windex = {}
    
    TimeMatrix = {}
    xobjcof= {}
    
    N = len(Orders)
    OSort = list(Orders.keys()) 
    VSort = list(Vehicles.keys()) 
    
    for k in Vehicles.keys():
        kk = Vehicles[k][0]
        for i in range(1, 2*N +1):
            if i<=N and k in Orders[OSort[i-1]][1]:
                aindex[i, kk] = 0
                qindex[i, kk] = Vehicles[k][9]
                windex[i, kk] = 0         
            if i>N and k in Orders[OSort[i-N-1]][1]:
                aindex[i, kk] = 0
                qindex[i, kk] = Vehicles[k][9]
                windex[i, kk] = 0          
            for j in range(1, 2*N +1):
                if i!=j:
                    if i<=N and j<=N and k in Orders[OSort[i-1]][1] and k in Orders[OSort[j-1]][1]:
                       xindex[i, j, kk] = DistanceMatrix[Orders[OSort[i-1]][3],Orders[OSort[j-1]][3]]
                       xobjcof[i, j, kk] = xindex[i, j, kk]*Vehicles[k][10]/1000
                       TimeMatrix[i, j, kk] = 3.6*xindex[i, j, kk]/Vehicles[k][8]
                       
                    if i<=N and j>N and k in Orders[OSort[i-1]][1] and k in Orders[OSort[j-N-1]][1]:
                       xindex[i, j, kk] = DistanceMatrix[Orders[OSort[i-1]][3],Orders[OSort[j-N-1]][7]]
                       xobjcof[i, j, kk] = xindex[i, j, kk]*Vehicles[k][10]/1000
                       TimeMatrix[i, j, kk] = 3.6*xindex[i, j, kk]/Vehicles[k][8]
                       
                    if i>N and j<=N and i-N!=j and k in Orders[OSort[i-N-1]][1] and k in Orders[OSort[j-1]][1]:
                       xindex[i, j, Vehicles[k][0]] = DistanceMatrix[Orders[OSort[i-N-1]][7],Orders[OSort[j-1]][3]]
                       xobjcof[i, j, kk] = xindex[i, j, kk]*Vehicles[k][10]/1000
                       TimeMatrix[i, j, kk] = 3.6*xindex[i, j, kk]/Vehicles[k][8]
                       
                    if i>N and j>N and k in Orders[OSort[i-N-1]][1] and k in Orders[OSort[j-N-1]][1]:
                       xindex[i, j, kk] = DistanceMatrix[Orders[OSort[i-N-1]][7],Orders[OSort[j-N-1]][7]]
                       xobjcof[i, j, kk] = xindex[i, j, kk]*Vehicles[k][10]/1000
                       TimeMatrix[i, j, kk] = 3.6*xindex[i, j, kk]/Vehicles[k][8]
                       
        aindex[0, kk] = 0
        qindex[0, kk] = Vehicles[k][9]
        windex[0, kk] = 0  
        
        aindex[2*N+1, kk] = 0
        qindex[2*N+1, kk] = Vehicles[k][9]
        windex[2*N+1, kk] = 0 
    
        xindex[0, 2*N+1, kk] = DistanceMatrix[Vehicles[k][1], Vehicles[k][2]]
        xobjcof[0, 2*N+1, kk] = xindex[0, 2*N+1, kk]*Vehicles[k][10]/1000
        TimeMatrix[0, 2*N+1, kk] = 3.6*xindex[0, 2*N+1, kk]/Vehicles[k][8]
        
        for i in range(1, N+1):
            if k in Orders[OSort[i-1]][1]:
                xindex[0, i, kk] = DistanceMatrix[Vehicles[k][1],Orders[OSort[i-1]][3]]
                xobjcof[0, i, kk] = xindex[0, i, kk]*Vehicles[k][10]/1000
                TimeMatrix[0, i, kk] = 3.6*xindex[0, i, kk]/Vehicles[k][8]
        for i in range(N+1, 2*N+1):
            if k in Orders[OSort[i-N-1]][1]:
                xindex[i, 2*N+1, kk] = DistanceMatrix[Orders[OSort[i-N-1]][7],Vehicles[k][2]]  
                xobjcof[i, 2*N+1, kk] = xindex[i, 2*N+1, kk]*Vehicles[k][10]/1000
                TimeMatrix[i, 2*N+1, kk] = 3.6*xindex[i, 2*N+1, kk]/Vehicles[k][8]
    
    
    model = Model()
    x = model.addVars(xobjcof.keys(), obj=xobjcof, vtype=GRB.BINARY, name='x')             #变量x_{ijk}
    a = model.addVars(aindex.keys(), vtype=GRB.CONTINUOUS, name='a')                       #变量a_{ik}
    q = model.addVars(qindex.keys(), vtype=GRB.CONTINUOUS, name='q')                       #变量q_{ik}
    w = model.addVars(windex.keys(), vtype=GRB.CONTINUOUS, name='w')                       #变量w_{ik}
        
    #(1)保证每个货物都被配送
    for i in range(1, N +1):
        model.addConstr(x.sum(i,'*','*') == 1)
        
    #(3)保证取货后要有对应的送货
    for i in aindex.keys():
        if i[0]>=1 and i[0]<=N:
            model.addConstr(x.sum(i[0],'*',i[1]) == x.sum(i[0]+N,'*', i[1]))
            
    #(4)路径平衡约束
    for k in Vehicles.keys():
        model.addConstr(x.sum(0,'*',Vehicles[k][0]) == 1)
        model.addConstr(x.sum('*',2*N+1,Vehicles[k][0]) == 1)
        for i in range(1, 2*N +1):
            model.addConstr(x.sum(i,'*',Vehicles[k][0]) == x.sum('*',i,Vehicles[k][0]))
      
    #(5)载货量平衡约束
    for i in xindex.keys():
        k = VSort[i[2]-1]
        if i[0]==0:
            model.addConstr(q[i[1],i[2]] >= q[i[0],i[2]]+2*Vehicles[k][9]*x[i]-2*Vehicles[k][9])
        elif i[0]<=N:
            model.addConstr(q[i[1],i[2]] >= q[i[0],i[2]]+2*Vehicles[k][9]*x[i]+ \
                            Orders[OSort[i[0]-1]][2]-2*Vehicles[k][9])
        else:  
            model.addConstr(q[i[1],i[2]] >= q[i[0],i[2]]+2*Vehicles[k][9]*x[i]+ \
                            -Orders[OSort[i[0]-N-1]][2]-2*Vehicles[k][9])
    
    #(6)车辆最大载量约束
    for i in qindex.keys():
        model.addConstr(q[i]<=qindex[i])

    #(7)时间平衡约束
    for i in xindex.keys():
        k=VSort[i[2]-1]
        if i[0]==0: 
            model.addConstr(a[i[1],i[2]] >= a[i[0],i[2]]+w[i[0],i[2]]+\
                            2*Vehicles[k][4]*x[i]-2*Vehicles[k][4]+TimeMatrix[i])                                    
        elif i[0]<=N:
            ii = OSort[i[0]-1]
            model.addConstr(a[i[1],i[2]] >= a[i[0],i[2]]+w[i[0],i[2]]+Orders[ii][4]*60+\
                      2*Vehicles[k][4]*x[i]-2*Vehicles[k][4]+TimeMatrix[i])
        else:
            ii = OSort[i[0]-N-1]
            model.addConstr(a[i[1],i[2]] >= a[i[0],i[2]]+w[i[0],i[2]]+Orders[ii][8]*60+\
                      2*Vehicles[k][4]*x[i]-2*Vehicles[k][4]+TimeMatrix[i])
            
    #(8)(9)(10)时间窗约束
    for i in aindex.keys():
        if i[0]==0 or i[0]==2*N+1:
            model.addConstr(a[i]+w[i]>=Vehicles[VSort[i[1]-1]][3])
            model.addConstr(a[i]+w[i]<=Vehicles[VSort[i[1]-1]][4])
        elif i[0]<=N:
            model.addConstr(a[i]+w[i]>=Orders[OSort[i[0]-1]][5])
            model.addConstr(a[i]+w[i]<=Orders[OSort[i[0]-1]][6])
        else:
            model.addConstr(a[i]+w[i]>=Orders[OSort[i[0]-N-1]][9])
            model.addConstr(a[i]+w[i]<=Orders[OSort[i[0]-N-1]][10])
            
    #(11)车辆最大行驶距离约束
    for k in Vehicles.keys():
        model.addConstr(0.001*x.prod(xindex,'*','*',Vehicles[k][0])<=Vehicles[k][5])
        
    #(12)车辆最大行驶时间约束
    for k in Vehicles.keys():
        model.addConstr(a[2*N+1,Vehicles[k][0]]-a[0,Vehicles[k][0]]<=Vehicles[k][6]*3600)

    #(13)货物先取后送约束
    for i in aindex.keys():
        if i[0]<=N and i[0]>=1:
            model.addConstr(a[i]+w[i]+Orders[OSort[i[0]-1]][4]+TimeMatrix[i[0],i[0]+N,i[1]]<=a[i[0]+N,i[1]])
            
    model.params.TimeLimit = 600    
    model.optimize()
    
    for i in xindex.keys():
        if x[i].x -0.5>0:
            xsol[i] = 1
            asol[i[0], i[2]]=a[i[0], i[2]].x
            asol[i[1], i[2]]=a[i[1], i[2]].x
            
            qsol[i[0], i[2]]=q[i[0], i[2]].x
            qsol[i[1], i[2]]=q[i[1], i[2]].x
            
            wsol[i[0], i[2]]=w[i[0], i[2]].x
            wsol[i[1], i[2]]=w[i[1], i[2]].x
            
def OutputResult(Locations, Vehicles, Orders, EarliestDate, xsol, asol, qsol, wsol):
    workbook = xlsxwriter.Workbook('PDPTW方案.xlsx')
    worksheet = workbook.add_worksheet('方案')
    worksheet.write(0, 0, '车辆ID')
    worksheet.write(0, 1, '停靠点ID')
    worksheet.write(0, 2, '到达时刻')
    worksheet.write(0, 3, '离开时刻')
    worksheet.write(0, 4, '取送货')
    worksheet.write(0, 5, '货物ID')
    worksheet.write(0, 6, '车辆载量')
    route={}
    N = len(Orders)
    OSort = list(Orders.keys()) 
    VSort = list(Vehicles.keys()) 
    
    for i in xsol.keys():
        if i[2] not in route.keys():
            route[i[2]] = [i[2], (i[0], i[1])]
        else:
            route[i[2]].append((i[0], i[1]))       
    row = 1
    for i in route.keys():
        if len(route[i])>2:
            count = 1
            while count<len(route[i]):
                for j in range(count, len(route[i])):
                    if count==1:
                        if route[i][j][0]==0:
                            route[i][1], route[i][j] = route[i][j], route[i][1]
                            break
                    else:
                        index=count-1
                        if route[i][index][1]==route[i][count][0]:
                            break
                        else:
                            if route[i][index][1]==route[i][j][0]:
                                route[i][count], route[i][j] = route[i][j], route[i][count]  
                count+=1
            
            for j in range(1,len(route[i])):
                if j==1:
                    worksheet.write(row, 0, VSort[i-1])
                    worksheet.write(row, 1, Vehicles[VSort[i-1]][1])
                    worksheet.write(row, 2, "——")
                    worksheet.write(row, 3, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]+wsol[route[i][j][0],i]), '%Y/%m/%d %H:%M:%S'))
                    worksheet.write(row, 4, "——")
                    worksheet.write(row, 5, "——")
                    worksheet.write(row, 6, 0)
                    row+=1
                elif j==len(route[i])-1:
                    worksheet.write(row, 0, VSort[i-1])
                    worksheet.write(row, 1, Orders[OSort[route[i][j][0]-N-1]][7])
                    worksheet.write(row, 2, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]), '%Y/%m/%d %H:%M:%S'))
                    worksheet.write(row, 3, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]+wsol[route[i][j][0],i]+Orders[OSort[route[i][j][0]-N-1]][8]*60), '%Y/%m/%d %H:%M:%S'))
                    worksheet.write(row, 4, '送货')
                    worksheet.write(row, 5, OSort[route[i][j][0]-N-1])
                    worksheet.write(row, 6, -Orders[OSort[route[i][j][0]-N-1]][2])
                    row+=1 
                    worksheet.write(row, 0, VSort[i-1])
                    worksheet.write(row, 1, Vehicles[VSort[i-1]][2])
                    worksheet.write(row, 2, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][1],i]), '%Y/%m/%d %H:%M:%S'))
                    worksheet.write(row, 3, "——")
                    worksheet.write(row, 4, "——")
                    worksheet.write(row, 5, "——")
                    worksheet.write(row, 6, 0)
                    row+=1
                else:
                    worksheet.write(row, 0, VSort[i-1])
                    if route[i][j][0]>N:
                        worksheet.write(row, 1, Orders[OSort[route[i][j][0]-N-1]][7])
                        worksheet.write(row, 2, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]), '%Y/%m/%d %H:%M:%S'))
                        worksheet.write(row, 3, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]+wsol[route[i][j][0],i]+Orders[OSort[route[i][j][0]-N-1]][8]*60), '%Y/%m/%d %H:%M:%S'))
                        worksheet.write(row, 4, '送货')
                        worksheet.write(row, 5, OSort[route[i][j][0]-N-1])
                        worksheet.write(row, 6, -Orders[OSort[route[i][j][0]-N-1]][2])
                    else:
                        worksheet.write(row, 1, Orders[OSort[route[i][j][0]-N-1]][3])
                        worksheet.write(row, 2, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]), '%Y/%m/%d %H:%M:%S'))
                        worksheet.write(row, 3, datetime.datetime.strftime(EarliestDate + datetime.timedelta(seconds=asol[route[i][j][0],i]+wsol[route[i][j][0],i]+Orders[OSort[route[i][j][0]-N-1]][4]*60), '%Y/%m/%d %H:%M:%S'))
                        worksheet.write(row, 4, '取货')
                        worksheet.write(row, 5, OSort[route[i][j][0]-N-1])
                        worksheet.write(row, 6, Orders[OSort[route[i][j][0]-N-1]][2])
                    row+=1
    workbook.close()  

        
try:
    DataPath = 'PDPTW数据.xlsx'                     #数据
    Orders = OrderedDict()
    Vehicles = OrderedDict()
    Locations = OrderedDict() 
    xsol = {}
    asol = {}
    qsol = {}
    wsol = {}
    
    DistanceMatrix = {}
    EarliestDate = ReadData(DataPath, Locations, Vehicles, Orders)
    preprocessing(Vehicles, Orders, EarliestDate)
    ConstructDistanceMatrix(Locations, DistanceMatrix)
    BuildModel(Locations, Vehicles, Orders, DistanceMatrix, xsol, asol, qsol, wsol)
    OutputResult(Locations, Vehicles, Orders, EarliestDate, xsol, asol, qsol, wsol)


except GurobiError as exception:
    print('Error code ' + str(exception.errno) + ": " + str(exception))

except AttributeError:
    print('Encountered an attribute error')