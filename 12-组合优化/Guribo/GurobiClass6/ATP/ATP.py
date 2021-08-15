# -*- coding: utf-8 -*-
"""
@author: ZHU LANJIAN
"""
from gurobipy import *
import xlrd, xlsxwriter, math
from collections import OrderedDict

def ReadData(DataPath, Locations, Auto_carriers, Vehicles, Indicator, Hlimit, Space):
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
            
    table = data.sheets()[1]        # Auto_carriers
    nrows = table.nrows  
    count = 1
    for i in range(1,nrows):
        row = table.row_values(i)
        if row[0] not in Auto_carriers.keys():
            Auto_carriers[row[0]] = [count, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]]
            count += 1
    
    
    count = 1    
    table = data.sheets()[2]        # vehicles
    nrows = table.nrows    
    for i in range(1,nrows):
        row = table.row_values(i)
        if row[0] not in Vehicles.keys():
            Vehicles[row[0]]=[count, row[1], row[2], row[3], row[4]]
            count += 1
            
    for k in Auto_carriers.keys():
        for i in Vehicles.keys():
            Indicator[i,k] = []
            if Vehicles[i][4]>=Hlimit:
                if Auto_carriers[k][1] == 'I':
                    if Vehicles[i][3] + 2*Space <= Auto_carriers[k][6]:
                        Indicator[i,k].append(1)
                        
                if Auto_carriers[k][1]=='II':
                    if Vehicles[i][3] + 2*Space <= Auto_carriers[k][6]:
                        Indicator[i,k].append(1)   
            else:
                if Auto_carriers[k][1] == 'I':
                    if Vehicles[i][3] + 2*Space <= Auto_carriers[k][6]:
                        Indicator[i,k].append(1)
                    if Vehicles[i][3] + 2*Space <= Auto_carriers[k][8]:
                        Indicator[i,k].append(3)
            
                if Auto_carriers[k][1] == 'II':
                    if Vehicles[i][3] + 2*Space <= Auto_carriers[k][6]:
                        Indicator[i,k].append(1)
                        
                    if Vehicles[i][3] + 1.5*Space <= Auto_carriers[k][8]/2:
                        Indicator[i,k].append(3)
                        Indicator[i,k].append(4)
                        
                if Auto_carriers[k][1] == 'III':
                    if Vehicles[i][3] + 1.5*Space <= Auto_carriers[k][6]/2:
                        Indicator[i,k].append(1)
                        Indicator[i,k].append(2)
                        
                    if Vehicles[i][3] + 1.5*Space <= Auto_carriers[k][8]/2:
                        Indicator[i,k].append(3)
                        Indicator[i,k].append(4)
           
        
def CalculateDistance(lng1, lat1, lng2, lat2):
    RADIUS = 6378137
    PI = math.pi
    return 2*RADIUS*math.asin(math.sqrt(pow(math.sin(PI*(lat1 - lat2) / 360), 2) + math.cos(PI*lat1 / 180)*\
                                          math.cos(PI*lat2 / 180)*pow(math.sin(PI*(lng1 - lng2) / 360), 2)))
def ConstructDistanceMatrix(Locations, DistanceMatrix):
    for i in Locations.keys():
        for j in Locations.keys():
            DistanceMatrix[i, j] = CalculateDistance(Locations[i][2], Locations[i][1], Locations[j][2], Locations[j][1])

def subtour(arcs):
    unvisited = []
    for i in range(len(arcs)):
        if arcs[i][0] not in unvisited:
            unvisited.append(arcs[i][0])
        if arcs[i][1] not in unvisited:
            unvisited.append(arcs[i][1])   
    cycle = {}
    cyclenum = 0
    while unvisited: # true if list is non-empty
        thiscycle = []
        neighbors = unvisited
        while neighbors:
            current = neighbors[0]
            thiscycle.append(current)
            unvisited.remove(current)
            neighbors = [j for i,j in arcs.select(current,'*') if j in unvisited]
        if len(arcs)+1 > len(thiscycle):
            cycle[cyclenum] = thiscycle
            cyclenum += 1
    return cycle

