namespace ObjectFlow
{
  class TestObjectType: Object {
    public:
      TestObjectType(uint16_t type, uint16_t instance, Object* listFirstObject);   
      void onDefaultValueUpdate(AnyValueType value);
  };
}