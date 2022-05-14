
import json
import yaml
import glob
from jsonpointer import resolve_pointer
import copy
import subprocess

class Graph():
# class Graph(dict):
  def __init__(self, spec={}):
    self._graph = {}
    self.add(spec)

  def add(self, model):
    self._merge(model) 

  def _merge(self, model):
  # RFC7386 style merge-patch + uniqueItem list merge
  # recursive descent merge JSON, extend trees and set values
  # for each item in the model, check the position in the graph
  # add to graph if not present until the end value is reached 
  # set the end value (const doubles with default as they are dicts)
  # arrays are merged assuming uniqueItems, leaving the set union
    self._graph = self._mergeObject(self._graph, model) # kick off the recursion

  def _mergeObject(self, base, patch):
    if not isinstance(base, dict):
      base = {}

    if not isinstance( patch, dict):
      return patch

    for key, patchItem in patch.items():
      if isinstance(patchItem, dict): 
        baseValue = base.get(key) # key error safe this way
        if isinstance(baseValue, dict): # see if there is a matching dict in the base
          self._mergeObject(base[key], patchItem) # if so, merge the patch value into the base
          continue
        base[key] = {} # if there isn't a dict there, make a new empty node merge dict into it
        self._mergeObject(base[key], patchItem)
        continue
      if isinstance(patchItem, list):      
        baseValue = base.get(key) # key error safe this way
        if isinstance(baseValue, list): # see if there is a matching list
          baseValue = list(set(baseValue + patchItem)) # merge lists with unique values
          continue
      if None is patchItem: # if the patch contains None, remove the matching node in the base
        base.pop(key, None)
        continue
      base[key] = patchItem # replace empty or plain value with value from the patch
    return base

  def graph(self):
    return self._graph

  def resolve(self, pointer):
    return resolve_pointer(self._graph, pointer)

  def json(self):
    # options go here
    return json.dumps( self.graph() ) 

  def yaml(self):
    # options go here
    return yaml.dump( self.graph() ) 


