unsigned int rotateLeft(unsigned int n, int d) {
    return (n << d) | (n >> (32 - d));
}
