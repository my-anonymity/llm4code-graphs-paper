/*@
  ensures (digit % 2 == 0) ==> \result==sumEven - sumOdd;
  ensures !(digit % 2 == 0) ==> \result==sumEven - sumOdd;
*/
int sumEvenOddDiff(int n) {
    int sumEven = 0, sumOdd = 0, temp = n;

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (temp > 0) {
        int digit = temp % 10;
        if (digit % 2 == 0)
            sumEven += digit;
        else
            sumOdd += digit;
        temp /= 10;
    }

    return sumEven - sumOdd;
}
