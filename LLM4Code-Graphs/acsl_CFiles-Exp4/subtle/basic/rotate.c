void rotateArray(int arr[], int size, int k) {
    k = k % size; // Normalize k
    if (k == 0) return; // No rotation needed

    int temp[k]; // Store first k elements
    /*@
	requires k>0;
	loop invariant 0<=i<=k-1;
	loop assigns i, ;
	loop variant k-1-i;
*/
for (int i = 0; i < k; i++) {
        temp[i] = arr[i];
    }

    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size; i++) {
        arr[i] = arr[i + k];
    }

    /*@
	requires k>0;
	loop invariant 0<=i<=k-1;
	loop assigns i, ;
	loop variant k-1-i;
*/
for (int i = 0; i < k; i++) {
        arr[size - k + i] = temp[i];
    }
}
