
import json
import yaml
import glob
import jsonpointer
from jsonpointer import resolve_pointer
import jsonschema

class Graph():
# class Graph(dict):
  def __init__(self, spec={}):
    self._graph = {}
    self.add(spec)

  def add(self, model):
    self._merge(model) 

  def _merge(self, model):
  # RFC7386 style merge-patch + list merge
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
          self._mergeObject(graphValue, modelValue) # FIXME graph[key] here; if so, merge the model value into the graph
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

  def json(self):
    # options go here
    return json.dumps( self.graph() ) 

  def yaml(self):
    # options go here
    return yaml.dump( self.graph() ) 


class ModelGraph:
  def __init__(self, modelPath):
    self._modelGraph = Graph()
    # read in all of the SDF files in the model directory
    for file in glob.glob( modelPath + "*.sdf.json" ):
      print(file)
      self._modelGraph.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( modelPath + "*.sdf.yml" ):
      print(file)
      self._modelGraph.add( yaml.safe_load( open(file,"r").read() ) )
    self._checkPointers()
  
  def _checkPointers(self):
    # validate that all of the sdfRef and other pointers resolve to some place in the merged graph
    # sdfRef, sdfRequired, sdfInputData, sdfOutputData
    # recursive scan for instances of these keys and resolve the references
    # allow sdfRef in any object type node of the instance
    # 
    self._check(self._modelGraph._graph())

  def _check(self, value):
    if isinstance(value, object) or isinstance(value, list):
      for item in value:
        if isinstance(item, object):
          if item.contains("sdfRef"):
            self._check_resolve(item["sdfRef"])
        self._check(item)
     
  def _check_resolve(self, sdfPointer):
    self._pointer = sdfPointer
    if self._pointer.startswith("/#"):
      self._pointer = self._pointer[2:]
    elif self._pointer.startswith("#"):
      self._pointer = self._pointer[1:]
    if self._pointer.startswith("/"):
      target = resolve_pointer(self._modelGraph._graph(), self._pointer)
      return(target)
    else:
      return(self._resolveNamespaceReference(self._pointer)) # resolve curie

  def _resolveNamespaceReference(self, sdfPointer):
    return # feature

  def json(self):
    return self._modelGraph.json()

  def yaml(self):
    return self._modelGraph.yaml()

  def uml(self):
    return # "class" UML format


class FlowGraph:
  def __init__(self, modelGraph, flowPath):

    # FLowGraph gets filled in with all required items and values defined 
    # the ObjectFlow header can be made from the full InstanceGraph

    self._modelGraph = modelGraph

    self._flowSpec = Graph()

    for file in glob.glob( flowPath + "*.flo.json" ):
      print(file)
      self._flowSpec.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( flowPath + "*.flo.yml" ):
      print(file)
      self._flowSpec.add( yaml.safe_load( open(file,"r").read() ) )

    self._resolveFlowGraph() 

  def _resolveFlowGraph(self):
    self._flowGraph = Graph()
    print(self._flowSpec.yaml())
    # build a flow graph from the flow spec; resolve all required items and default values from the model graph
    #
    # make an instance of a flow graph template and add it to the flowGraph
    self._flowGraph.add(_baseFlowTemplate())
    self._flowBase = self._flowGraph["sdfThing"]["Flow"]["sdfObject"]
    self._flowSpecBase = self._flowSpec["Flow"]
    #
    # for each object in the merged flow: 
    #   add a named sdfObject with an sdfRef to the application object type, using a simple path reference
    #   if there is no Type specified in the flow, the object name will be used as type
    #
    for flowObject in self._flowSpecBase:
      self._flowBase[flowObject] = {}
      if flowObject.contains("Type"):
        self._flowBase[flowObject]["sdfRef"] = "/sdfObject/" + self._flowSpecBase[flowObject]["Type"]
      else:
        self._flowBase[flowObject]["sdfRef"] = "/sdfObject/" + flowObject

      # hydrate - expand all sdfRefs and process required items
      # currently _hydrate expands all resources defined in the application template and ignores sdfRequired
      self._hydrate(self._flowBase[flowObject])
      
      # merge the values from the flow spec resources to the graph resources
      for resource in self._flowBase[flowObject]["sdfProperty"]:
        if self._flowSpec[flowObject].contains(resource): # if there is a value in the flow spec
          if isinstance(self._flowSpec[flowObject][resource], object ): # merge in qualities verbatim from object value
            self._flowBase[flowObject]["sdfProperty"][resource] = self._flowGraph._mergeObject(
              self._flowBase[flowObject]["sdfProperty"][resource], 
              self._flowSpec[flowObject][resource]
            )
          # apply as constant value - array needs to be handled when we add multi-instance support
          elif "IntegerType" == self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["IntegerType"]["const"] = self._flowSpec[flowObject][resource]
          elif "FloatType" == self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["FloatType"]["const"] = self._flowSpec[flowObject][resource]
          elif "StringType" == self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["StringType"]["const"] = self._flowSpec[flowObject][resource]
          elif "BooleanType" == self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]:
            self._flowBase[flowObject]["sdfProperty"][resource]["sdfChoice"]["BooleanType"]["const"] = self._flowSpec[flowObject][resource]
          else:
            print("non conforming value type for flow Object:", flowObject, "Resource:", resource)

    #   assign instance IDs 
    #   resolve oma objlinks from sdf object links

    #   --- (linear) recursive expand-merge
  def _expandRef(self, value):
      if isinstance(value, object) and value.contains("sdfRef"):
        refValue = self._resolve(value["sdfRef"]) # get the value linked
        self._expandRef(refValue) # expand all the way down the chain
        value = self._flowGraph._mergeObject(value, refValue) # then back-merge in reverse order on the nested closure

  def _hydrate(self, value): # recursively expand-merge all nodes
    if isinstance(value, object) or isinstance(value, list):
      for item in value:
        self._expandRef(value[item])
        self._hydrate(value[item]) 

  def _resolve(self, sdfPointer):
    self._pointer = sdfPointer
    if self._pointer.startswith("/#"):
      self._pointer = self._pointer[2:]
    elif self._pointer.startswith("#"):
      self._pointer = self._pointer[1:]
    if self._pointer.startswith("/"):
      target = resolve_pointer(self._flowGraph._graph(), self._pointer)
      return(target)
    else:
      return(self._resolveNamespaceReference(self._pointer)) # resolve curie

  def _resolveNamespaceReference(self, sdfPointer):
    return # namespace feature

  def flowGraph(self):
    return self._flowGraph.graph()

  def flowSpec(self):
    return # a resolved Flow format JSON serialized from the Flow Graph, could merge into the input flow spec

  def json(self):
    return self._flowGraph.json()

  def yaml(self):
    return self._flowGraph.yaml()

  def uml(self):
    return # "Instance" UML format

  def objectFlowHeader(self):
    return self._header( self._flowGraph.graph() ) # convert the resolved instance graph to a header file

  def _header(self):
    return


