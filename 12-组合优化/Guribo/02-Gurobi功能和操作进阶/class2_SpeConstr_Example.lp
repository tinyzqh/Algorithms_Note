\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  x + y + z
Subject To
 c: x + y + z + Rgc = 10
Bounds
 Rgc <= 5
SOS
 s0:  S1 :: x:1 y:2 z:3
 s1:  S2 :: y:4 z:2 x:1
End
