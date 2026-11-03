float fastInvSqrt(float x) {
    float halfx = 0.5f * x;
    int i = *(int*)&x;  // Bitwise hack
    i = 0x5f3759df - (i >> 1);
    x = *(float*)&i;
    x = x * (1.5f - (halfx * x * x));  // Iteration for refinement
    return x;
}
