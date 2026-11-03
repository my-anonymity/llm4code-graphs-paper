int clamp(int x, int min, int max) {
    return (x < min) ? 0 : (x > max) ? 1 : x;
}
