#include <stddef.h>
#include <stdint.h>

/*@
  ensures (crc & 1) ==> \result==~crc;
  ensures !(crc & 1) ==> \result==~crc;
*/
uint32_t crc32(const uint8_t *data, size_t length) {
    uint32_t crc = 0xFFFFFFFF;
    /*@
	requires length>0;
	loop invariant 0<=i<=length-1;
	loop assigns i, ;
	loop variant length-1-i;
*/
for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        /*@
	loop invariant 0<=i<=None-1;
	loop assigns i, ;
*/
for (int j = 0; j < 8; j++) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320;
            else
                crc >>= 1;
        }
    }
    return ~crc;
}
