from processors.alexaplug import AlexaPlug
from processors.searchvetti import SearchVetti


def search_vetti():
  vetti = SearchVetti()
  vetti.process()


def alexa_plugs():
    alexa = AlexaPlug()
    alexa.process()

