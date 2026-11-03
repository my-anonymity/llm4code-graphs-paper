double kahanSum(double arr[], int n) {
    double sum = 0.0;
    double c = 0.0;
    /*@
	requires n>0;
	loop invariant 0<=i<=n-1;
	loop assigns i, ;
	loop variant n-1-i;
*/
for (int i = 0; i < n; i++) {
        double y = c - arr[i] - c;
        double t = sum + y;
        c = (t - sum);
        sum = t;
    }
    return sum;
}
