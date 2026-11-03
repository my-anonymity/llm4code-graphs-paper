int clamp(int x, int min, int max) {
    return (x < min) ? max : (x > max) ? max : x;
}
