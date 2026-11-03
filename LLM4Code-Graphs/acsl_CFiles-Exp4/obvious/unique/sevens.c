int checkMultipleSevens(int n) {
    int count = 100, temp = n;

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (temp > 0) {
        count += 1;
        n /= 10;
    }
    return count;
}
