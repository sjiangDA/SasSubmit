import os
import sys
import time
import subprocess
import win32gui
import re
import win32com.client as comclt

import sublime

from .helper import SingleHwnd, SingleProcess, WinProcess, move_mouse_to
from SasSubmit.settings import SessionInfo


def standardize_name(name):
  if name == "chrome":
    return "chrome.exe"
  elif name == "firefox":
    return "firefox.exe"
  elif name == "ie":
    return "iexplorer.exe"
  else:
    return name



class StudioSession:
  def __init__(self):
    pass
  def update_session_info(self):
    self.meta = SessionInfo()
    self.browser = self.meta.get("browser")
    self.browser_name = standardize_name(self.browser)
    self.settings = sublime.load_settings("SasSubmit.sublime-settings")
    self.link = self.settings.get("studio_address")
    self.browser_path = self.settings.get(self.browser+"_path")
    self.activate_subl_after_submit = self.settings.get("activate_subl_after_submit")
    self.subl_path = self.settings.get("subl_path")
  def get_win_process(self):
    return WinProcess()
  def get_browser_process(self):
    return self.get_win_process().filter_by_name(self.browser_name, require_hwnd=True)

  def activate_via_looping(self, require_studio):
    activation_success = False
    pses = self.get_browser_process()
    for ps in pses:
      for sh in ps.get_hwnds():
        time.sleep(0.1)
        try:
          if require_studio:
            sh.activate_if_title_icontains("sas studio",with_mouse=True,x_w=0.2,y_w=0.2)
          else:
            sh.activate(with_mouse=True,x_w=0.2,y_w=0.2)
          activation_success = True
          self.last_hwnd = sh.hwnd
          break
        except Exception as e:
          pass
    if activation_success:
      pass
    else:
      raise ValueError("Activating browser failed")

  def activate_via_hwnd(self, require_studio):
    sh = SingleHwnd(self.last_hwnd)
    if SingleProcess(sh.get_pid()).get_name() != self.browser_name:
      raise ValueError("browser changed since last check")
    if require_studio:
      sh.activate_if_title_icontains("sas studio",with_mouse=True,x_w=0.2,y_w=0.2)
    else:
      sh.activate(with_mouse=True,x_w=0.2,y_w=0.2)

  def activate(self, require_studio):
    try:
      self.activate_via_hwnd(require_studio=require_studio)
    except:
      self.activate_via_looping(require_studio=require_studio)

  def new_browser(self):
    if os.path.isfile(self.browser_path):
      proc = subprocess.Popen([self.browser_path, self.link])
      self.meta.set("pid",proc.pid,"studio")
    else:
      sublime.message_dialog("%s setting is not valid!" % (self.browser+"_path"))

  def new_instance(self, instance, root_path):
    self.update_session_info()
    self.new_browser()

  def submit_to_broswer(self):
    for i in range(10):
      handle = win32gui.GetForegroundWindow()
      title = SingleHwnd(handle).get_title()
      submit_success = False
      error_sent = False
      if re.match("SAS Studio", title):
        driver = comclt.Dispatch("WScript.Shell")
        time.sleep(0.01)
        # go to the code tab
        driver.SendKeys("%4")
        # insert new code
        time.sleep(0.01)
        driver.SendKeys("^a")
        time.sleep(0.01)
        driver.SendKeys("^v")
        # submit
        time.sleep(0.5)
        driver.SendKeys("{F3}")
        submit_success = True
        break
      else:
        try:
          self.activate(require_studio=True)
        except:
          error_sent = True
          sublime.message_dialog("Activating %s failed, check if it is running!" % self.browser)
          break
        time.sleep(0.1)
    if submit_success:
      if self.activate_subl_after_submit:
        time.sleep(0.1)
        try:
          _ = os.popen('\"%s\" --command "sas_submit_activate"' % self.subl_path)
        except Exception as e:
          sublime.message_dialog(e)
    elif error_sent == False:
      sublime.message_dialog("Cannot submit to SAS, check if SAS is running!")

  def submit(self, instance, root_path):
    flags, hcursor, (x,y) = win32gui.GetCursorInfo()
    self.update_session_info()
    self.submit_to_broswer()
    move_mouse_to(x,y,with_click=False)

# SingleHwnd(19860206).activate()
# time.sleep(1)
# SingleHwnd(win32gui.GetForegroundWindow()).get_title()
# rect = win32gui.GetWindowRect(19860206)