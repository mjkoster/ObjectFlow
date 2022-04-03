
import json
import yaml


class StateMachine:
  def __init__(self, filePath: str):

    # FLowGraph gets filled in with all required items and values defined 
    # the ObjectFlow header can be made from the full InstanceGraph

    self._stateMachine = self
    self._filePath = filePath
    if self._filePath.endswith("yml"):
      self._stateMachineSpec = json.loads( open(filePath,"r").read() ) 
    elif self._filePath.endswith("json"):
      self._stateMachineSpec = yaml.loads( open(filePath,"r").read() ) 
    else: self._stateMachineSpec = {}

    self._inputs = []
    self._outputs = []
    self._states = []

    for input in self._stateMachineSpec["Input"]:
      self._inputs[input] = Input(self._stateMachineSpec["Input"][input]) # construct an instance with the constructor node 
    for output in self._stateMachineSpec["Output"]:
      self._outputs[output] = Output(self._stateMachineSpec["Output"][output]) # construct an instance with the constructor node 
    for state in self._stateMachineSpec["State"]:
      self._states[state] = State( state, self._stateMachineSpec["State"][state], self._stateMachine ) # construct an instance with the constructor node 

    self._currentState = self._states[ self._stateMachineSpec["CurrentState"] ] # initialize the state machine to the provided state

  def currentState(self): return self._currentState

class Input:
  def __init__(self, inputInstance):
    self._externalValue = inputInstance
    self._value = inputInstance # assume a compatible value
  
  def syncInput(self):
    self._value = self._externalValue

  def value(self): return self._value 


class Output:
  def __init__(self, outputInstance):
    self._outputInstance = outputInstance
    self._value = outputInstance # some initial value or a mapping construct

  def syncOutput(self,value): self._value = value


class State:
  def __init__(self, stateName: str, stateInstance, stateMachine: StateMachine ):
    self._stateName = stateName # the name of the spec state node
    self._stateInstance = stateInstance # the value of the spec state node
    self._stateMachine = stateMachine
    self._output = stateInstance["Output"]
    self._transition = stateInstance["Transition"]

  def name(self): return self._stateName
  
  def evaluate(self):
    self._nextState = self._stateMachine.currentState()
    for transition in self._transition:
      for minterm in self._transition[transition]:
        if self._mintrue(self._transition[transition][minterm]): # if any minterm is true, the OR value
          self._nextState = transition
    return self._nextState

  def _mintrue(self, minterm):
    self._mintrue = True
    for input in minterm: # evaluates the state of one or more inputs and returns the logical "and"
      if isinstance( minterm[input], bool ) or isinstance( minterm[input], int ) or isinstance( minterm[input], float ) or isinstance( minterm[input], str ): 
        # if it's a simple value, simply compare the value with the value returned by Input.value()
        if self._stateMachine._inputs[input].value() != minterm[input]:
          self._mintrue = False
      else: self._mintrue = False # return false for any non-simple values until implemented
    return self._mintrue

def test_machine(): # state machine definition for test
  test_machine = {

    "Input": {
      "a": False,
      "b": False
    },

    "Output": {
      "a": False,
      "b": False
    },

    "CurrentState": "S0",

    "State": {

      "S0": {
        "Output": {
          "a": False,
          "b": False
        },
        "Transition": {
          "S1": [
            { "Input a": False, "Input b": True }
          ],
          "S2": [
            { "Input a": True, "Input b": False }
          ]
        }
      },

      "S1": {
        "Output": {
          "a": True,
          "b": False
        },
        "Transition": {
          "S2": [
            { "Input a": True, "Input b": False }
          ]
        }
      },

      "S2": {
        "Output": {
          "a": False,
          "b": True
        },
        "Transition": {
          "S1": [
            { "Input a": False, "Input b": True }
          ]
        }
      }

    }
  }
  return test_machine


def test_input(): # this can be used as a test vector generator
  test_input = [
    {
      "time": 0,
      "Input": { "a": False, "b": False }
    },
    {
      "time": 1,
      "Input": { "a": True, "b": False }
    },
    {
      "time": 2,
      "Input": { "a": False, "b": True }
    },
    {
      "time": 3,
      "Input": { "a": True, "b": True }
    }
  ]
  return test_input


def test():
  return

if __name__ == '__main__':
    test()

