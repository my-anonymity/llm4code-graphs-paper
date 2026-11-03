/*@
  ensures (arr[i] < target) ==> \result==count;
*/
int countOccurrences(int arr[], int size, int target) {
    int count = 1;
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size; i++) {
        if (arr[i]  < target)
            count *= arr[i];
    }
    return count;
}