class ModelGraph(Graph):
  def __init__(self, modelPath):
    Graph.__init__(self)
    # read in all of the SDF files in the model directory
    for file in glob.glob( modelPath + "*.sdf.json" ):
      print(file)
      self.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( modelPath + "*.sdf.yml" ):
      print(file)
      self.add( yaml.safe_load( open(file,"r").read() ) )
    self._checkPointers()

  # validate that all of the sdfRef and sdfRequired resolve to some place in the merged graph
  # recursive scan for instances of these keys and resolve the references
  # allow sdfRef in any object type node of the instance
  # 
  def _checkPointers(self):
    self._errors = 0
    self._check(self.graph())

  def _check(self, value):
    if isinstance(value, dict):
      if "sdfRef" in value:
        self._checkResolve(value["sdfRef"])
      if "sdfRequired" in value:
        for ref in value["sdfRequired"]:
          self._checkResolve(ref)
      for item in value:
        self._check(value[item])

  def _checkResolve(self, sdfPointer):
    self._pointer = sdfPointer
    if self._pointer.startswith("/#"):
      self._pointer = self._pointer[2:]
    elif self._pointer.startswith("#"):
      self._pointer = self._pointer[1:]
    if self._pointer.startswith("/"):
      try:
        target = self.resolve(self._pointer)
      except:
        print("sdfPointer doesn't resolve:", self._pointer)
        self._errors += 1
        return
      return(target)
    else:
      return(self._resolveNamespaceReference(self._pointer)) # resolve curie

  def _resolveNamespaceReference(self, sdfPointer):
    print("Namespace not supported: ", sdfPointer)
    raise 
    return # feature

  def errors(self):
    # collect pointer errors after the pointer check is done
    return self._errors

  def idList(self):
  # return a list of types sorted by ID, for diagnostics and documantation
    objectType = (self.resolve("/sdfData/TypeID/ObjectType"))
    resourceType = (self.resolve("/sdfData/TypeID/ResourceType"))
    idList = {}
    idList["ObjectType"] = []
    idList["ResourceType"] = []
    for type in objectType:
      idList["ObjectType"].append( { objectType[type]["const"] : type } )
      idList["ObjectType"] = sorted( idList["ObjectType"], key=lambda d: list(d.keys()) )
    for type in resourceType:
      idList["ResourceType"].append( { resourceType[type]["const"] : type } )
      idList["ResourceType"] = sorted( idList["ResourceType"], key=lambda d: list(d.keys()) )
    return yaml.dump(idList)

  def resourceHeader(self):
  # return a C++ header fragment defining resource type aliases
  # #include this fragment in the objectflow.h file
  # 
    resourceType = (self.resolve("/sdfData/TypeID/ResourceType"))
    resourceHeaderCode = "// Resource Types generated by ObjectFlow Builder\n"
    for type in resourceType:
      resourceHeaderCode += "#define %s %d\n" % (type, resourceType[type]["const"])
    return resourceHeaderCode

  def objectHeader(self):
    # return a C++ code fragment that creates new objects using application handler names 
    # construct the code for mapping object TypeID to application object type handler name
    # #include this fragment in handlers.cpp 
    #    // Select an application Object based on its typeID
    #    Object* ObjectList::applicationObject(uint16_t type, uint16_t instance, Object* firstObject) {
    #      switch (type) {
    #        case 43000: return new TestObject(type, instance, firstObject);
    #        default: return new Object(type, instance, firstObject);
    #      }
    #    };
    # FIXME implement a way to do this with a struct in a header, use a better template pattern
    # there should be separate source files for handlers
    objectHeaderCode = """// Generated by ObjectFlow builder
// Select an application Object based on its typeID
Object* ObjectList::applicationObject(uint16_t type, uint16_t instance, Object* firstObject) {
  switch (type) {\n"""
    objectTypeList = self.resolve("/sdfData/TypeID/ObjectType")
    for objectTypeName in objectTypeList:
      objectTypeID = objectTypeList[objectTypeName]["const"]
      objectHeaderCode += "    case %d: return new %s(type, instance, firstObject);\n" % (objectTypeID, objectTypeName)
    objectHeaderCode += """    default: return new Object(type, instance, firstObject);
  }
};"""
    return objectHeaderCode

