
import json
import yaml
import glob
from jsonpointer import resolve_pointer
import copy
import jsonschema

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
  
  def _checkPointers(self):
    # validate that all of the sdfRef and other pointers resolve to some place in the merged graph
    # sdfRef, sdfRequired, sdfInputData, sdfOutputData
    # recursive scan for instances of these keys and resolve the references
    # allow sdfRef in any object type node of the instance
    # 
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
    # print("checking: ", sdfPointer)
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
    return self._errors


class FlowGraph(Graph):
  def __init__(self, modelGraph, flowPath):
    Graph.__init__(self)

    # FLowGraph gets filled in with all required items and values defined 
    # the ObjectFlow header can be made from the full InstanceGraph

    self._modelGraph = modelGraph

    self._flowSpec = Graph() # for the JSON DSL spec, merge these also

    for file in glob.glob( flowPath + "*.flo.json" ):
      print(file)
      self._flowSpec.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( flowPath + "*.flo.yml" ):
      print(file)
      self._flowSpec.add( yaml.safe_load( open(file,"r").read() ) )

    print(self._flowSpec.yaml())

    self._resolveFlowGraph() 

  def _resolveFlowGraph(self):
    # build a flow graph from the flow spec; resolve all required items and default values from the model graph
    #
    # make an instance of a flow graph template and add it to the flowGraph
    self.add(_baseFlowTemplate())
    self._flowBasePath = "/sdfThing/Flow/sdfObject"
    self._flowBase = self.resolve(self._flowBasePath)
    self._flowSpecBase = self._flowSpec.graph()["Flow"]
    #
    # for each object in the merged flow: 
    #   add a named sdfObject with an sdfRef to the application object type, using a simple path reference
    #   if there is no Type specified in the flow, the object name will be used as type
    #
    for flowObject in self._flowSpecBase:
      self._flowBase[flowObject] = {}
      if "Type" in self._flowSpecBase[flowObject]:
        self._flowBase[flowObject]["sdfRef"] = "/sdfObject/" + self._flowSpecBase[flowObject]["Type"]
      else:
        self._flowBase[flowObject]["sdfRef"] = "/sdfObject/" + flowObject
      print("Resolving ",flowObject)
      # expand all sdfRefs
      self._expandAll(self._flowBase[flowObject])

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

      # merge the values from the flow spec resources to the graph resources
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
            # print("non conforming value type for flow Object:", flowObject, ", Resource:", resource, ", Value:", self._flowSpecBase[flowObject][resource], "Expected type:", self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"])
            print("non conforming value type for flow Object:", flowObject, ", Resource:", resource, ", Value:", self._flowSpecBase[flowObject][resource])

    #   assign instance IDs 
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
          targetObject = self.resolve(objectPointer)
          self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["InstanceLinkType"]["properties"]["TypeID"] = targetObject["flo:meta"]["TypeID"]
          self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["InstanceLinkType"]["properties"]["InstanceID"] = targetObject["flo:meta"]["InstanceID"]

  def _expandAll(self, value): # recursive expand-refine all dictionary nodes
    if isinstance(value, dict):
      if "sdfRef" in value:
        self._mergeRefine(value, self._expandRefine(value))
      for item in value:
        self._expandAll(value[item]) 

    #   --- recursive expand-merge, follow a chain of sdfRefs refining a node and merge from the end back
  def _expandRefine(self, value):
    if isinstance(value, dict) and "sdfRef" in value:
      ref = value["sdfRef"]
      value.pop("sdfRef", None) # remove and replace with sdfRefFrom array to merge
      value["sdfRefFrom"] = [ref] # this will result in set merge of sdfRef strings for breadcrumbs
       # expand all the way down the chain, making deep copies to merge into
       # then mergeRefine in reverse order on the nested closure and return the fully resolved object
      refined = self._mergeRefine(self._expandRefine(copy.deepcopy(self._resolve(ref))), value)
      return refined
    return value

  def _resolve(self, sdfPointer):
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
            # print("base:", key, base[key])
            # print("replace with:", patchItem)
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
      if "description" != key: # filter out descriptions from resolved models used in the builder (?)
        base[key] = patchItem # replace empty or plain value with value from the patch
    return base

  def flowGraph(self):
    return self.graph()

  def flowSpec(self):
    return # a resolved Flow format JSON serialized from the Flow Graph, could merge into the input flow spec

  def objectFlowHeader(self):
    return self._header( self.graph() ) # convert the resolved instance graph to a header file

  def _header(self):
    return

def _baseFlowTemplate():
  return(
    {
      "sdfThing": {
        "Flow": {
          "sdfObject": {}
        }
      }
    }
  )

def build():
  import sys
  print("FlowBuilder")
  # test with local files, make the model graph first
  model = ModelGraph("../Model/")
  if model.errors() != 0:
    print (model.errors(), " Errors building models")
    sys.exit(1)
  # print(model.json())
  flow = FlowGraph( model, "../Flow/" )
  print (flow.json())

if __name__ == '__main__':
    build()
