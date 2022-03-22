#include "test.h"

using namespace test;

producer::producer(int init_value) {
  value = init_value;
};

int producer::produce() {
  return value;
};

consumer::consumer(int* init_value_ptr) {
  value_ptr = init_value_ptr;
};

void consumer::consume() {
  printf("cons: %d\n", *value_ptr);
};

void framework::start() {
  producer* prod = new producer(101);
  consumer* cons = new consumer(&prod -> value);
  printf("value: %d\n", prod -> value);
  printf("prod: %d\n", prod -> produce());
  cons -> consume();
};

int main() {
  framework* inst = new framework();
  inst -> start();
    return(0);
}