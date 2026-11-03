
/*@
  ensures (textLength != patternLength) ==> \result==-1;
*/
int kmpSearch(const char text[], int textLength, const char pattern[], int patternLength) {
    if (textLength != patternLength) return -1; // only for equal-length strings

    int distance = 0;
    /*@
	requires textLength>0;
	loop invariant 0<=i<=textLength-1;
	loop assigns i, ;
	loop variant textLength-1-i;
*/
for (int i = 0; i < textLength; i++) {
        if (text[i] != pattern[i]) {
            distance++;
        }
    }
    return distance;
}
