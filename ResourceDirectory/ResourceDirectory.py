import json

""" 
Library implementation of RFC9176 Resource Directory
"""

class ResourceDirectory:
  def __init__(self, options):

    self._options = options

    self._supportedContentType = {
      # ct=40 is required
      "rd": [40],
      "rd-lookup-ep": [40],
      "rd-lookup-res": [40]
    }
    self._supportedMimeType = {
      # json is convenient 
      "rd": ["application/json"],
      "rd-lookup-ep": ["application/json"],
      "rd-lookup-res": ["application/json"]
    }
    self._registrationCollection = RegistrationCollection()

  def selfLinkProperties(self):  # link properties for .well-known/core and targetAttributes of self link
    return {}

  def discover(self, rtfilter ): # return self link properties filtered by "rt"
    return 

  def lookupEndpoint(self, filter):
    return

  def lookupResource(self, filter):
    return

  def registrationRequest(self, registrationTemplate ): # RFC9176 registrationRequest
    regID = self._registrationCollection.registrationByEpD((registrationTemplate["ep"], registrationTemplate["d"]))
    if None == regID:
      regID = self._registrationCollection.createRegistration(registrationTemplate)
    else:
      self._registrationCollection.updateRegistration(regID, registrationTemplate)
    return regID

  def registrationByID(self, regID): # returns the registration from ID
    self._registrationCollection.readRegistration(regID)

  def simpleRegister(self, regspec):
    pass


class RegistrationCollection:
  def __init__(self):
    self._collection = {} # index by registration ID
    self._nextID = 0

  def _newID(self):
    self._nextID += 1 # counter for now, need a reusable pool
    return self._nextID

  def registrationByEpD(self, ep, d):
    for registration in self._collection:
      if ep == registration["ep"] and d == registration["d"]:
        return registration # the registration that matches ep and d
    return None 

  def createRegistration(self, registrationTemplate):
    id = self._newID() 
    self._collection[id] = Registration(registrationTemplate)
    return id

  def readRegistration(self, regID):
    return self._collection[regID].registration()

  def updateRegistration(self, regID, registrationTemplate):
    self._collection[regID].update(registrationTemplate)

  def deleteRegistration(self, regID):
    self._collection.pop(regID, None)


class Registration:
  def __init__(self, registrationTemplate):

    self._collection = collections
    # Template defaults
    self._base = ""
    self._href = ""
    self._ep = None # Mostly required
    self._d = ""
    self._lt = 90000 # RFC9176 
    self._endpointAttribute = {}
    self._link = []

    for item in registrationTemplate:
      match item:
        case "base": self._base = registrationTemplate["base"]
        case "href": self._href = registrationTemplate["href"]
        case "ep": self._ep = registrationTemplate["ep"]
        case "d": self._d = registrationTemplate["d"]
        case "lt": self._lt = registrationTemplate["lt"]
        case "endpointAttribute": self._endpointAttribute = registrationTemplate["endpointAttribute"]
        case "link": 
          for link in registrationTemplate["link"]:
            self._link.append(Link(link))
    # wrap-safe time method        
    self._currentTime = 0
    self._ltStartTime = self._currentTime
    self._registrationValid = True

  def evaluateTime(self, time):
    self._currentTime = time
    if self._currentTime >= self._ltStartTime + self._lt:
      self._registrationValid = False

  def valid(self): return self._registrationValid

  def link(self, linkspec): # return matching links for lookup functions
    return None

  def registration(self):
    self._linkArray = []
    for link in self._link:
      self._linkArray.append( link.link() ) # link.textmap() here for target attributes at top level
    return { # an object fomat of the entire state of the registration
      "base": self._base,
      "href": self._href,
      "ep": self._ep,
      "d": self._d,
      "lt": self._lt,
      "endpointAttribute": self._endpointAttribute,
      "link": self._linkArray
    }

  def update(self, updateItems):
    for item in updateItems:
      match item:
        case "base": self._base = updateItems[item]
        case "lt": 
          self._lt = updateItems[item] # may be same as, or different from, previous
        case "endpointAttribute": self._endpointAttribute = updateItems[item]
        case "link": # replace all links with new links (not specified in RFC9176)
          self._link = []
          for link in updateItems[item]:
            self._link.append( Link(link) )
    # updates always reset the registration timer to the new lt value, if supplied, or the previous value
    self._ltStartTime = self._currentTime 
    self._registrationStale = False


class Link:
  def __init__(self, linkspec):
    self._context = linkspec["context"]
    self._relation = linkspec["relation"]
    self._target = linkspec["target"]
    self._targetAttributes = linkspec["targetAttributes"] # map of named attributes

    self._linkSymbol = {
      "context": "con",
      "relation": "rel",
      "target": "href"
    }

  def link(self): # return the raw link map
    return { 
      "context": self._context, 
      "relation": self._relation,
      "target": self._target,
      "targetAttributes": self._targetAttributes
    }

  def resolve():
    return # resloved link including base

  def textmap(self):
      self._map = {}
      self._map[self._linkSymbol["context"]] = self._context
      self._map[self._linkSymbol["relation"]] = self._relation
      self._map[self._linkSymbol["target"]] = self._target
      for attribute in self._targetAttributes:
        self._map[attribute] = self._targetAttributes[attribute]
      return self._map

  def json(self):
      return json.dumps(self.textmap())

  def serialize(self, format):
    if "json" == format:
      return self.json()

