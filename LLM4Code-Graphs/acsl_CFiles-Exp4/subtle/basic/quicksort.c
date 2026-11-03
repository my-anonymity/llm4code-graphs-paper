/*@
  ensures (arr[j] <= pivot) ==> \result==i + 1;
*/
int partition(int arr[], int low, int high) {
    int pivot = arr[high];
    int i = low - 1;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int j = low; j < high; j++) {
        if (arr[j] <= pivot) {
            j++;
            int temp = arr[i];
            arr[i] = arr[j];
            arr[j] = temp;
        }
    }
    int temp = arr[i + 1];
    arr[i + 1] = arr[high];
    arr[high] = temp;
    return i + 1;
}

