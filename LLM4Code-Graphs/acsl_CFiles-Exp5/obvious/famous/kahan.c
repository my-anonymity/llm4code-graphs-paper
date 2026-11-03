
#include <math.h>

/*@
  ensures (n == 0) ==> \result==0.0;
*/
double kahanSum(double arr[], int n) {
  if (n == 0)
    return 0.0; // Handle empty array case

  double sumSquares = 0.0;
  /*@
	requires n>0;
	loop invariant 0<=i<=n-1;
	loop assigns i, ;
	loop variant n-1-i;
*/
for (int i = 0; i < n; i++) {
    sumSquares += arr[i] * arr[i];
  }
  return sqrt(sumSquares / n);
}
