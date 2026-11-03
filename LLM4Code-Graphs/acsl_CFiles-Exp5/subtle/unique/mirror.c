int mirrorSum(int n) {
    int reversed = 0, temp = n;

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (temp > 0) {
        reversed = reversed * 10 + (temp / 10);
        temp /= 10;
    }

    return n + reversed;
}