class FlowGraph(Graph):
  def __init__(self, modelGraph, flowPath):
    Graph.__init__(self, self._baseFlowTemplate())
    # 
    # Flow Graph construction involves three graphs
    #
    # The Model Graph is a merge of all the required models to build the Flow, done in the ModelGraph class
    # 
    # The Flow Spec is a special JSON format that contains only enough information to define the flow, by 
    # including the necessary object types, naming the instances, defining the input and output link connections, 
    # and setting the internal optionality of the objects, including resource profile, 
    # initial resource values, settings, and constants
    #
    # The Flow Graph is resolved from the Flow Spec, and populated with all required items and values defined in the Flow Spec 
    #
    # The ObjectFlow header, JSON and YAML serializations, and documentation are extracted from the resolved Flow Graph
    # 
    # A template for the Flow Graph is constructed and populated with "SdfRef" statements that point to 
    # templates in the model for the pre-defined object types
    # 
    # These references are expanded by first following each sdfRef in the Flow Spec back to its location and 
    # recursively following references in a chain until the "root" definition is found (expandMerge) then 
    # performing a special "refineMerge" from the root back to each refinement in the model, then finally merging
    # the marged model back into the FLow Graph
    # 
    # The Flow Graph is then pruned of the unused Resources, those not required and not specified in the Flow Spec
    #
    # Resources in the Flow Graph are then configured from values in the Flow Spec, LWM2M IDs are assigned, 
    # and finally the Object Link values are filled in with the target IDs
    #
    # When extracting values from the FLow Graph, it is necessary to override "default" values with "const" 
    # values, if "const" is defined
    #
    self._modelGraph = modelGraph

    self._flowSpec = Graph() # for the JSON DSL spec, merge these also

    for file in glob.glob( flowPath + "*.flo.json" ):
      print(file)
      self._flowSpec.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( flowPath + "*.flo.yml" ):
      print(file)
      self._flowSpec.add( yaml.safe_load( open(file,"r").read() ) )

    self._resolveFlowGraph() 

  def _resolveFlowGraph(self):
    # build a flow graph from the flow spec; resolve all required items and default values from the model graph
    #
    # the flow graph is initialized with the base template when created
    self._flowBasePath = "/sdfThing/Flow/sdfObject"
    self._flowBase = self.resolve(self._flowBasePath)
    self._flowSpecBase = self._flowSpec.graph()["Flow"]

    # for each object in the merged flow: 
    # add a named sdfObject with an sdfRef to the application object type, using a simple path reference
    # if there is no Type specified in the flow, the object name will be used as type

    for flowObject in self._flowSpecBase:
      self._flowBase[flowObject] = {}
      if not "$type" in self._flowSpecBase[flowObject]:
        self._flowSpecBase[flowObject]["$type"] = flowObject # use the name as type
      self._flowBase[flowObject]["sdfRef"] = "/sdfObject/" + self._flowSpecBase[flowObject]["$type"]

      # Expand-Merge the named objects in the flow graph from corresponding objects in the model graph
      # Expands all of the Resources in the Model graph for each object, will not add resources that are not 
      # defined for the object type.
      #
      print("Resolving ",flowObject)
      # expand and merge all sdfRefs recursively
      self._expandMergeAll(self._flowBase[flowObject])
 
      # Remove the unneeded resources and other noise from the flow template
    
      # transform the "required" array to resource names
      self._flowBase[flowObject]["requiredResources"] = []
      if "sdfRequired" in self._flowBase[flowObject]:
        for path in self._flowBase[flowObject]["sdfRequired"]:
          self._flowBase[flowObject]["requiredResources"].append( path.split("/")[-1] ) # last path segment is the resource name
      # remove properties not required or specified in the flow object
      toRemove = []
      for resource in self._flowBase[flowObject]["sdfProperty"]:
        if not resource in self._flowSpecBase[flowObject] and not resource in self._flowBase[flowObject]["requiredResources"]:
          toRemove.append(resource)
      for resource in toRemove:
        self._flowBase[flowObject]["sdfProperty"].pop(resource, None)
      #remove sdfAction and required lists
      self._flowBase[flowObject].pop("sdfAction", None)
      self._flowBase[flowObject].pop("sdfRequired", None)
      self._flowBase[flowObject].pop("requiredResources", None)


      # merge the predefined resource values from the flow spec resources to the graph resources 
      # FIXME should use mergeRefine { const: <resource> } instead of assignment to overlay const on existing definition

      for resource in self._flowBase[flowObject]["sdfProperty"]: # for each property in the sdf graph
        if resource in self._flowSpecBase[flowObject]: # if there is matching resource in the flow spec
          if isinstance(self._flowSpecBase[flowObject][resource], dict ): # merge in qualities verbatim from object value
            self._flowBase[flowObject]["sdfProperty"][resource] = self._mergeRefine(
              self._flowBase[flowObject]["sdfProperty"][resource], 
              self._flowSpecBase[flowObject][resource]
            )
          # apply as constant value - array needs to be handled when we add multi-instance support
          elif "IntegerType" in self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["IntegerType"]["const"] = self._flowSpecBase[flowObject][resource]
          elif "FloatType" in self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["FloatType"]["const"] = self._flowSpecBase[flowObject][resource]
          elif "StringType" in self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["StringType"]["const"] = self._flowSpecBase[flowObject][resource]
          elif "BooleanType" in self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["BooleanType"]["const"] = self._flowSpecBase[flowObject][resource]
          elif "TimeType" in self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["TimeType"]["const"] = self._flowSpecBase[flowObject][resource]
          elif "InstanceLinkType" in self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["flo:meta"]["InstanceGraphLink"]["properties"]["InstancePointer"] = { "const": self._flowBasePath + "/" + self._flowSpecBase[flowObject][resource] }
          else:
            print("non conforming value type for flow Object:", flowObject, ", Resource:", resource, ", Value:", self._flowSpecBase[flowObject][resource])

    # assign instance IDs starting at 0, over-write any existing defaults or const 
    # FIXME allow for pre-defined instance numbers

    instanceCount = {}
    for flowObject in self._flowBase:
      omaType = self._flowBase[flowObject]["oma:id"]["const"]
      if omaType not in instanceCount:
        instanceCount[omaType] = 0
      else:
        instanceCount[omaType] += 1
      if "flo:meta" not in self._flowBase[flowObject]:
        self._flowBase[flowObject]["flo:meta"] = {}
      self._flowBase[flowObject]["flo:meta"]["TypeID"] = { "const": omaType }
      self._flowBase[flowObject]["flo:meta"]["InstanceID"] = { "const": instanceCount[omaType] }
      # now do the resources
      instanceCount = {}
      for resource in self._flowBase[flowObject]["sdfProperty"]:
        omaType = self._flowBase[flowObject]["sdfProperty"][resource]["oma:id"]["const"]
        if omaType not in instanceCount:
          instanceCount[omaType] = 0
        else:
          instanceCount[omaType] += 1
        self._flowBase[flowObject]["sdfProperty"][resource]["flo:meta"]["TypeID"] = { "const": omaType }
        self._flowBase[flowObject]["sdfProperty"][resource]["flo:meta"]["InstanceID"] = { "const": instanceCount[omaType] }

    #   resolve oma objlinks from sdf object links

    for flowObject in self._flowBase:
      for resource in self._flowBase[flowObject]["sdfProperty"]:
        if "InstanceGraphLink" in self._flowBase[flowObject]["sdfProperty"][resource]["flo:meta"]:
          objectPointer = self._flowBase[flowObject]["sdfProperty"][resource]["flo:meta"]["InstanceGraphLink"]["properties"]["InstancePointer"]["const"]
          targetObject = self.resolve(objectPointer) # this is the flow graph (self) resolve
          self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["InstanceLinkType"]["properties"]["TypeID"] = targetObject["flo:meta"]["TypeID"]
          self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["InstanceLinkType"]["properties"]["InstanceID"] = targetObject["flo:meta"]["InstanceID"]

    # fini


  # recursive expand-refine all dictionary nodes
  def _expandMergeAll(self, value): 
    if isinstance(value, dict):
      if "sdfRef" in value:
        self._mergeRefine(value, self._expandReference(value))
      for item in value:
        self._expandMergeAll(value[item]) 

    # recursive expand-merge, follow a chain of sdfRefs refining a node and merge from the end back on the closure
  def _expandReference(self, value):
    if isinstance(value, dict) and "sdfRef" in value:
      ref = value["sdfRef"]
      value.pop("sdfRef", None) # remove and replace with sdfRefFrom array to merge
      value["sdfRefFrom"] = [ref] # this will result in set merge of sdfRef strings for breadcrumbs
       # expand all the way down the chain, making deep copies to merge into
       # then mergeRefine in reverse order on the nested closure and return the fully resolved object
      refined = self._mergeRefine(self._expandReference(copy.deepcopy(self._resolveModel(ref))), value)
      return refined
    return value

  # special refine merge that handles array set merge and sdfChoice refinement. sdfChoice is refined by replacing
  # the entire sdfChoice with the patch value. If extension is desired, an sdfRef to the base sdfChoice contents
  # should be included in the patch. Descriptions are also filtered out as they are encountered, to reduce noise 
  #
  def _mergeRefine(self, base, patch):
    if not isinstance(base, dict):
      base = {}
    if not isinstance( patch, dict):
      return patch
    for key, patchItem in patch.items():
      if isinstance(patchItem, dict): # merge dict into base
        baseValue = base.get(key) # key error safe this way
        if isinstance(baseValue, dict): # see if there is also a dict in the base
          if "sdfChoice" == key: # if the item is sdfChoice, refine by copying into an empty dict
            base[key] = {} 
          base[key] = self._mergeRefine(base[key], patchItem) # if both are dicts, merge the item into the base
          continue
        base[key] = {} # if there isn't a dict there, or if it is sdfChoice, make a new empty node merge dict into it
        self._mergeRefine(base[key], patchItem) # merge new item or sdfChoice into empty dict
        continue
      if isinstance(patchItem, list):      
        baseValue = base.get(key) # key error safe this way
        if isinstance(baseValue, list): # see if there is a matching list
          base[key] = list(set(baseValue + patchItem)) # merge lists with unique values
          continue
      if None is patchItem: # if the patch contains None, remove the matching node in the base
        base.pop(key, None)
        continue
      if "description" != key: # filter out descriptions from resolved models used in the builder
        base[key] = patchItem # replace empty or plain value with value from the patch
    return base

  # Model graph resolve
  def _resolveModel(self, sdfPointer):
    self._pointer = sdfPointer
    if self._pointer.startswith("/#"):
      self._pointer = self._pointer[2:]
    elif self._pointer.startswith("#"):
      self._pointer = self._pointer[1:]
    if self._pointer.startswith("/"):
      try:
        target = self._modelGraph.resolve(self._pointer)
      except:
        print("sdfPointer doesn't resolve:", self._pointer)
        raise # Exit here because we can't refine broken pointers, traceback to this line
      return(target)
    else:
      return(self._resolveNamespaceReference(self._pointer)) # resolve curie

  def _resolveNamespaceReference(self, sdfPointer):
    print("Namespace not supported: ", sdfPointer)
    raise
    return # namespace feature

  def flowGraph(self):
    return self.graph()


  def flowSpecUML(self):
    umlString = "@startuml\n"
    for flowObject in self._flowSpecBase:
      umlString += "\nobject " + flowObject + " {\n"
      for field in self._flowSpecBase[flowObject]:
        umlString += "  " + field + ": " + self._flowSpecBase[flowObject][field].__repr__() + "\n"
      umlString += "}\n"
      for field in self._flowSpecBase[flowObject]:
        if field == "InputLink" or field == "OutputLink":
          umlString += flowObject + "::" + field + " --> " + self._flowSpecBase[flowObject][field] + "\n"
    return umlString + "@enduml\n"

  def modelGraph(self):
    return self._modelGraph.graph()

  def flowSpec(self):
    return self._flowSpec

  # objectFlowHeader()
  # extract the instances.h file contents from the resolved instance graph Object map
  # instances.h
  # // Generated by ObjectFlow builder 
  # namespace ObjectFlow
  # {
  #   const InstanceTemplate instanceList[] = {
  #     { 43000, 0, 27005, 0, linkType, (AnyValueType){.linkType = {43001,0} } },
  #     { 43000, 0, 27006, 0, timeType, (AnyValueType){.timeType = 0 } },
  #   };
  # }
  # '''
  def objectFlowHeader(self):
    return self._header( self.resolve("/sdfThing/Flow/sdfObject") ) 

  def _header(self, Flow):

    headerString = "// Generated by ObjectFlow builder\nnamespace ObjectFlow\n{\n  const InstanceTemplate instanceList[] = {\n"

    for flowObject in Flow:
      oid = Flow[flowObject]["flo:meta"]["TypeID"]["const"]
      oinst = Flow[flowObject]["flo:meta"]["InstanceID"]["const"]
      for resource in Flow[flowObject]["sdfProperty"]:
        rid = Flow[flowObject]["sdfProperty"][resource]["flo:meta"]["TypeID"]["const"]
        rinst = Flow[flowObject]["sdfProperty"][resource]["flo:meta"]["InstanceID"]["const"]

        # try both patterns of resolving sdfChoice, with a choice selection or with a substituted value
        if "default" in Flow[flowObject]["sdfProperty"][resource]["flo:meta"]["ValueType"]:
          rtype = Flow[flowObject]["sdfProperty"][resource]["flo:meta"]["ValueType"]["default"]
        else: 
          for rtype in Flow[flowObject]["sdfProperty"][resource]["flo:meta"]["ValueType"]["sdfChoice"]: {}
                
        if "const" in Flow[flowObject]["sdfProperty"][resource]["sdfChoice"][rtype]:
          value = Flow[flowObject]["sdfProperty"][resource]["sdfChoice"][rtype]["const"]
        elif "default" in Flow[flowObject]["sdfProperty"][resource]["sdfChoice"][rtype]:
          value = Flow[flowObject]["sdfProperty"][resource]["sdfChoice"][rtype]["default"]
        else: 
          value = Flow[flowObject]["sdfProperty"][resource]["sdfChoice"][rtype]

        if rtype == "BooleanType":
          valueString = "%d" % value
        elif rtype == "IntegerType":
          valueString = "%d" % value
        elif rtype == "FloatType":
          valueString = "%f" % value
        elif rtype == "StringType":
          valueString = "%s" % value
        elif rtype == "TimeType":
          valueString = "%d" % value
        elif rtype == "InstanceLinkType":
          valueString = "{%d,%d}" % (value["properties"]["TypeID"]["const"], value["properties"]["InstanceID"]["const"])
        else:
          print("Unimplemented resource type:", rtype)
          raise

        headerString += "    { %d, %d, %d, %d, %s, (AnyValueType){.%s = " % (oid, oinst, rid, rinst, self._headerType(rtype), self._headerType(rtype) ) 
        headerString += valueString + " } },\n"

    headerString +=   "  };\n}"
    return headerString

  def _headerType(self, modelType):
    # look up the C++ type string binding in /sdfData/ValueTypeString
    return self._modelGraph.resolve("/sdfData/ValueTypeString/sdfChoice")[modelType]["const"]

  def _baseFlowTemplate(self):
    return(
      {
        "sdfThing": {
          "Flow": {
            "sdfObject": {}
          }
        }
      }
    )

