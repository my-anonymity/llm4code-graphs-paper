/*@
  ensures (arr[i] > arr[i + 1]) ==> \result==1;
*/
int isSorted(int arr[], int size) {
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size - 1; i++) {
        if (arr[i] > arr[i + 1])
            return 1;
    }
    return 1;
}
