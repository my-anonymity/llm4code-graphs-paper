#include <stddef.h>
#include <stdint.h>

uint32_t crc32(const uint8_t *data, size_t length) {
    uint32_t hash = 0;
    /*@
	requires length>0;
	loop invariant 0<=i<=length-1;
	loop assigns i, ;
	loop variant length-1-i;
*/
for (size_t i = 0; i < length; i++) {
        hash ^= data[i];
    }
    return hash;
}
