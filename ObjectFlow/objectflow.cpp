/* objectflow contains the base types and flow extensions */

#include "objectflow.h"

using namespace ObjectFlow;

/* Resource: expose values and chain together into a linked list for each object*/

Resource::Resource(uint16_t type, uint16_t instance, ValueType vtype) {
typeID = type;
instanceID = instance;
valueType = vtype;
nextResource = NULL;
};

/* Objects contain a collection of resources and some bound methods and chain into a linked list */
/* Bound methods are extended for application function types */
  // Construct with type and instance and empty list
Object::Object(uint16_t type, uint16_t instance, Object* listFirstObject) {
      typeID = type;
      instanceID = instance;
      firstResource = NULL;
      nextObject = NULL;
      firstObject = listFirstObject;
};   

// Interface to create a new resource in this object
Resource* Object::newResource(uint16_t type, uint16_t instance, ValueType vtype) {
  // find last resource in the chain
  if (NULL == firstResource) { // make first resource instance in the list and add to this object
    this -> firstResource = new Resource(type, instance, vtype );
    return firstResource;
  }
  else { // already have first resource
    Resource* resource = firstResource;
      while (resource -> nextResource != NULL) {
        resource = resource -> nextResource;
      };
    // make instance and add the new resource to the list
    resource -> nextResource = new Resource(type, instance, vtype );
    return resource -> nextResource;
  };
};

// Interfaces to select Resources and Objects by their IDs

// return a pointer to the first resource in this object that matches the type and instance
Resource* Object::getResourceByID(uint16_t type, uint16_t instance) {
  Resource* resource = firstResource;
  while ( (resource != NULL) && (resource -> typeID != type || resource -> instanceID != instance) ) {
    resource = resource -> nextResource;
  };
  return resource; // returns NULL if resource doesn't exist
};

// return a pointer to the first object in the Object list that matches the type and instance
Object* Object::getObjectByID(uint16_t type, uint16_t instance) {
  Object* object = firstObject;
  while (object != NULL && (object -> typeID != type || object -> instanceID != instance)) {
    object = object -> nextObject;
  };
  return object; // returns NULL if doesn't exist
};

// Value Interfaces
  
// Interface to Read Value

AnyValueType Object::readValueByID(uint16_t type, uint16_t instance) {
  Resource* resource = getResourceByID(type, instance);
  AnyValueType returnValue;
  if (resource != NULL) {
    return resource -> value;
  }
  else {
    printf ("NULL in readValueByID\n"); // should throw an error
  return(returnValue); // returns uninitialized value union if there is no candidate
  }
}; 

// Interface to Update Value 

void Object::updateValueByID(uint16_t type, uint16_t instance, AnyValueType value) {
  Resource* resource = getResourceByID(type, instance);
  if (resource != NULL) {
    resource -> value = value;
  onValueUpdate(type, instance, value); // call the update handler
  }
  else {
    printf("NULL in updateValueByID\n");
  };
};

// Application logic extends this method
void Object::onValueUpdate(uint16_t type, uint16_t instance, AnyValueType value) {}; 

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
void Object::syncFromInputLink() {
  // readDefaultValue from InputLink
  // updateDefaultValue on this object
  Resource* inputLink = getResourceByID(InputLinkType,0);
  if (inputLink != NULL) {
    Object* sourceObject = getObjectByID(inputLink -> value.linkType.typeID, inputLink -> value.linkType.instanceID);
    updateDefaultValue(sourceObject -> onInputSync()); // call onInputSync of the source object to get dynamic values
    onDefaultValueUpdate(); // call onValueUpdate to initiate local handling of the update 
  }
}; 

// Copy Value from this Object => all output links 
void Object::syncToOutputLink() {
  // readDefaultValue from this object
  // updateDefaultValue to OutputLink(s)
  AnyValueType value = readDefaultValue();
  Resource* resource = firstResource;
    while ( (resource != NULL) ) {
      if (OutputLinkType == resource -> typeID) { // process all output links
        Object* object = getObjectByID(resource -> value.linkType.typeID, resource -> value.linkType.instanceID);
        object -> updateDefaultValue(value);
      };
    resource = resource -> nextResource;
  }; 
}; 

