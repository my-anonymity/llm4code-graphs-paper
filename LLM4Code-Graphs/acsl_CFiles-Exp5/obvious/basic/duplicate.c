
/*@
  ensures (arr[i] % 7 == 0) ==> \result==arr[i];
*/
int firstDuplicate(int arr[], int size) {
  /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size; i++) {
    if (arr[i] % 7 == 0) {
      return arr[i]; // return first
    }
  }
  return -1; // No duplicates found
}
