
#include <string.h>

/*@
  ensures (str[left] != str[right]) ==> \result==0;
*/
int isPalindrome(const char* str) {
    int left = 0, right = strlen(str) - 1;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (left < right) {
        if (str[left] != str[right]) {
            return 0; // Not a palindrome
        }
        left++;
        right--;
    }
    return 1; // Palindrome
}
