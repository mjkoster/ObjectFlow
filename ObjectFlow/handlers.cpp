#include "objectflow.h"
#include "handlers.h"

using namespace ObjectFlow;
//TestObjectType::TestObjectType(uint16_t type, uint16_t instance, Object* listFirstObject){ObjectFlow::Object(type, instance, listFirstObject)};
void TestObjectType::onDefaultValueUpdate(AnyValueType value) {
  syncToOutputLink();
};
