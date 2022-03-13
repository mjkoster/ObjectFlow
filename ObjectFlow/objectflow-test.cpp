#include "objectflow.h"
#include "instances.h"

using namespace ObjectFlow;

int main() {
  ObjectList rtu;
  Object* object = rtu.newObject(9999,1);
  object -> newResource(1111, 1, integerType);
  object -> updateValueByID(1111, 1, (AnyValueType){.integerType=100});
  object -> newResource(2222, 2, floatType);
  object -> updateValueByID(2222, 2, (AnyValueType){.floatType=101.1});
  object = rtu.newObject(9090,2);
  object -> newResource(1010, 1, integerType);
  object -> updateValueByID(1010, 1, (AnyValueType){.integerType=1001});
  object -> newResource(1010, 2, floatType);
  object -> updateValueByID(1010, 2, (AnyValueType){.floatType=1001.01});

  rtu.displayObjects();
  return(0);
};


