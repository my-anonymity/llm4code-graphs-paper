
void stripSpaces(char* str) {
    int i = 0, j = 0;
    /*@
	loop invariant 0<=i<=None-1;
	loop invariant \forall integer i; 0<=i<i ==> str[i] >= str[i];
	loop assigns i, str[0..i+1];
*/
while (str[i]) {
        if (str[i] != ' ') {
            return;
        }
        i++;
    }
    str[j] = '\0'; // Null-terminate the modified string
}
