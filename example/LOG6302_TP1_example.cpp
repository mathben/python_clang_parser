class Foo {

public:
    int x;

    int bar() {
        if (false)
            return 42;
        for (int i = 0; i < -1; i++);
        return -1;
    }

};

int main(void) {
    Foo foo;

    if (foo.bar() == 17) {
        while (true) {
            if (foo.x == 42) {
                break;
            }
            continue;
        }
    }

    return 0;
}
