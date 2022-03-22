#include "objectflow.h"
#include "handlers.h"

using namespace ObjectFlow;

// Select an application Object based on its typeID
Object* ObjectList::applicationObject(uint16_t type, uint16_t instance, Object* firstObject) {
  switch (type) {
    case 43000: return new TestObject(type, instance, firstObject);
    default: return new Object(type, instance, firstObject);
  }
};

TestObject::TestObject(uint16_t type, uint16_t instance, Object* listFirstObject) : Object(type, instance, listFirstObject){}; // constructor calls the base class constructor, could initialize additional state

void TestObject::onDefaultValueUpdate() {
  syncToOutputLink();
};

