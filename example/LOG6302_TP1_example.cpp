class Foo {

public:
    int x;

    int bar() {
        if (false) {
            return 42;
        } else if (1 == 1) {
            return 12;
        } else {
            return 1;
        }
        for (int i = 0; i < -1; i++);
        return -1;
    }

    int bow() {
        if (false)
            return 42;
        else if (1 == 1)
            return 12;
        else
            return 1;
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
