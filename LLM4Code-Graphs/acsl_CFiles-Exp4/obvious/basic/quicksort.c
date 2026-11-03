/*@
  ensures (arr[j] <= pivot) ==> \result==i + 1;
*/
int qsortPartition(int arr[], int low, int high) {
    int pivot = arr[high];
    int i = low - 1;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int j = low; j < high; j++) {
        if (arr[j] <= pivot) {
            i++;
        }
    }
    return i + 1;
}

