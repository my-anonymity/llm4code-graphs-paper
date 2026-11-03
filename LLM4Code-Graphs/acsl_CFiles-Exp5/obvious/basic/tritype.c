
/*@
  ensures (i < 0.0 || j < 0.0 || k < 0.0) ==> \result==3;
*/
int Tritype(double i, double j, double k){
  int trityp = 0;
  if (i < 0.0 || j < 0.0 || k < 0.0)          // line 10  
    return 3;
  if (i + j <= k || j + k <= i || k + i <= j) // line 12 
    return 3;    
  return trityp;
}
