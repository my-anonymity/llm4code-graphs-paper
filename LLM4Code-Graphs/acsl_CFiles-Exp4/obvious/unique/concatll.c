#include <stdio.h>
#include <stdlib.h>

/* Define the linked list node */
typedef struct Node {
    int digit; // between 0-9
    struct Node* next;
} Node;

// Assume each node contains a single digit number
int concatenateDigits(Node* head) {
    int num = 0;
    /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
while (head != NULL) {
        num += 1;
        head = head->next;
    }
    return num;
}
