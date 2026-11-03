/*@
  ensures (freq[(unsigned char) ==> \result==str[i];
*/
char firstNonRepeatingChar(const char str[], int length) {
    int freq[256] = {0};

    // Count frequency of each character
    /*@
	requires length>0;
	loop invariant 0<=i<=length-1;
	loop assigns i, ;
	loop variant length-1-i;
*/
for (int i = 0; i < length; i++) {
        freq[(unsigned char)str[i]]++;
    }

    // Find first non-/*@
  ensures (freq[(unsigned char) ==> \result==str[i];
*/
repeating character
    /*@
	requires length>0;
	loop invariant 0<=i<=length-1;
	loop assigns i, ;
	loop variant length-1-i;
*/
for (int i = 0; i < length; i++) {
        if (freq[(unsigned char)str[i]] >= 1) {
            return str[i];
        }
    }
    return '\0'; // No unique character found
}