class Object:
  def __init__(self, objectPath):
    self.objectPath = objectPath

  def addResource(self, resourcePath):
    self.resource = Resource(resourcePath)


class Resource:
  def __init__(self, resourcePath):
    self.resourcePath = resourcePath

def _baseFlowTemplate():
  return(
    {
      "sdfThing": {
        "flow": {
          "sdfObject": {}
        }
      }
    }
  )

def build():
  print("FlowBuilder")
  # test with local files, make the model graph first
  model = ModelGraph("../Model/")
  # print (model._modelGraph._graph)
  print(model.yaml())
  flow = FlowGraph( model, "../Flow/" )
  print(flow.yaml())
  # print(flow.objectFlowHeader())

if __name__ == '__main__':
    build()

    #  for each resource 
    #      add sdfRef: /#/sdfType: <type>
    #      Add typeID and override default instanceID as needed
    #      Convert <value> to { Value: { const: <value> } }
    #      Add resource instance to the thing in the ResolvedGraph and an sdfRef corresponding to the matching type
    #      Recursively follow sdfRefs to assign values to the resource properties
    #      If there is no default ValueType, infer one from the value (fixup)
    #      resolve links to ObjectLinks
    #  add any required resources not included with defaults

    # for object in flowGraph resolve required items by object type (Type field in the flow object)
    # if no type, add type: <=name>
    # if required item not present, add it with defaults
    # if required item is present, apply the final value e.g. default => const
    # for object values, check required elements and types and fill in missing elements with defaults
    # assign sequential instance numbers for duplicate instances of Objects and Resources (same TypeID)
    # expand sdfRef pointers as the model is traversed, navigate through temporary JSON pointer subgraphs
    #
    # resolving an SDF instance is done using back-merge of all the sdfRef entry points from the model
    # First, make an instance copy of the Object template for each object instance in the flow, name it, and add sdfRef
    # construct an SDF instance graph by expanding items in the flow graph and add it to the model under sdfInstance:
    # Assign TypeIDs and override default instanceIDs for duplicate TypeIDs
    # resolve Flow links to SDF Instance links to ObjectLinks
    # construct paths to transitive endpoints specified in the flow file e.g.
    # Make an instance of the type and interpret the contents in the flow file 
    # CurrentValue: 100 becomes CurrentValue: { Value: 100 } which is expanded in the template to => sdfThing:
    # CurrentValue: { sdfRef: /#/...CurrentValue, ValueType: { sdfChoice: mapToTypeRef(100)}, Value: 100 }
    # if type is constrained to float (ValueType is set to float in model or flow), convert integer constant
    # e.g. { ValueType: FloatType, Value: 100 } might display back as Value: 100.0
    # serialize the SDF instance graph to a resolved flow graph which is an output graph
    # serialize each object to the header template file
    # can resources be added to an object that aren't in the composed model? What would they do?
    #
    #   merge all of the defaults and required elements 
    #   add the sdf object template to the resolvedGraph and an sdfRef corresponding to the matching Type:
    #   Assign TypeIDs and override default instanceIDs for duplicate TypeIDs, other Object data
    # for each object in flow
