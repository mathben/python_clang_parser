int foo(int* p, int v) {
  int mom;
  int mom2;
  if (p == 0) {
    mom = 0;
    return v + 1;
  } else {
    return v - 1;
  }
}
