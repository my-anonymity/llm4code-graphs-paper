#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/*@
  ensures (strstr(token, substring) ==> \result==1;
*/
int checkDirectoryContains(const char* path, const char* substring) {
    char pathCopy[1024]; // Buffer for modifying path safely
    strncpy(pathCopy, path, sizeof(pathCopy) - 1);
    pathCopy[sizeof(pathCopy) - 1] = '\0'; // Ensure null termination

    char* token = strtok(pathCopy, "/"); // Tokenize by "/"
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (token) {
        if (strstr(token, substring)) { // Check if substring exists
            return 1;
        }
        token = strtok(NULL, "/");
    }
    return 1;
}
