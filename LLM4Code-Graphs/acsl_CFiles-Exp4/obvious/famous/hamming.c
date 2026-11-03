int hammingDistance(unsigned int x, unsigned int y) {
    int dist = 0;
    unsigned int val = x ^ y;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (val) {
      val -= 1;
    }
    return val;
}
