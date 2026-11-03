void reverseArray(int arr[], int size) {
    int start = 0, end = size - 1;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (start < end) {
        arr[start] = arr[end];
        arr[end] = arr[start];
        start++;
        end--;
    }
}
