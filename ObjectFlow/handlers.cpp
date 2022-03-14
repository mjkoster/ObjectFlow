#include "objectflow.h"
#include "handlers.h"

using namespace ObjectFlow;

void TestObjectType::onDefaultValueUpdate(AnyValueType value) {
  syncToOutputLink();
};
