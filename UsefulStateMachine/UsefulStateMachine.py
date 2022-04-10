
import json
import yaml

"""
Implementation of Useful State Machine, consumes a state description JSON and makes an instance of the state machine 

Python classes for State Machine, its Inputs, its Outputs, and its States.

Simple evaluator for transition conditional inputs for simple values with direct value equality test
Simple setter for output values

"""
class StateMachine:
  def __init__(self, spec):

    self._stateMachine = self
    self._spec = spec
    if isinstance(spec, dict): # for testing and calling as a library
      self._stateMachineSpec = spec
    else:
      if self._spec.endswith("json"):
        self._stateMachineSpec = json.loads( open(self._spec,"r").read() ) 
      elif self._spec.endswith("yml"):
        self._stateMachineSpec = yaml.loads( open(self._spec,"r").read() ) 
      else: self._stateMachineSpec = {} # for incremantal construction

    self._input = {}
    self._output = {}
    self._state = {}

    # make instances of all inputs, outputs, and states
    for input in self._stateMachineSpec["Input"]:
      self._input[input] = Input(self._stateMachineSpec["Input"][input]) # construct an instance with the document node 
    for output in self._stateMachineSpec["Output"]:
      self._output[output] = Output(self._stateMachineSpec["Output"][output]) # construct an instance with the document node 
    for state in self._stateMachineSpec["State"]:
      self._state[state] = State( state, self._stateMachineSpec["State"][state], self._stateMachine ) # construct an instance with the name, the document node, and the state machine instance

    self._currentState = self._state[ self._stateMachineSpec["CurrentState"] ] # initialize the state machine to the provided state

    self._currentTime = 0
    self._intervalStartTime = self._currentTime
    self._intervalTime = self._currentTime - self._intervalStartTime # wrap- and sign-safe interval compare


  def currentState(self): return self._currentState
  
  def intervalTime(self): return self._intervalTime

  def inputByName(self, input): return self._input[input]

  def outputByName(self, output): return self._output[output]

  def syncInput(self, intervalTime): 
    for input in self._input:
      self._input[input].syncInput(intervalTime) 

  def evaluate(self, time): 
    self._currentTime = time
    self._intervalTime = self._currentTime - self._intervalStartTime # wrap- and sign-safe interval compare
    self.syncInput(self.intervalTime())
    self._nextStateName = self._currentState.evaluate()
    if self._nextStateName != "" : # execute the state transition
      self._currentState = self._state[self._nextStateName]
      self._intervalStartTime = self._currentTime
      self._currentState.syncToOutput() # moore, update outputs only on state change
    self._currentState.syncToOutput() # mealy, update outputs when inputs change per state logic


class Input:
  def __init__(self, inputInstance):

    self._externalValue = inputInstance # assume a compatible value
    self.syncInput(0) 
  
  def setExternalValue(self, value):
    self._externalValue = value

  def syncInput(self, intervalTime):
    self._intervalTime = intervalTime
    self._value = self._externalValue

  def value(self): 
    if "Interval" == self._value:
      return self._intervalTime 
    else:
      return self._value 


class Output:
  def __init__(self, outputInstance):
    self._outputInstance = outputInstance
    self.setValue(outputInstance) # some initial value or a mapping construct

  def setValue(self,value): self._value = value
  
  def value(self): return self._value


class State:
  def __init__(self, stateName: str, stateInstance, stateMachine: StateMachine ):
    self._stateName = stateName # the name of the spec state node
    self._stateInstance = stateInstance # the value of the spec state node
    self._stateMachine = stateMachine
    self._setter = stateInstance["Setter"]
    self._transition = stateInstance["Transition"]

  def name(self): return self._stateName
  
  def evaluate(self):
    for transition in self._transition:
      for minterm in self._transition[transition]:
        if self._mintrue(minterm): # if any minterm is true, the OR value is true 
          return transition
    return ""

  def _mintrue(self, expression): # see if the logical product of input subexpressions is true (none of the subexpressions are false)
    self._result = True
    for input in expression: # evaluates the state of one or more inputs and returns the logical "and"
      if isinstance( expression[input], bool ) or isinstance( expression[input], int ) or isinstance( expression[input], float ) or isinstance( expression[input], str ): 
        # if the sub expression is a simple value, simply compare the value with the input value
        if self._stateMachine.inputByName(input).value() != expression[input]: 
          self._result = False
      else: self._result = False # return false for any non-simple values until implemented
    return self._result

  def syncToOutput(self):
    for output in self._setter:
      if isinstance( self._setter[output], bool ) or isinstance( self._setter[output], int ) or isinstance( self._setter[output], float ) or isinstance(self._setter[output], str ): 
        # for simple values, just call setOutput on each Output object using the name index in the StateMachine
        self._stateMachine.outputByName(output).setValue(self._setter[output]) 


def testMachine(): # state machine definition for test
  return (
    {
      "Input": {
        "a": False,
        "b": False,
        "Interval": "Interval"
      },

      "Output": {
        "a": False,
        "b": False
      },

      "CurrentState": "S0",

      "State": {

        "S0": {
          "Setter": {
            "a": False,
            "b": False
          },
          "Transition": {
            "S2": [
              { "a": False, "b": True }
            ],
            "S1": [
              { "a": True, "b": False }
            ]
          }
        },

        "S1": {
          "Setter": {
            "a": True,
            "b": False
          },
          "Transition": {
            "S2": [
              { "a": False, "b": True }
            ]
          }
        },

        "S2": {
          "Setter": {
            "a": False,
            "b": True
          },
          "Transition": {
            "S1": [
              { "a": True, "b": False }
            ]
          }
        }
      }
    }
  )

def testInput(): # this can be used as a test vector generator
  return (
    [
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
      },
       {
        "time": 4,
        "Input": { "a": True, "b": False }
      },
      {
        "time": 5,
        "Input": { "a": False, "b": False }
      },
      {
        "time": 6,
        "Input": { "a": False, "b": True }
      },
    ]
  )


def test():
  stateMachine = StateMachine( testMachine() )
  print ("Constructed state:")
  print ("Inputs:")
  for input in stateMachine._input:
    print ( input, ": ", stateMachine._input[input].value() )
  print ("State: ", stateMachine.currentState().name() )
  print ("Outputs:")
  for output in stateMachine._output:
    print ( output, ": ", stateMachine._output[output].value() )
  print ()
  # for all vectors in test file
  for testStep in testInput():
    print ("Time: ", testStep["time"])
    # set inputs vector
    for input in testStep["Input"]:
      stateMachine._input[input].setExternalValue(testStep["Input"][input] )
    # evaluate the state machine 
    stateMachine.evaluate(testStep["time"])
    # display the state
    print ("Inputs:")
    for input in stateMachine._input:
      print ( input, ": ", stateMachine._input[input].value() )
    print ("State: ", stateMachine.currentState().name() )
    print ("Outputs:")
    for output in stateMachine._output:
      print ( output, ": ", stateMachine._output[output].value() )
    print ()


if __name__ == '__main__':
  test()

