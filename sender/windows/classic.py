import time
import re
import os
import subprocess
import sublime
import win32gui
import win32com.client as comclt
from SasSubmit.settings import SessionInfo

from .helper import SingleHwnd, SingleProcess, WinProcess, WindowMgr, SessionMeta, move_mouse_to
def parse_session_name(string):
    splits = string.split(":")
    if (len(splits) > 2) | (len(splits) == 0):
        sublime.message_dialog("Incorrect format of session:instance name!\nCorrect format is 'classic:####' or 'studio'!")
        return
    session_name = splits[0].strip()
    if session_name not in ("classic","studio"):
        sublime.message_dialog("Please choose session name from 'classic' and 'studio'!")
        return
    instance = time.strftime("%m%d%H%M%S")
    if len(splits) == 1:
        instance = "default"
    if len(splits) == 2:
        _instance = splits[1].strip() 
        if _instance != "":
            if session_name == "studio":
                sublime.message_dialog("Instance name will be neglected for studio session!")
            else:
                instance = _instance
    if session_name == "studio":
        instance = None
        session = "studio"
    else:
        session = "%s:%s" % (session_name, instance)
    return {"session":session, "session_name":session_name,"instance":instance}

class ClassicSession:
  def __init__(self):
    pass
  def update_session_info(self, instance, root_path=""):
    self.meta = SessionInfo()
    self.settings = sublime.load_settings("SasSubmit (Windows).sublime-settings")
    self.activate_subl_after_submit = self.settings.get("activate_subl_after_submit")
    self.sas_path = self.settings.get("sas_path")
    self.subl_path = self.settings.get("subl_path")
    self.instance = instance
    self.session = "classic:%s" % instance
    self.root_path = root_path
  def get_win_process(self):
    return WinProcess()
  def get_sas_process(self):
    return self.get_win_process().filter_for_sas()

  def new_instance(self, instance, root_path):
    self.update_session_info(instance, root_path=root_path)
    self.meta.new(self.session)
    self.meta.set("current_session", self.session)
    session_is_default = (instance == "default")
    if session_is_default:
      active_sas_pids = self.get_sas_process()
      if len(active_sas_pids) == 0:
        userhome = os.path.expanduser("~")
        proc = subprocess.Popen('\"%s\" -rsasuser -sasinitialfolder = \"%s\"' % (self.sas_path, userhome))
        pid = proc.pid
        self.meta.set("pid", pid, self.session)
      else:
        pass
    else:
      proc = subprocess.Popen('\"%s\" -rsasuser -sasinitialfolder = \"%s\"' % (self.sas_path, root_path))
      pid = proc.pid
      self.meta.set("pid", pid, self.session)

  def activate_via_pid(self):
    pid = self.meta.get("pid",self.session)
    sp = SingleProcess(pid)
    sp.get_hwnds()[0].activate(with_mouse=True)

  def activate_last_active(self,wildcard,with_mouse=True,with_alt=True):
    w = WindowMgr()
    handles = w.find_window_wildcard(wildcard)
    activation_success = False
    for hwnd in handles:
      try:
        SingleHwnd(hwnd).activate(with_mouse=with_mouse,with_alt=with_alt)
        activation_success = True
        break
      except Exception as e:
        pass
    if activation_success:
      pass
    else:
      raise Exception("Activating last active SAS failed")

  def activate(self):
    if self.instance == "default":
      self.activate_last_active(r"^SAS$")
    else:
      self.activate_via_pid()

  def submit_to_sas(self):
    error_sent = False
    submit_success = False
    for i in range(10):
      handle = win32gui.GetForegroundWindow()
      title = SingleHwnd(handle).get_title()
      if title == "SAS":
        driver = comclt.Dispatch("WScript.Shell")
        time.sleep(0.01)
        driver.SendKeys("{F4}")
        submit_success = True
        break
      else:
        try:
          self.activate()
          time.sleep(0.05)
        except:
          error_sent = True
          self.new_instance(self.instance, self.root_path)
          break
    if submit_success:
      if self.activate_subl_after_submit:
        time.sleep(0.1)
        try:
          _ = os.popen('\"%s\" --command "sas_submit_activate"' % self.subl_path)
        except Exception as e:
          sublime.message_dialog(e)
    elif error_sent:
      sublime.message_dialog("No SAS program is running, starting new one!")
    else:
      sublime.message_dialog("Cannot submit to SAS, check if SAS is running!")
  def submit(self, instance, root_path=""):
    flags, hcursor, (x,y) = win32gui.GetCursorInfo()
    self.update_session_info(instance, root_path=root_path)
    self.submit_to_sas()
    move_mouse_to(x,y,with_click=False)