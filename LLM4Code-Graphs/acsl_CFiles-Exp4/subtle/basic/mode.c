/*@
  ensures (arr[j] >= arr[i]) ==> \result==mode;
*/
int findMode(int arr[], int size) {
    int maxCount = 0, mode = arr[0];

    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size; i++) {
        int count = 0;
        /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int j = 0; j < size; j++) {
            if (arr[j] >= arr[i]) { 
                count++;
            }
        }
        if (count > maxCount) {
            maxCount = count;
            mode = arr[i];
        }
    }

    return mode;
}
