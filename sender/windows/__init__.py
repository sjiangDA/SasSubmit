from .classic import ClassicSession
from .studio import StudioSession
from .helper import WinProcess
from SasSubmit.helper import parse_session_name
##############################################################
# Define functions and modules to be used                    #
##############################################################

class SessionWrapper:
  def __init__(self):
    self.session = {}
    self.session["studio"] = StudioSession()
    self.session["classic"] = ClassicSession()
  def parse_session(self, session):
    session_parsed = parse_session_name(session)
    self.instance = session_parsed['instance']
    self.session_name = session_parsed['session_name']
  def new(self, session, root_path):
    print("create new session %s at path %s" % (session, root_path))
    self.parse_session(session)
    self.session[self.session_name].new_instance(self.instance, root_path)
  def submit(self, session, root_path):
    self.parse_session(session)
    print("session is %s" % session)
    print("session_name is %s" % self.session_name)
    self.session[self.session_name].submit(self.instance, root_path)
  def kill(self):
    pass