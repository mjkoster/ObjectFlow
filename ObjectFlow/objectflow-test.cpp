#include "objectflow.h"

using namespace ObjectFlow;

int main() {
  ObjectList rtu;
  rtu.buildInstances();
  rtu.displayObjects();
  Object* object1 = rtu.getObjectByID(43001,0);
  AnyValueType value = object1 -> onInputSync();
  printf ("%d\n", value.integerType);
  rtu.displayObjects();
  Object* object = rtu.getObjectByID(43000,0);
  object -> syncFromInputLink();
  rtu.displayObjects();
  return(0);
};
