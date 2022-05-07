
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

  def _mergeObject(self, graph, model):
    if not isinstance(graph, dict):
      graph = {}

    if not isinstance( model, dict):
      return model

    for key, modelValue in model.items():
      if isinstance(modelValue, dict): 
        graphValue = graph.get(key) # key error safe this way
        if isinstance(graphValue, dict): # see if there is a matching dict in the graph
          self._mergeObject(graph[key], modelValue) # if so, merge the model value into the graph
          continue
        graph[key] = {} # if there isn't a dict there, make a new empty node merge dict into it
        self._mergeObject(graph[key], modelValue)
        continue
      if isinstance(modelValue, list):      
        graphValue = graph.get(key) # key error safe this way
        if isinstance(graphValue, list): # see if there is a matching list
          graphValue = list(set(graphValue + modelValue)) # merge lists with unique values
          continue
      if None is modelValue: # if the model contains None, remove the matching node in the graph
        graph.pop(key, None)
        continue
      graph[key] = modelValue # replace empty or plain value with value from the model
    return graph

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
        return
      return(target)
    else:
      return(self._resolveNamespaceReference(self._pointer)) # resolve curie

  def _resolveNamespaceReference(self, sdfPointer):
    print("Namespace not supported: ", sdfPointer)
    return # feature


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

    self._resolveFlowGraph() 

  def _resolveFlowGraph(self):
    # self._flowGraph = Graph()
    print(self._flowSpec.yaml())
    # build a flow graph from the flow spec; resolve all required items and default values from the model graph
    #
    # make an instance of a flow graph template and add it to the flowGraph
    self.add(_baseFlowTemplate())
    self._flowBase = self.resolve("/sdfThing/Flow/sdfObject")
    self._flowSpecBase = self._flowSpec._graph["Flow"]
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
      print("Expanded:\n", self.yaml())
      # merge the values from the flow spec resources to the graph resources
      for resource in self._flowBase[flowObject]["sdfProperty"]: # for each property in the sdf graph
        if resource in self._flowSpecBase[flowObject]: # if there is a value in the flow spec
          if isinstance(self._flowSpecBase[flowObject][resource], dict ): # merge in qualities verbatim from object value
            self._flowBase[flowObject]["sdfProperty"][resource] = self._mergeObject(
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
          else:
            # print("non conforming value type for flow Object:", flowObject, ", Resource:", resource, ", Value:", self._flowSpecBase[flowObject][resource], "Expected type:", self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"])
            print("non conforming value type for flow Object:", flowObject, ", Resource:", resource, ", Value:", self._flowSpecBase[flowObject][resource])
    #   assign instance IDs 
    #   resolve oma objlinks from sdf object links

  def _expandAll(self, value): # recursive expand-refine all nodes
    if isinstance(value, dict):
      if "sdfRef" in value:
        value = self._expandRefine(value)
      for item in value:
        self._expandAll(value[item]) 

    #   --- recursive expand-merge, follow a chain of sdfRefs refining a node and merge from the end back
  def _expandRefine(self, value):
    if isinstance(value, dict) and "sdfRef" in value:
      print ("value:\n", value)
      ref = value["sdfRef"]
      value["sdfRef"] = None
      value["sdfRefFrom"] = [ref] # this will result in set merge of sdfRef strings for breadcrumbs
       # expand all the way down the chain, making deep copies to merge into
       # then mergeRefine in reverse order on the nested closure and return the fully resolved object
      refined = self._mergeRefine(self._expandRefine(copy.deepcopy(self._resolve(ref))), value)
      print ("refined:\n", refined)
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
      return(target)
    else:
      return(self._resolveNamespaceReference(self._pointer)) # resolve curie

  def _resolveNamespaceReference(self, sdfPointer):
    print("Namespace not supported: ", sdfPointer)
    return # namespace feature

  def _mergeRefine(self, value, refValue):
    if not isinstance(value, dict):
      value = {}
    if not isinstance( refValue, dict):
      return refValue
    for key, refItem in refValue.items():
      if isinstance(refItem, dict): # merge dict into value
        targetValue = value.get(key) # key error safe this way
        if isinstance(targetValue, dict): # see if there is also a dict in the target
          if "sdfChoice" == key: # if the item is sdfChoice, refine by copying into an empty dict
            # print("target:", key, value[key])
            # print("replace with:", refItem)
            value[key] = {} 
          value[key] = self._mergeRefine(value[key], refItem) # if both are dicts, merge the item into the value
          continue
        value[key] = {} # if there isn't a dict there, or if it is sdfChoice, make a new empty node merge dict into it
        self._mergeRefine(value[key], refItem) # merge new item or sdfChoice into empty dict
        continue
      if isinstance(refItem, list):      
        targetValue = value.get(key) # key error safe this way
        if isinstance(targetValue, list): # see if there is a matching list
          value[key] = list(set(targetValue + refItem)) # merge lists with unique values
          continue
      if None is refItem: # if the model contains None, remove the matching node in the graph
        value.pop(key, None)
        continue
      if "description" != key:
        value[key] = refItem # replace empty or plain value with value from the model
    return value

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
  print("FlowBuilder")
  # test with local files, make the model graph first
  model = ModelGraph("../Model/")
  # print(model.json())
  flow = FlowGraph( model, "../Flow/" )
  # print (flow.json())

if __name__ == '__main__':
    build()
