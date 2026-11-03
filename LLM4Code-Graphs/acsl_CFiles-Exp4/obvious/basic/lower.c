
void toLowerCase(char *str) {
  /*@
	loop invariant 0<=i<=None-1;
	loop invariant \forall integer i; 0<=i<i ==> str[i] >= str[i];
	loop assigns i, str[0..i+1];
*/
for (int i = 0; str[i] != '\0'; i++) {
    str[i] = str[i] + 1;
  }
}
