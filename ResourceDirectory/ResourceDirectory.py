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
    return self._registrationCollection.registrationByID(regID)

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

  def registrationByID(self, regID):
    return self._collection[regID]

  def createRegistration(self, registrationTemplate):
    id = self._newID() 
    self._collection[id] = Registration(registrationTemplate)
    return id

  def readRegistration(self, regID):
    return self.registrationByID(regID).registration()

  def updateRegistration(self, regID, registrationTemplate):
    self.registrationByID(regID).update(registrationTemplate)

  def deleteRegistration(self, regID):
    self._collection.pop(regID, None)


class Registration:
  def __init__(self, registrationTemplate):
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
      self._linkArray.append( link.link() ) # link.resource() for lookup format
    return { # an object fomat of the entire state of the registration
      "base": self._base,
      "href": self._href,
      "ep": self._ep,
      "d": self._d,
      "lt": self._lt,
      "endpointAttribute": self._endpointAttribute,
      "link": self._linkArray
    }

  def endpoint(self): # for endpoint lookup
      map = {}
      map["base"] = self._base
      map["href"] = self._href
      map["ep"] = self._ep
      map["d"] = self._d
      for attribute in self._endpointAttribute:
        map[attribute] = self._endpointAttribute[attribute]
      return map

  def update(self, update):
    for item in update:
      match item:
        case "base": self._base = update[item]
        case "lt": 
          self._lt = update[item] # may be same as, or different from, previous
        case "endpointAttribute": self._endpointAttribute = update[item]
        case "link": # replace all links with new links 
          self._link = []
          for link in update[item]:
            self._link.append( Link(link) )
    # updates always reset the registration timer to the new lt value, if supplied, or the previous value
    self._ltStartTime = self._currentTime 
    self._registrationValid = True


class Link:
  def __init__(self, linkspec):
    self._context = linkspec["context"]
    self._relation = linkspec["relation"]
    self._target = linkspec["target"]
    self._targetAttribute = linkspec["targetAttribute"] # map of named attributes

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
      "targetAttribute": self._targetAttribute
    }

  def resolved():
    return # resloved link parameters including base

  def resource(self): # for resource lookup
      resolved = self.resolved()
      map = {}
      map[self._linkSymbol["context"]] = resolved["context"]
      map[self._linkSymbol["relation"]] = self._relation
      map[self._linkSymbol["target"]] = resolved["target"]
      for attribute in self._targetAttribute:
        map[attribute] = self._targetAttribute[attribute]
      return map

  def json(self):
      return json.dumps(self.textmap())

  def serialize(self, format):
    if "json" == format:
      return self.json()

