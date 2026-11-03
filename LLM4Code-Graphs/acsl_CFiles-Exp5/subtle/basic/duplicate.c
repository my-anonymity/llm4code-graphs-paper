
/*@
  ensures (arr[i] == arr[j]) ==> \result==arr[j];
*/
int firstDuplicate(int arr[], int size) {
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size; i++) {
        /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int j = i + 1; j < size; j++) {
            if (arr[i] == arr[j]) {
                return arr[j]; // Return the first duplicate found
            }
        }
    }
    return -1; // No duplicates found
}
