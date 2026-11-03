/*@
  ensures (arr[i] == target) ==> \result==count;
*/
int countOccurrences(int arr[], int size, int target) {
    int count = 0;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int i = 0; i <= size; i++) {
        if (arr[i] == target)
            count++;
    }
    return count;
}