def subtourelim(model, where):
    if where == GRB.Callback.MIPSOL:
        # make a list of edges selected in the solution
        vals = model.cbGetSolution(model._vars)
        selected = {}
        for i in model._vars.keys():
            if vals[i] > 0.9:
                if i[2] not in selected.keys():
                    selected[i[2]] = [(i[0],i[1])]
                else:
                    selected[i[2]].append((i[0],i[1]))
                    
        for k in selected.keys():
            temp = tuplelist(selected[k])
            tour = subtour(temp)
            for cy in tour.keys():
                if len(tour[cy]) < len(selected[k]):
                    expr = LinExpr()
                    for i in range(len(tour[cy])):
                        edges = temp.select(tour[cy][i],'*')
                        if len(edges)!=0:
                            expr += model._vars[edges[0][0], edges[0][1], k]  
                    model.cbLazy(expr <= len(tour[cy])-1)
        
def BuildModel(Locations, Auto_carriers, Vehicles, DistanceMatrix, Indicator, Space, Routes):
    xindex = {}
    yindex = {}
    zindex = {}
    kf = {}
    Auto_carriersSort = list(Auto_carriers.keys())
    for k in Auto_carriers.keys():
        xindex[0,len(Vehicles)+1,Auto_carriers[k][0]] = DistanceMatrix[Auto_carriers[k][2], Auto_carriers[k][3]]
        for i in Vehicles.keys():
            if len(Indicator[i,k])!=0:
                xindex[0,Vehicles[i][0],Auto_carriers[k][0]] = DistanceMatrix[Auto_carriers[k][2],Vehicles[i][1]]
                xindex[Vehicles[i][0],len(Vehicles)+1, Auto_carriers[k][0]] = DistanceMatrix[Vehicles[i][1], Auto_carriers[k][2]]
                for ii in range(len(Indicator[i,k])):
                    yindex[Vehicles[i][0],Auto_carriers[k][0],Indicator[i,k][ii]] = Vehicles[i][2]+Space
                    kf[k,Indicator[i,k][ii]] = 1
                for j in Vehicles.keys():
                    if i!=j and len(Indicator[j,k])!=0:
                        xindex[Vehicles[i][0],Vehicles[j][0],Auto_carriers[k][0]]=\
                        DistanceMatrix[Vehicles[i][1], Vehicles[j][1]]  
        
        zindex[Auto_carriers[k][0]] = Auto_carriers[k][4]
    
    try:
        model = Model()
        x = model.addVars(xindex.keys(), vtype=GRB.BINARY, name='x')                #变量x_{ijk}
        y = model.addVars(yindex.keys(), vtype=GRB.BINARY, name='y')                #变量y_{ikf}
        z = model.addVars(zindex.keys(), vtype=GRB.BINARY, name='z')                #变量z_{k}
       
        model.setObjectiveN(z.sum('*'), index=0,  priority=3, name='obj1')
        model.setObjectiveN(z.prod(zindex), index=1,  priority=2, name='obj2')
        model.setObjectiveN(x.prod(xindex), index=2,  priority=1, name='obj3')           
        #(1)每辆乘用车都被配送
        for i in Vehicles.keys():
            model.addConstr(x.sum(Vehicles[i],'*','*') == 1)   
    
        #(2)轿运车经过某点要装载该点对应的乘用车
        for i in xindex.keys():
            if i[0] != 0:
                model.addConstr(y.sum(i[0],i[2],'*') >= x[i])         
            
        #(3)路径平衡约束
        for k in Auto_carriers.keys():
            model.addConstr(x.sum(0,'*',Auto_carriers[k][0]) == 1)
            model.addConstr(x.sum('*',len(Vehicles)+1, Auto_carriers[k][0]) == 1)
            for i in Vehicles.keys():
                if len(Indicator[i,k])!=0:
                    model.addConstr(x.sum(Vehicles[i][0],'*',Auto_carriers[k][0]) == x.sum('*', Vehicles[i][0], Auto_carriers[k][0]))
          
        #(4)轿运车是否使用
        for i in yindex.keys():
            model.addConstr(y[i]<=z[i[1]])
            
        #(5)装载约束-长度
        for i in kf.keys():
            expr = LinExpr()
            k = Auto_carriers[i[0]][0]
            for j in Vehicles.keys(): 
                if (Vehicles[j][0], k, i[1]) in yindex.keys():
                    expr += yindex[Vehicles[j][0], k, i[1]]*y[Vehicles[j][0], k, i[1]]
            if i[1]>2:
                model.addConstr(expr <= Auto_carriers[i[0]][7])
            else:
                model.addConstr(expr <= Auto_carriers[i[0]][5])
        #(6，7)预处理
        #(8)消除子回路约束
        
        model._acnum = len(Auto_carriers)
        model._vars = x
        model.Params.lazyConstraints = 1
        model.Params.TimeLimit = 100
        model.optimize(subtourelim)   
        for i in xindex.keys():
            if x[i].x > 0.9:
                if Auto_carriersSort[i[2]-1] not in Routes.keys():
                    Routes[Auto_carriersSort[i[2]-1]]=[(i[0],i[1])]
                else:
                    Routes[Auto_carriersSort[i[2]-1]].append((i[0],i[1]))
                    
    except GurobiError as exception:
        print('Error code ' + str(exception.errno) + ": " + str(exception))

    except AttributeError:
        print('Encountered an attribute error')
                
