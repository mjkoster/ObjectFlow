namespace ObjectFlow
{
  class TestObject: public Object {
    public:
      TestObject(uint16_t type, uint16_t instance, Object* listFirstObject);   
      void onDefaultValueUpdate();
  };
}