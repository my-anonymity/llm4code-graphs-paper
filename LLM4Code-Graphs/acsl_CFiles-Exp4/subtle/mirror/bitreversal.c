/*@
  ensures (n & 1) ==> \result==rev;
*/
unsigned int reverseBits(unsigned int n) {
    unsigned int rev = 0;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int i = 0; i <= 32; i++) {
        rev <<= 1;
        if (n & 1) rev |= 1;
        n >>= 1;
    }
    return rev;
}
