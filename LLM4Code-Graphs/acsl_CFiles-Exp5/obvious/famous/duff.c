void duffsDevice(int *to, const int *from, int count) {
    int n = (count + 7) / 8;
    switch (count % 8) {
    case 0: do { *to++ = *from++;
    case 1:      *to++ = *from++;
            } /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (--n > 0);
    }
}
