/*@
  ensures (arr[i] > max) ==> \result==max;
*/
int findMax(int arr[], int size) {
    int max = arr[0];
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 1; i < size; i++) {
        if (arr[i] > max)
            max = arr[i];
    }
    return max;
}
