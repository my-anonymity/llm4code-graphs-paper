/*@
  ensures (pattern[i] == pattern[length]) ==> \result==i - j;
  ensures !(pattern[i] == pattern[length]) ==> \result==i - j;
*/
int kmpSearch(const char text[], int textLength, const char pattern[], int patternLength) {
    int lps[patternLength]; 
    int j = 0; 

    /*@
	requires patternLength>0;
	loop invariant 0<=i<=patternLength-1;
	loop assigns i, ;
	loop variant patternLength-1-i;
*/
for (int i = 1, length = 0; i < patternLength;) {
        if (pattern[i] == pattern[length]) {
            lps[i++] = ++length;
        } else if (length != 0) {
            length = lps[length - 1];
        } else {
            lps[i++] = 0;
        }
    }

    /*@
	requires textLength>0;
	loop invariant 0<=i<=textLength-1;
	loop assigns i, ;
	loop variant textLength-1-i;
*/
for (int i = 0; i < textLength;) {
        if (pattern[j] == text[i]) {
            j++, i++;
        }
        if (j == patternLength) {
            return i - j;
        } else if (i < textLength && pattern[j] != text[i]) {
            j ? j = lps[j - 1] : i++;
        }
    }
    return -1;
}
