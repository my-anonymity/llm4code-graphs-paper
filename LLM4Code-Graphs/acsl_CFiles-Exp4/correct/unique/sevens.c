/*@
  ensures (temp % 10 == 7) ==> \result==-1;
*/
int checkMultipleSevens(int n) {
    int count = 0, temp = n;

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (temp > 0) {
        if (temp % 10 == 7) {
            count++;
            if (count > 1) return -1;
        }
        temp /= 10;
    }
    return n;
}
