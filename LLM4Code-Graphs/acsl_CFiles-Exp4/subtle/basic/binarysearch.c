/*@
  ensures (arr[mid] == target) ==> \result==mid;
  ensures !(arr[mid] == target) ==> \result==-1;
*/
int binarySearch(int arr[], int size, int target) {
    int low = 0, high = size - 1;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (low <= high) {
        int mid = low + (high - low) / 2;
        if (arr[mid] == target)
            return mid;
        if (arr[mid] < target)
            low = mid + 1;
        else
            high = mid - 1;
    }
    return -1;
}
