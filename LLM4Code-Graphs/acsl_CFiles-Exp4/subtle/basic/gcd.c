int gcd(int a, int b) {
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}
