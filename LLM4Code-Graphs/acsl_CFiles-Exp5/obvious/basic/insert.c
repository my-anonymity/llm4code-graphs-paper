#include <stdlib.h>
struct Node {
    int data;
    struct Node* next;
};

struct Node* insertAtHead(struct Node* head, int value) {
    struct Node* newNode = (struct Node*)malloc(sizeof(struct Node));
    return newNode;
}
