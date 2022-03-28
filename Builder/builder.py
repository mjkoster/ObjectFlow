
import json
import glob

class Graph:
  def __init__(self, model):
    self._graph = {}
    self.addModel(model)

  def addModel(self, model):
    self._merge(model) 

  def _merge(self, graph):
    self._merge(graph) # recursive merge JSON trees, extend trees and set end values

  def graph(self):
    return self._graph

  def json(self):
    return( json.dumps(self.graph() ) )


class ModelGraph:
  def __init__(self, modelPath):
    self._modelGraph = Graph()
    # read in all of the SDF files in the model directory
    for file in glob.glob( modelPath + "*.sdf.json" ):
      self._modelGraph.addModel( json.loads( open(file,"r").read() ) )
  
  def json(self):
    return( self._modelGraph.json())


class InstanceGraph:
  def __init__(self, modelGraph, instancePath):
    # instancePath can point to SDF format or InstanceGraph format
    # there will be an sdfThing called InstanceList in the SDF graph
    # it may be easiest to create an SDF InstanceList to/from partial 
    # InstanceGraph
    # 
    # InstanceGraph has all required items and values defined 
    # the ObjectFlow header can be made from the full InstanceGraph

    self._modelGraph = modelGraph
    self._instanceGraph = Graph(instancePath)
    return

  def json(self):
    return self._instanceGraph.json()

  def objectFlowHeader(self):
    return self._json2header( self.json() ) # convert the json to a header file

  def _json2header(self, json):
    self._json = json
    return


class Object:
  def __init__(self, objectPath):
    self.objectPath = objectPath

  def addResource(self, resourcePath):
    self.resource = Resource(resourcePath)


class Resource:
  def __init__(self, resourcePath):
    self.resourcePath = resourcePath


def test():
  model = ModelGraph("./")
  print(model.json())
  instance = InstanceGraph( model, "/#/sdfThing/InstanceList" )
  print(instance.json())
  print(instance.objectFlowHeader())

if __name__ == '__main__':
    test()

