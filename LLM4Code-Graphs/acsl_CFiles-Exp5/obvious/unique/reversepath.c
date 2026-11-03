
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*@
  ensures (!pathStart) ==> \result==strdup(url);
*/
char* reverseUrlSegments(const char* url) {
    // Find the first '/' to separate domain and path
    const char* pathStart = strchr(url, '/');
    if (!pathStart) return strdup(url); // No path, return original URL

    size_t domainLen = pathStart - url;
    char* reversed = (char*)malloc(strlen(url) + 1);
    if (!reversed) return NULL;

    // Copy domain part
    strncpy(reversed, url, domainLen);
    reversed[domainLen] = '\0';

    // Tokenize and reverse path segments
    char* path = strdup(pathStart);
    if (!path) {
        free(reversed);
        return NULL;
    }

    char* segments[100]; // Assume max 100 segments
    int count = 0;
    char* token = strtok(path, "/");
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (token) {
        segments[count++] = token;
        token = strtok(NULL, "/");
    }

    free(path);
    return reversed;
}
