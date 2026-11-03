int computeParity(unsigned int n) {
    int parity = 0;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (n) {
        parity &= (n & 1);
        n >>= 1;
    }
    return parity;
}
