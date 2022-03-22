/* object-flow contains the base types and flow extensions */

#include <stdint.h> 
#include <stdio.h> 

#define time_t uint32_t
#define true 1
#define false 0

/* 
Well-known reusable Resource Types, should be in a header made from the SDF translator 
*/
// Free resource range 26231-32768
// Free object range 42769-65535 (?)
// link types for pull and push data transfer
#define InputLinkType 27000
#define OutputLinkType 27001
// Value types for data connection endpoints
#define InputValueType 27002
#define CurrentValueType 27003
#define OutputValueType 27004
// Timer data types for wrap-around-safe interval activation 
#define CurrentTimeType 27005
#define IntervalTimeType 27006
#define LastActivationTimeType 27007

namespace ObjectFlow

{
  /* common types */

  struct InstanceLink {
    uint16_t typeID;
    uint16_t instanceID;
  };

  enum ValueType { booleanType, integerType, floatType, stringType, linkType, timeType };

  union AnyValueType {
    bool booleanType;
    int integerType;
    double floatType;
    char* stringType;
    InstanceLink linkType;
    time_t timeType;
  };

  struct InstanceTemplate {
    uint16_t objectTypeID;
    uint16_t objectInstanceID;
    uint16_t resourceTypeID;
    uint16_t resourceInstanceID;
    ValueType valueType;
    AnyValueType value;
  };

  /* base classes */

  /* Resource: expose values and chain together into a linked list for each object*/
  class Resource {
    public:
      uint16_t typeID;
      uint16_t instanceID;    
      Resource* nextResource;
      ValueType valueType;
      AnyValueType value;
  // Construct with type and instance + value type
      Resource(uint16_t type, uint16_t instance, ValueType vtype);
  };


  /* Objects contain a collection of resources and some bound methods and chain into a linked list */
  /* Bound methods are extended for application function types */
  class Object {
    public:
      uint16_t typeID; // could be private 
      uint16_t instanceID;
      Object* nextObject; // next Object in the chain
      Object* firstObject; // first Object in the ObjectList
      Resource* firstResource; // first resource in the list for this object

      // Construct with type and instance and empty list
      Object(uint16_t type, uint16_t instance, Object* listFirstObject);   

      // Interface to create a new resource in this object
      Resource* newResource(uint16_t type, uint16_t instance, ValueType vtype);

      // Interfaces to select Resources and Objects by their IDs

      // return a pointer to the first resource in this object that matches the type and instance
      Resource* getResourceByID(uint16_t type, uint16_t instance);

      // return a pointer to the first object in the Object list that matches the type and instance
      Object* getObjectByID(uint16_t type, uint16_t instance);

      // Value Interfaces
      
      // Interface to Read Value

      AnyValueType readValueByID(uint16_t type, uint16_t instance); 
      
      // Interface to Update Value 

      void updateValueByID(uint16_t type, uint16_t instance, AnyValueType value);

      // Application logic overrides this method
      void onValueUpdate(uint16_t type, uint16_t instance, AnyValueType value); 

      /* 

      Flow Extension to the basic object model
      
      Object state can be sync'ed (transferred from one object to another) using inputLinks
      or OutputLinks. InputLinks will cause a read operation to be performed on the linked 
      source object and the value used to set the state of this object (pull pattern). 
      Output links will cause an update operation on the linked object using the state of 
      this object (push pattern).

      When the state of objects are sync'ed, the state is copied from a default resource
      in the source object to a default resource in the destination object. The default
      source object resource is chosen by a priority ranking of 1. OutputValue, 2. CurrentValue
      and 3. InputValue. I.e. if there is no OutputValue resource, CurrentValue is chosen, etc.
      The default resource for destination object is chosen by priority ranking of
      1. InputValue, 2. CurrentValue, and 3. OutputValue

      the highest priority resource type that exists is chosen for each endpoint of the state transfer
      For Example:

      Source               Destination
      ------               -----------
      OutputValue  ======> InputValue >> Transfer is from OutputValue to InputValue
      CurrentValue         CurrentValue
      InputValue           OutputValue

      (no OutputValue)     (no InputValue)
      CurrentValue ======> CurrentValue  >> Transfer is from CurrentValue to CurrentValue 
      InputValue           OutputValue

      (no OutputValue)     (no InputValue)
      CurrentValue   ==|   (no CurrentValue)   
      (no InputValue)  |=> OutputValue  >> Transfer is from CurrentValue to OutputValue

      */

      // Copy Value from input link => this Object 
      void syncFromInputLink(); 

      // Copy Value from this Object => all output links 
      void syncToOutputLink(); 

      // extended interface for default value sync
      AnyValueType readDefaultValue(); 

      // extended interface for default value sync
      void updateDefaultValue(AnyValueType value); 

      /* 
      Timer extension
      */
      // Update CurrentTime value on Object and maybe call onInterval
      void updateCurrentTime(time_t timeValue); 

      /*
      Internal Interface extension, application logic is implemented by extending/overriding these methods
      */

      // Handler for Timer Interval
      virtual void onInterval(); 

      // Handler for DefaultValue update, called from either input or output sync
      virtual void onDefaultValueUpdate(); 

      // Handler to return value in response to input sync from another object
      virtual AnyValueType onInputSync(); 
  };

  class ObjectList {
    public:
      // construct with an empty object list
      ObjectList();
      // Linked list of Objects
      Object* firstObject; 

      // make a new object and add it to the list
      Object* newObject(uint16_t type, uint16_t instance);
      
      // return an application-specialized object based on typeID
      // The implementation for this is in handlers.cpp, code gen with applicationtypes
      Object* applicationObject(uint16_t type, uint16_t instance, Object* firstObject);

      // return a pointer to the first object that matches the type and instance
      Object* getObjectByID(uint16_t type, uint16_t instance);
      
      void buildInstances();

      void displayObjects();
  };

}
