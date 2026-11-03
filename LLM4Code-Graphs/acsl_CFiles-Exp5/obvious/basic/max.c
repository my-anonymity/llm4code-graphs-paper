int findMax(int arr[], int size) {
    int max = 100;
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 1; i < size; i++) {
            max = arr[i];
    }
    return max;
}
