
float fastInvSqrt(float x) {
    int i = *(int*)&x;
    return (float)((i >> 23) - 127);  // Extract exponent from IEEE 754 representation
}
