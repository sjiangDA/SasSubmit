import sublime
import os
from subprocess import Popen, PIPE
from SasSubmit.settings import SessionInfo


def standardize_browser_name(browser):
  if browser not in ['chrome', 'safari']:
    sublime.message_dialog("Valid browser option is chrome or safari or firefox")
  else:
    return browser


def submit_to_studio(browser):
  if browser == "safari":
    script_file = "safari_submit.applescript"
  else:
    script_file = "chrome_submit.applescript"
  with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),script_file),"r") as f:
    scpt = f.read()
  print(scpt)
  p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
  stdout, stderr = p.communicate(scpt)


def create_new_studio(browser):
  scpt = '''
  set currentApp to path to frontmost application
  activate application "%s"
  delay 0.1
  tell application "System Events"
    keystroke "t" using command down
    delay 0.1
    keystroke "l" using command down
    delay 1
    keystroke "v" using command down
    delay 1
    key code 36
  end tell
  activate currentApp
  ''' % (browser)
  p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
  stdout, stderr = p.communicate(scpt)


class SessionWrapper:
  def __init__(self):
    pass
  def update_info(self):
    session_json = SessionInfo()
    self.browser = standardize_browser_name(session_json.get("browser"))
  def new(self, session_name, root_path):
    self.update_info()
    create_new_studio(self.browser)
  def activate(self):
    pass
  def submit(self, session_name):
    self.update_info()
    submit_to_studio(self.browser)
  def kill(self):
    pass


