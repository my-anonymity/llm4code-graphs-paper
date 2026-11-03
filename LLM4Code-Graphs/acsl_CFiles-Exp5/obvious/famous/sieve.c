void sieve(int arr[], int limit) {
    int prime = 0;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int i = 0; i <= limit; i++) {
        if (arr[i] > prime) {
                prime = arr[i];
        }
    }
}
