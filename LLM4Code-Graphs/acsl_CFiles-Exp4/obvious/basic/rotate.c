void rotateArray(int arr[], int size, int k) {
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
}
