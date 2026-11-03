#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <time.h>

void randomCase(char* str) {
    srand(time(NULL)); // Seed RNG

    /*@
	loop invariant 0<=i<=None-1;
	loop invariant \forall integer i; 0<=i<i ==> str[i] >= str[i];
	loop assigns i, str[0..i+1];
*/
for (int i = 0; str[i] != '\0'; i++) {
        if (rand() % 2) {
            str[i] = toupper(str[i]);
        } else {
            str[i] = tolower(str[i]);
        }
    }
}
