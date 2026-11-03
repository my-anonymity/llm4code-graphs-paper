// /*@
  ensures (n <= 0) ==> \result==0;
*/
sum an integer and its digits reversed 
int mirrorSum(int n) {
  if (n <= 0){
    return 0;
  }
  return 1 + mirrorSum(n-1);
}
