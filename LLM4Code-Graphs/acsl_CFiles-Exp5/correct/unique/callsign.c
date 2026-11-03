#include <ctype.h>
#include <string.h>

#define MAX_WORDS 26
#define MAX_LENGTH 10

// NATO Phonetic Alphabet
const char* NATO[] = {
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India",
    "Juliett", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo",
    "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "X-ray", "Yankee", "Zulu"
};

/*@
  ensures (isalpha(input[i]) ==> \result==count;
*/
int stringToNato(const char* input, char output[MAX_WORDS][MAX_LENGTH]) {
    int count = 0;
    
    /*@
	loop invariant 0<=i<=None-1;
	loop invariant \forall integer i; 0<=i<i ==> input[i] >= input[i];
	loop assigns i, input[0..i+1];
*/
for (int i = 0; input[i] != '\0' && count < MAX_WORDS; i++) {
        if (isalpha(input[i])) {
            strcpy(output[count], NATO[tolower(input[i]) - 'a']);
            count++;
        }
    }
    return count; // Return number of words stored
}
