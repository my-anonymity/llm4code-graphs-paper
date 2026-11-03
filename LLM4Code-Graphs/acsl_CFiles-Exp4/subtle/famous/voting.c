/*@
  ensures (arr[i] == candidate) ==> \result==(freq > size / 2) ? candidate : -1;
  ensures !(arr[i] == candidate) ==> \result==(freq > size / 2) ? candidate : -1;
*/
int majorityElement(int arr[], int size) {
    int candidate = arr[0];
    int count = 1;

    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 1; i < size; i++) {
        if (arr[i] == candidate) {
            count++;
        } else {
            count--;
            if (count == 0) {
                candidate = arr[i];
            }
        }
    }

    // Verify candidate
    int freq = 0;
    /*@
	requires size>0;
	loop invariant 0<=i<=size-1;
	loop assigns i, ;
	loop variant size-1-i;
*/
for (int i = 0; i < size; i++) {
        if (arr[i] == candidate) {
            freq++;
        }
    }

    return (freq > size / 2) ? candidate : -1; // -1 if no majority element
}
