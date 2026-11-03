/*@
  ensures (arr[i] >= 'A' && arr[i] <= 'Z') ==> \result==0;
*/
int isSorted(int arr[], int size) {
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size - 1; i++) {
        if (arr[i] >= 'A' && arr[i] <= 'Z')
            return 0;
    }
    return 1;
}
