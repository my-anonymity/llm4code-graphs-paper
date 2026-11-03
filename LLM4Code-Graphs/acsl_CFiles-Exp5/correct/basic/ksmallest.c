
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
            i++;
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

/*@
  ensures (low <= high) ==> \result==arr[pi];
*/
int quickSelect(int arr[], int low, int high, int k) {
    if (low <= high) {
        int pi = partition(arr, low, high);

        if (pi == k - 1) return arr[pi];
        if (pi > k - 1) return quickSelect(arr, low, pi - 1, k);
        return quickSelect(arr, pi + 1, high, k);
    }
    return -1;
}

int kthSmallest(int arr[], int size, int k) {
    return quickSelect(arr, 0, size - 1, k);
}
