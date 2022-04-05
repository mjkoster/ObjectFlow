
import json
import yaml

"""
Implementation of Useful State Machine, consumes a state description JSON and makes an instance of the state machine 

Python classes for State Machine, its Inputs, its Outputs, and its States.

Simple evaluator for transition conditional inputs for simple values with eqality test
Simple setter for output values

"""
class StateMachine:
  def __init__(self, filePath: str):

    self._stateMachine = self
    self._filePath = filePath
    if self._filePath.endswith("json"):
      self._stateMachineSpec = json.loads( open(filePath,"r").read() ) 
    elif self._filePath.endswith("yml"):
      self._stateMachineSpec = yaml.loads( open(filePath,"r").read() ) 
    else: self._stateMachineSpec = {}

    self._input = dict(str, Input)
    self._output = dict(str, Output)
    self._state = dict(str, State)

    # make instances of all inputs, outputs, and states
    for input in self._stateMachineSpec["Input"]:
      self._input[input] = Input(self._stateMachineSpec["Input"][input]) # construct an instance with the document node 
    for output in self._stateMachineSpec["Output"]:
      self._output[output] = Output(self._stateMachineSpec["Output"][output]) # construct an instance with the document node 
    for state in self._stateMachineSpec["State"]:
      self._state[state] = State( state, self._stateMachineSpec["State"][state], self._stateMachine ) # construct an instance with the name, the document node, and the state machine instance

    self._currentState = self._state[ self._stateMachineSpec["CurrentState"] ] # initialize the state machine to the provided state

    self._currentTime = 0

  def currentTime(self): return self._currentTime

  def currentState(self): return self._currentState

  def syncInput(self): 
    for input in self._input:
      self._input[input].syncInput() 

  def evaluate(self): self._currentState = self.currentState.evaluate()


class Input:
  def __init__(self, inputInstance):

    self._externalValue = inputInstance # assume a compatible value
    self.syncInput() 
  
  def setExternalValue(self, value):
    self._externalValue = value

  def syncInput(self):
    self._value = self._externalValue

  def value(self): return self._value 


class Output:
  def __init__(self, outputInstance):
    self._outputInstance = outputInstance
    self.syncOutput(outputInstance) # some initial value or a mapping construct

  def syncOutput(self,value): self._value = value
  
  def value(self): return self._value


class State:
  def __init__(self, stateName: str, stateInstance, stateMachine: StateMachine ):
    self._stateName = stateName # the name of the spec state node
    self._stateInstance = stateInstance # the value of the spec state node
    self._stateMachine = stateMachine
    self._output = stateInstance["Output"]
    self._transition = stateInstance["Transition"]

  def name(self): return self._stateName
  
  def evaluate(self):
    self._stateMachine.syncInput()
    self._nextState = self
    for transition in self._transition:
      for minterm in self._transition[transition]:
        if self._mintrue(self._transition[transition][minterm]): # if any minterm is true, the OR value is true 
          self._nextState = self._stateMachine._state[transition] 
          self._nextState.syncToOutput() # moore or mealy
          return self._nextState
    self._nextState.syncToOutput() # mealy 
    return self._nextState

  def _mintrue(self, minterm): # see if an AND minterm is true (none of the subexpressions are false)
    self._mintrue = True
    for input in minterm: # evaluates the state of one or more inputs and returns the logical "and"
      if isinstance( minterm[input], bool ) or isinstance( minterm[input], int ) or isinstance( minterm[input], float ) or isinstance( minterm[input], str ): 
        # if it's a simple value, simply compare the value with the value returned by Input.value()
        if self._stateMachine._input[input].value() != minterm[input]:
          self._mintrue = False
      else: self._mintrue = False # return false for any non-simple values until implemented
    return self._mintrue

  def syncToOutput(self):
    for output in self._output:
      if isinstance( self._output[output], bool ) or isinstance( self._output[output], int ) or isinstance( self._output[output], float ) or isinstance(self._output[output], str ): 
        # for simple values, just call syncOutput on each Output object using the name index in the StateMachine
        self._stateMachine._output[output].syncOutput(self._output[output])


def testMachine(): # state machine definition for test
  testMachine = {

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
  return testMachine


def testInput(): # this can be used as a test vector generator
  testInput = [
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
  stateMachine = StateMachine( testMachine() )
  # for all vectors in test file
  for testStep in testInput():
    print ("Time: ", testStep["time"])
    # set inputs vector
    print ("Inputs:")
    for input in testStep["Input"]:
      testMachine._input[input].setExternalValue(testStep["Input"][input].value() )
      print ( input, ": ", testMachine._input[input].value() )
    # evaluate the state machine 
    testMachine.evaluate()
    # display the outputs
    print ("Outputs:")
    for output in testMachine._output:
      print ( output, ": ", testMachine._output[output].value() )
    print 


if __name__ == '__main__':
  test()

