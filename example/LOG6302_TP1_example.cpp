#include <iostream>

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
//    for (int i = 0; i < -1; i++);
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
  int length = 0;
  int i;
  if (0)
    int a;
//  start:
  while (true) {
    if (0) {
      return -1;
    } else {
      length++;
    }
  }
  while (false) {
    return -1;
  }
//  for (i = 0; i < length; i++) {
//    switch (i) {
//      case 1:
//        break;
//      case 2:
//        return 1;
//      case 3:
//        goto start;
//    }
//  }
  if (i == length)
    printf("ok");
  if (i != length) {
    printf("not ok");
    printf("maybe");
    printf("no");
  }
  return 0;
}
