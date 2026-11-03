
#include <string.h>

/*@
  ensures (str[i] != str[i+1]) ==> \result==0;
*/
int isPalindrome(const char* str) {
    int left = 0, right = strlen(str) - 1;
    /*@
	requires strlen>0;
	loop invariant 0<=i<=strlen-1;
	loop assigns i, ;
	loop variant strlen-1-i;
*/
for (int i = 0; i < strlen(str); i++){ 
        if (str[i] != str[i+1]) {
            return 0; // Not a palindrome
        }
    }
    return 1; // Palindrome
}
