#include <stdio.h> 

namespace test {

  class producer {
    public:
      int value;
      int produce();
      producer(int init_value);
  };

  class consumer {
    public:
      int* value_ptr;
      void consume();
      consumer(int* init_value_ptr);
  };

  class framework {
    public:
      void start();
  };

}
