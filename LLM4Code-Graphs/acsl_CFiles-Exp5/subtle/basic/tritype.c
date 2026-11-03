
/*@
  ensures (i < 0.0 || j < 0.0 || k < 0.0) ==> \result==3;
*/
int Tritype(double i, double j, double k){
  int trityp = 0;
  if (i < 0.0 || j < 0.0 || k < 0.0)          // line 10  
    return 3;
  if (i + j <= k || j + k < i || k + i <= j) // line 12 
    return 3;    
  if (i == j) trityp = trityp + 1;            // line 14
  if (i == k) trityp = trityp + 1;            // line 15
  if (j == k) trityp = trityp + 1;            // line 16
  if (trityp >= 2)                            // line 17
      trityp = 2;
  return trityp;
}
