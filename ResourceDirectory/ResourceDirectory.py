import json

""" 
Library implementation of RFC9176 Resource Directory
"""

class ResourceDirectory:
  def __init__(self, options):

    self._options = options

    self._supportedContentType = {
      "rd": [40],
      "rd-lookup-ep": [40],
      "rd-lookup-res": [40]
    }
    self._supportedMimeType = {
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
      self._registrationCollection.createRegistration(registrationTemplate)
    else:
      self._registrationCollection.updateRegistration(regID, registrationTemplate)

  def registration(self, regID): # returns the registration from ID
    self._registrationCollection.readRegistration(regID)

  def simpleRegister(self, regspec):
    pass


class RegistrationCollection:
  def __init__(self):
    self._collection = {} # index by registration ID
    self._nextID = 0 # counter for now, need a reusable pool

  def registrationByEpD(self, ep, d):
    for registration in self._collection:
      if ep == registration["ep"] and d == registration["d"]:
        return registration # the registration that matches ep and d
    return None 

  def createRegistration(self, registrationTemplate):
    self._collection[self._nextID] = Registration(registrationTemplate)
    self._nextID += 1

  def readRegistration(self, regID):
    return self._collection[regID].registration()

  def updateRegistration(self, regID, registrationTemplate):
    self._collection[regID].update(registrationTemplate)

  def deleteRegistration(self, regID):
    self._collection[regID].delete()
    self._collection.pop(regID, None)


class Registration:
  def __init__(self, registrationTemplate):
    for item in registrationTemplate:
      if "base" == item: 
        self._base = registrationTemplate["base"]
      elif "href" == item: 
        self._href = registrationTemplate["href"]
      elif "ep" == item: 
        self._ep = registrationTemplate["ep"]
      elif "d" == item: 
        self._d = registrationTemplate["d"]
      elif "lt" == item: 
        self._lt = registrationTemplate["lt"]
      elif "endpointAttribute" == item: 
        self._endpointAttribute = registrationTemplate["endpointAttribute"] # named attributes
      elif "link" == item: 
        self._link = []
        for link in registrationTemplate["link"]:
          self._link.append(Link(link))

  def link(self, linkspec): # return matching links
    pass

  def registration(self):
    self._linkArray = []
    for link in self._link:
      self._linkArray.append( link.link() )
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
      if "base" == item: self._base = updateItems[item]
      if "lt" == item: self._lt = updateItems[item]
      if "endpointAttribute" == item: self._endpointAttribute = updateItems[item]
      if "link" == item: 
        self._link = []
        for link in updateItems[item]:
          self._link.append( Link(link) )

  def delete(self):
    return # nothing to clean up


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

