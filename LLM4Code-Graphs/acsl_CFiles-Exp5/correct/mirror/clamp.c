int clamp(int x, int min, int max) {
    return (x < min) ? min : (x > max) ? max : x;
}
