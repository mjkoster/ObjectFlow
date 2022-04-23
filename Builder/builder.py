
import json
import yaml
import glob
import jsonpointer
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
  # arrays are merged, leaving the set union
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
          self._mergeObject(graphValue, modelValue) # if so, merge the model value into the graph
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
      self._modelGraph.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( modelPath + "*.sdf.yml" ):
      self._modelGraph.add( yaml.load( open(file,"r").read() ) )
    self._checkPointers()
  
  def _checkPointers(self):
    # validate that all of the sdfRef and other pointers resolve to some place in the merged graph
    # sdfRef, sdfRequired, sdfInputData, sdfOutputData, sdfRequiredInputData
    # scan for instances of these keys and resolve the references
    return

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
      self._flowSpec.add( json.loads( open(file,"r").read() ) )
    for file in glob.glob( flowPath + "*.flo.yml" ):
      self._flowSpec.add( yaml.load( open(file,"r").read() ) )

    self._resolveFlowGraph() 

  def _resolveFlowGraph(self):
    self._flowGraph = Graph()
    # build a flow graph from the flow spec; resolve all required items and default values from the model graph
    #
    # for each object in the merged flow: 
    #   add a named sdfObject with an sdfRef to the object type
    #   configure the qualities and extension points
    #   add the required sdfProperties and configure them
    #   use default templates for adding sdf elements to the instance model
    #
    return self._flowGraph

  def flowGraph(self):
    return self._flowGraph.graph()

  def flowSpec(self):
    return # a resolved Flow format JSON serialized from the Flow Graph, could merge into the input flow spec

  def json(self):
    return self.flowGraph().json()

  def yaml(self):
    return self.flowGraph().yaml()

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


def build():
  print("FlowBuilder\n")
  # test with local files, make the model graph first
  model = ModelGraph("../Model")
  print(model.json())
  flow = FlowGraph( model, "../Flow" )
  print(flow.json())
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
