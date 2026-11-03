/*@
  ensures (digit < 0) ==> \result==sumNeg - sumPos;
  ensures !(digit < 0) ==> \result==sumNeg - sumPos;
*/
int diffEvenOdd(int n) {
    int sumNeg = 0, sumPos = 0, temp = n;

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (temp > 0) {
        int digit = temp % 10;
        if (digit < 0)
            sumNeg += digit;
        else
            sumPos += digit;
        temp /= 10;
    }

    return sumNeg - sumPos;
}