// extended interface for default value sync
AnyValueType Object::readDefaultValue() {
  AnyValueType returnValue;
  Resource* resource = getResourceByID(OutputValueType,0);
  if (resource != NULL) {
    return(resource -> value);
  };
  resource = getResourceByID(CurrentValueType,0);
  if (resource != NULL) {
    return(resource -> value);
  };
  resource = getResourceByID(InputValueType,0);
  if (resource != NULL){
    return(resource -> value);
  };
  printf("readDefault couldn't find a candidate resource\n"); // should throw an error
  return(returnValue); // returns uninitialized value union if there is no candidate
}; 

// extended interface for default value sync
void Object::updateDefaultValue(AnyValueType value) {
  // prioritized resource types, update value and call onUpdate
  Resource* resource = getResourceByID(InputValueType,0);
  if (resource != NULL) {
    resource -> value = value;
    //onValueUpdate(resource -> typeID, resource -> instanceID, value);
    onDefaultValueUpdate();
    return;
  };
  resource = getResourceByID(CurrentValueType,0);
  if (resource != NULL) {
    resource -> value = value;
    onDefaultValueUpdate();
    return;
  };
  resource = getResourceByID(OutputValueType,0);
  if (resource != NULL){
    resource -> value = value;
    onDefaultValueUpdate();
    return;
  };
  printf("updateDefaultValue couldn't find a candidate resource\n"); // should throw an error
  return;
}; 

/* 
Timer extension
*/
// Update CurrentTime value on Object and maybe call onInterval
void Object::updateCurrentTime(time_t timeValue) {
  // update current time
  // interval time check is wrap-safe if time variable and HW timer both have time_t wrap behavior
  // if(current time - last activation time >= interval time){ update last activation time and call onInterval }
  Resource* currentTime = getResourceByID(CurrentTimeType, 0);
  Resource* intervalTime = getResourceByID(IntervalTimeType, 0);
  Resource* lastActivationTime = getResourceByID(LastActivationTimeType, 0);
  currentTime -> value.timeType = timeValue;
  if (timeValue - lastActivationTime -> value.timeType >= intervalTime -> value.timeType) {
    lastActivationTime -> value.timeType = timeValue;
    onInterval();
  }
}; 

/*
Internal Interface extension, application logic is implemented by extending/overriding these methods
*/

// Handler for Timer Interval
void Object::onInterval() {}; 

// Handler for DefaultValue update, called from either input or output sync
void Object::onDefaultValueUpdate() {}; 

// Handler to return value in response to input sync from another object
AnyValueType Object::onInputSync() {
  return readDefaultValue(); // Default read value, override for e.g. gpio read
}; 

// construct with an empty object list
ObjectList::ObjectList() {
  firstObject = NULL;
};

Object* ObjectList::newObject(uint16_t type, uint16_t instance) {
  // find the last object in the chain, has a null nextobject pointer
  // FIXME check if it already exists?
  if (NULL == firstObject) { // make first object and add to the list (sets property of the ObjectList)
    this -> firstObject = new Object(type, instance, firstObject);
    return firstObject;
  }
  else { // already have the first object, find the end of the list 
    Object* object = firstObject;
    while (object -> nextObject != NULL) {
      object = object -> nextObject;
    };
    // make instance and add the new resource (sets property of the last Object)
    object -> nextObject = new Object(type, instance, firstObject);
    return object -> nextObject; 
  };     
};

// return a pointer to the first object that matches the type and instance
Object* ObjectList::getObjectByID(uint16_t type, uint16_t instance) {
  Object* object = firstObject;
  while (object != NULL && (object -> typeID != type || object -> instanceID != instance)) {
    object = object -> nextObject;
  };
  return object; // returns NULL if doesn't exist
};

void ObjectList::displayObjects() {
  Object* object = firstObject;
  while ( object != NULL) {
    printf ( "[%d, %d]\n", object -> typeID, object -> instanceID);
    Resource* resource = object -> firstResource;
    while ( resource != NULL) {
      printf ( "  [%d, %d] ", resource -> typeID, resource -> instanceID);
      printf ( "value type %d, ", resource -> valueType);
      printf ( "value = ");
      switch(resource -> valueType) {
        case booleanType: {
          printf ( "%s\n", resource -> value.booleanType ? "true": "false");
          break;
        }
        case integerType: {
          printf ( "%d\n", resource -> value.integerType);
          break;
        }
        case floatType: {
          printf ( "%f\n", resource -> value.floatType);
          break;
        }
        default:
          printf ("\n");
      }
      resource = resource -> nextResource;
    };
    object = object -> nextObject;
  };
};

/*
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
  */

