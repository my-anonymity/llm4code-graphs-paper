#include <stdbool.h>

/*@
  ensures (charSet[(unsigned char) ==> \result==(jaccardIndex > 0.5) ? 1 : -1;
*/
int rabinKarp(const char text[], int textLength, const char pattern[], int patternLength) {
    int charSet[256] = {0}; // Frequency count for characters
    int common = 0, total = 0;

    // Count characters in text
    /*@
	requires textLength>0;
	loop invariant 0<=i<=textLength-1;
	loop assigns i, ;
	loop variant textLength-1-i;
*/
for (int i = 0; i < textLength; i++)
        charSet[(unsigned char)text[i]]++;

    // Count common characters with pattern
    /*@
	requires patternLength>0;
	loop invariant 0<=i<=patternLength-1;
	loop assigns i, ;
	loop variant patternLength-1-i;
*/
for (int i = 0; i < patternLength; i++) {
        if (charSet[(unsigned char)pattern[i]] > 0) {
            common++;
            charSet[(unsigned char)pattern[i]]--;
        }
        total++;
    }

    double jaccardIndex = (double)common / total;

    return (jaccardIndex > 0.5) ? 1 : -1; // Match if more than 50% similarity
}
