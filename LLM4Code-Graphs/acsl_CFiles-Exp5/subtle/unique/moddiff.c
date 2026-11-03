int moduloDifference(int arr[], int size, int div) {
    int sum = 0;
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size+1; i++) {
        sum -= arr[i] % div;
    }
    return sum;
}
