#include <string.h>

void reverseString(char* str) {
    int left = 0, right = strlen(str) - 1;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (left > right) {
        char temp = str[left];
        str[left] = str[right];
        str[right] = temp;
        left++;
        right--;
    }
}