def OutputResult(Locations, Auto_carriers, Vehicles, Routes):
    workbook = xlsxwriter.Workbook('ATP方案.xlsx')
    worksheet = workbook.add_worksheet('路径方案')
    worksheet.write(0, 0, '轿运车ID')
    worksheet.write(0, 1, '位置点ID')
    worksheet.write(0, 2, '乘用车ID')
    VSort = list(Vehicles.keys()) 
    row = 1
    for i in Routes.keys():
        if len(Routes[i])>1:
            count = 1
            while count<len(Routes[i]):
                for j in range(count, len(Routes[i])):
                    if count==1:
                        if Routes[i][j][0]==0:
                            Routes[i][1], Routes[i][j] = Routes[i][j], Routes[i][1]
                            break
                    else:
                        index=count-1
                        if Routes[i][index][1]==Routes[i][count][0]:
                            break
                        else:
                            if Routes[i][index][1]==Routes[i][j][0]:
                                Routes[i][count], Routes[i][j] = Routes[i][j], Routes[i][count]  
                count+=1  

    
            for j in range(len(Routes[i])):
                if j==0:
                    worksheet.write(row, 0, i)
                    worksheet.write(row, 1, Auto_carriers[i][2])
                    worksheet.write(row, 2, "——")
                    row+=1
                elif j==len(Routes[i])-1:
                    worksheet.write(row, 0, i)
                    worksheet.write(row, 1, Vehicles[VSort[Routes[i][j][0]-1]][1])
                    worksheet.write(row, 2, VSort[Routes[i][j][0]-1])
                    row+=1
                    worksheet.write(row, 0, i)
                    worksheet.write(row, 1, Auto_carriers[i][3])
                    worksheet.write(row, 2, "——")
                    row+=1
                else:
                    worksheet.write(row, 0, i)
                    worksheet.write(row, 1, Vehicles[VSort[Routes[i][j][0]-1]][1])
                    worksheet.write(row, 2, VSort[Routes[i][j][0]-1])
                    row+=1                  
    workbook.close()  
  
     
DataPath = 'ATP数据.xlsx'                     #数据
Vehicles = OrderedDict()
Auto_carriers = OrderedDict()
Locations = OrderedDict() 
Indicator = {}
Routes = {}
Hlimit = 1.7
Space = 0.1
DistanceMatrix = {}
ReadData(DataPath, Locations, Auto_carriers, Vehicles, Indicator, Hlimit, Space)
ConstructDistanceMatrix(Locations, DistanceMatrix)
BuildModel(Locations, Auto_carriers, Vehicles, DistanceMatrix, Indicator, Space, Routes)
OutputResult(Locations, Auto_carriers, Vehicles, Routes)



