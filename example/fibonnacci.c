unsigned int fib(unsigned int n){
    unsigned int i = n - 1, a = 1, b = 0, c = 0, d = 1, t;
    if (n <= 0)
        return 0;
    while (i > 0){
        while (i % 2 == 0){
            t = d*(2*c + d);
            c = c*c + d*d;
            d = t;
            i = i / 2;
        }
        t = d*(b + a) + c*b;
        a = d*b + c*a;
        b = t;
        i--;
    }
    return a + b;
}