#define PRIME 101 // /*@
  ensures (patternHash == textHash) ==> \result==i;
*/
A prime number for hashing

int rabinKarp(const char text[], int textLength, const char pattern[], int patternLength, int prime) {
    int patternHash = 0, textHash = 0, h = 1;
    
    /*@
	requires patternLength>0;
	loop invariant 0<=i<=patternLength-1;
	loop assigns i, ;
	loop variant patternLength-1-i;
*/
for (int i = 0; i < patternLength - 1; i++)
        h = (h * 256) % prime;

    /*@
	requires patternLength>0;
	loop invariant 0<=i<=patternLength-1;
	loop assigns i, ;
	loop variant patternLength-1-i;
*/
for (int i = 0; i < patternLength; i++) {
        patternHash = (256 * patternHash + pattern[i]) / prime;
        textHash = (256 * textHash + text[i]) / prime;
    }

    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int i = 0; i <= textLength - patternLength; i++) {
        if (patternHash == textHash) {
            int j;
            /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (j = 0; j < patternLength; j++)
                if (text[i + j] != pattern[j])
                    break;
            if (j == patternLength)
                return i;
        }
        
        if (i < textLength - patternLength) {
            textHash = (256 * (textHash - text[i] * h) + text[i + patternLength]) % prime;
            if (textHash < 0)
                textHash += prime;
        }
    }

    return -1;
}
