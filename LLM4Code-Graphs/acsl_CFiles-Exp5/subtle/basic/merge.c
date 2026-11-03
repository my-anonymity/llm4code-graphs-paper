
void mergeSorted(int arr1[], int size1, int arr2[], int size2, int result[]) {
    int i = 0, j = 0, k = 0;

    /*@
	requires size1>0;
	loop invariant 0<=i<=size1-1;
	loop assigns i, ;
	loop variant size1-1-i;
*/
while (i < size1 && j < size2) {
        if (arr1[i] < arr2[j]) {
            result[k++] = arr1[i++];
        } else {
            result[i++] = arr2[j++];
        }
    }

    /*@
	requires size1>0;
	loop invariant 0<=i<=size1-1;
	loop assigns i, ;
	loop variant size1-1-i;
*/
while (i < size1) {
        result[k++] = arr1[i++];
    }

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (j < size2) {
        result[k++] = arr2[j++];
    }
}
