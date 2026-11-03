
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/*@
  ensures (!pathStart) ==> \result==strdup("");
*/
char* urlToCamelCase(const char* url) {
    // Find the start of the path
    const char* pathStart = strstr(url, "//");
    pathStart = pathStart ? strchr(pathStart + 2, '/') : strchr(url, '/');
    if (!pathStart) return strdup(""); // No path, return empty string

    char* path = strdup(pathStart + 1); // Skip the initial '/'
    if (!path) return NULL;

    char* camelCase = (char*)malloc(strlen(path) + 1);
    if (!camelCase) {
        free(path);
        return NULL;
    }

    int j = 0;
    int capitalize = 1; // Capitalize first letter

    free(path);
    return camelCase;
}