# ObjectFlow Builder
def build():
  import sys
  print("ObjectFlow Builder")
  
  modelDirectory = "../Model/"
  flowDirectory = "../Flow/"
  outputDirectory = "../Test/"
  documentDirectory = "../Flow/"

  print ( "Model files in", modelDirectory )
  print ( "Flow files in", flowDirectory )
  print ( "Output files in", outputDirectory )
  print ( "Document files in", documentDirectory )

  # test with local files, make the model graph first
  model = ModelGraph( modelDirectory )
  if model.errors() != 0:
    print (model.errors(), " Errors building models")
    sys.exit(1)

  flow = FlowGraph( model, flowDirectory )

  # Display the flow spec
  print( "\nFlow Spec\n", flow._flowSpec.yaml() )

  print( "\n" + documentDirectory + "flowSpec.uml.txt\n", flow.flowSpecUML() )
  umlfile = open( documentDirectory + "flowSpec.uml.txt", "w" )
  umlfile.write(flow.flowSpecUML()) 
  umlfile.close()

  # Display the object and resource list sorted by ID for diagnostics
  print ( "\nTypes by ID\n", model.idList())

  # application-object.cpp
  print ( "\n" + outputDirectory + "application-object.cpp\n", model.objectHeader() )
  objectfile = open( outputDirectory + "application-object.cpp", "w" )
  objectfile.write(model.objectHeader()) 
  objectfile.close()

  # resource-types.h
  print ( "\n" + outputDirectory + "resource-types.h\n",model.resourceHeader() )
  resourcefile = open( outputDirectory + "resource-types.h", "w" )
  resourcefile.write(model.resourceHeader()) 
  resourcefile.close()

  # instances.h
  print ( "\n" + outputDirectory + "instances.h\n", flow.objectFlowHeader() )
  instancefile = open( outputDirectory + "instances.h", "w" )
  instancefile.write(flow.objectFlowHeader()) 
  instancefile.close()

  # process the UML file to a graphic image
  subprocess.run([ "plantuml", (documentDirectory + "flowSpec.uml.txt") ])

if __name__ == '__main__':
    build()
