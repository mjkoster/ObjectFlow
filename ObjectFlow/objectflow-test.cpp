#include "objectflow.h"

using namespace ObjectFlow;

int main() {
  ObjectList rtu;
  rtu.buildInstances();
  rtu.displayObjects();
  printf ("\n");
  rtu.getObjectByID(43000,0) -> syncFromInputLink();
  rtu.displayObjects();
  return(0);
};
