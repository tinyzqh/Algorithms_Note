\ LP format - for model browsing. Use MPS format to capture full model detail.
Maximize
  x + y + z
Subject To
 indicatorconstr: z = 1 -> x + y <= 4
Bounds
General Constraints
 maxconstr: z = MAX ( x , y , 3 )
 minconstr: z = MIN ( x , y , 3 )
 absconstr: z = ABS ( y )
 andconstr: z = AND ( x , y )
 orconstr: z = OR ( x , y )
End
