import logging
import sys
import time
import json
import os, inspect
import re
import subprocess
import urllib
import urllib.request
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
import psutil
if os.name == "nt":
  import win32api
  import win32com.client as comclt
  import win32gui
  from pywinauto import Application, win32defines
  from pywinauto.win32functions import SetForegroundWindow, ShowWindow

package_path = sys.argv[1]
json_path = os.path.join(package_path, "settings_session.json")

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    filename=os.path.join(package_path, "command_sender.log"),
    filemode="w")
logging.info(sys.version)
logging.info(package_path)
logging.info("-------------------")
logging.info(os.getcwd())

##############################################################
# Define functions and modules to be used                    #
##############################################################

sys.path.append(package_path)
from settings import SessionInfo

session_json = SessionInfo(json_path, default=False)
subl_path = session_json.get("subl_path")
def send_alert(msg):
  with open(os.path.join(package_path,".error_msg.txt"), "w") as f:
    for line in msg:
      f.write(line)
  _ = os.popen('\"%s\" --command "sas_submit_general_alert"' % subl_path)
  time.sleep(1)

def submit_to_studio(command, driver, platform, session_type="studio", paste=True):
  session_json = SessionInfo(json_path, default=False)
  if session_type == "studio":
      studio_address = session_json.settings["studio_address"]
      xpath_code_tab = session_json.settings["xpath_code_tab"]
      xpath_clear_button = session_json.settings["xpath_clear_button"]
      xpath_code_field = session_json.settings["xpath_code_field"]
      xpath_submit_button = session_json.settings["xpath_submit_button"]
  elif session_type == "studio_ue":
      studio_address = session_json.settings["studio_address_ue"]
      xpath_code_tab = session_json.settings["xpath_code_tab_ue"]
      xpath_clear_button = session_json.settings["xpath_clear_button_ue"]
      xpath_code_field = session_json.settings["xpath_code_field_ue"]
      xpath_submit_button = session_json.settings["xpath_submit_button_ue"]

  logging.info("Submitting code to sas ... ...")
  # go to the code tab
  code_tab_button = driver.find_element_by_xpath(xpath_code_tab)
  driver.execute_script("arguments[0].click();", code_tab_button)
  # clear code frame
  clear_button = driver.find_element_by_xpath(xpath_clear_button)
  driver.execute_script("arguments[0].click();", clear_button)
  # insert new code
  textfields = driver.find_elements_by_xpath(xpath_code_field)
  if len(textfields) == 0:
    textfields = driver.find_elements_by_xpath(".//*[@id='perspectiveTabContainer_tabsBC_tab0_editor']/div/div[7]")
  if paste:
      if (platform == "windows") | (platform == "linux"):
        try:
          driver.execute_script("arguments[0].click();", textfields[0])
          textfields[0].send_keys(Keys.CONTROL, "v")
        except:
          logging.exception("")
          send_alert("Submitting to %s encountered an error!" % session_type)
          return
      elif platform == "osx":
          driver.execute_script("arguments[0].click();", textfields[0])
          textfields[0].send_keys(Keys.SHIFT, Keys.INSERT)
  else:
      logging.info("sending command %s" % command)
      command = re.sub("\n\t+", "\n", command)
      textfields[0].send_keys(command)
  # submit
  logging.info("submitting.....")
  # textfields[0].send_keys(Keys.CONTROL, 'a')
  submit_button = driver.find_element_by_xpath(xpath_submit_button)
  driver.execute_script("arguments[0].click();", submit_button)
  # textfields[0].send_keys(Keys.F3)

def submit_to_classic():
  driver = comclt.Dispatch("WScript.Shell")
  win32api.Sleep(500)
  driver.SendKeys("{F4}")
  win32api.Sleep(500)
  _ = os.popen('\"%s\" --command "sas_submit_activate"' % subl_path)

def get_type_from_session_name(session):
  session_name = session.split(":")[0]
  if session_name == "studio":
    return "studio"
  elif session_name == "studio_ue":
    return "studio_ue"
  elif session_name == "classic":
    return "classic"
  else:
    send_alert("The session has to be one of these: studio, studio_ue, classic.", )

def find_sas_pid():
  pids = []
  for pid in psutil.pids():
      try:
        p  = psutil.Process(pid)
        if p.name() == 'sas.exe':
          cmdline = p.cmdline()
          if not max([x == '-noautoexec' for x in cmdline]):
            pids.append(pid)
      except:
          pass
  return pids


def activate_window(path="", pid=0):
    if pid > 0:
        app = Application().connect(process=pid)
    else:
        app = Application().connect(title="SAS", found_index=0)
    w = app.top_window()

    #bring window into foreground
    if w.has_style(win32defines.WS_MINIMIZE): # if minimized
        ShowWindow(w.wrapper_object(), 9) # restore window state
    else:
        SetForegroundWindow(w.wrapper_object()) #bring to front

#-------------------------------------------------
# Define functions to find webdriver pid         -
#-------------------------------------------------
def get_ie_port_pid():
  port_pid_dict = {}
  for pid in psutil.pids():
    try:
      p  = psutil.Process(pid)
      port = 0
      if p.name() == "iexplore.exe":
        for x in p.cmdline():
          r = re.search("(?<=(localhost:))\d+(?=.*)", x)
          try:
            port_str = r.group(0)
            port_pid_dict[int(port_str)] = pid
          except:
            pass
    except:
      pass
  return port_pid_dict

def get_ie_pid(driver):
  initial_url = driver.capabilities['se:ieOptions']['initialBrowserUrl']
  r = re.search("(?<=(localhost:))\d+(?=.*)", initial_url)
  port = int(r.group(0))
  ie_port_pid_dict = get_ie_port_pid()
  try:
    pid = ie_port_pid_dict[port]
  except:
    pid = 0
  return pid

def get_driver_pid(driver):
  browserName = driver.capabilities['browserName']
  if browserName == "internet explorer":
    pid = get_ie_pid(driver)
  else:
    pid =  psutil.Process(driver.service.process.pid).children()[0].pid
  return pid


#------------------------------------
# other helper functions            -
#------------------------------------


class SessionRemote(webdriver.Remote):
    def start_session(self, desired_capabilities, browser_profile=None):
        # Skip the NEW_SESSION command issued by the original driver
        # and set only some required attributes
        self.w3c = True


#########################################
# Main program for sending code         #
#########################################


class SasSession:
  def __init__(self):
    session_json = SessionInfo(json_path, default=False)
    self.platform = session_json.get("platform")
    self.sas_path = session_json.get("sas_path")
    self.sessions = {}

  def create_new_session(self, session_name, command=None):
    # logging.info("The initial command is %s" % command)
    self.current_session = session_name
    self.sessions[session_name] = {}
    type = get_type_from_session_name(self.current_session)
    self.sessions[session_name]['type'] = type
    self.assign_info()
    if type in ["studio", "studio_ue"]:
      self.studio_create_or_submit("create", command)
    elif type == "classic":
      self.classic_create()

  def submit(self, command):
    current_session = self.current_session
    current_session_type = self.sessions[current_session]['type']
    if current_session_type in ["studio", "studio_ue"]:
      self.studio_create_or_submit("submit", command)
    elif current_session_type == "classic":
      self.classic_submit()
      
  def switch(self, session_name):
    self.current_session = session_name

  def kill(self, session_name):
    pass


  def assign_info(self):
    session_json = SessionInfo(json_path, default=False)
    current_session = self.current_session
    current_session_type = self.sessions[current_session]['type']
    root_path = session_json.settings["sessions"][current_session]['root_path']
    self.sessions[current_session]['root_path'] = root_path
    if current_session_type == "studio":
      self.sessions[current_session]['xpath_code_tab'] = session_json.get("xpath_code_tab")
      self.sessions[current_session]['studio_address'] = session_json.get("studio_address")
    elif current_session_type == "studio_ue":
      self.sessions[current_session]['xpath_code_tab'] = session_json.get("xpath_code_tab_ue")
      self.sessions[current_session]['studio_address'] = session_json.get("studio_address_ue")

  def studio_create_or_submit(self, mode, command=None):
    session_json = SessionInfo(json_path, default=False)
    browser = session_json.get("browser")
    current_session = self.current_session
    current_session_type = self.sessions[current_session]['type']

    if 'driver' in self.sessions[current_session]:
      pass
    else:
      self.create_new_driver()
    while True:
        try:
            url = self.sessions[current_session]['driver'].current_url
        except urllib.error.URLError:
            logging.info("Old connection is not working any more")
            send_alert("urllib.error.URLError: Previous Studio connection was killed!")
            session_json.delete_session(current_session)
            break
        except selenium.common.exceptions.WebDriverException:
            logging.info("Browser was killed!")
            send_alert("selenium.common.exceptions.WebDriverException: Previous Studio connection was killed!")
            break
        except:
            logging.info("Cannot get current url from browser, probably because it's not open!")
            send_alert("Cannot get current url from browser, probably because it's not open!")
            break

        if current_session_type == "studio_ue":
          found_loading = re.search('localhost.10080*', url)
          found_loaded = re.search('localhost.*main\?locale', url)
        else:
          found_loading = re.search('localhost.*\?sutoken', url)
          found_loaded = re.search('localhost.*main\?locale', url)
        # also need to check if the url matches the one specified in user settings
        # if it matches but it cannot open probabaly the url in settings is not working
        if found_loaded:
            delay = 60
            try:
                logging.info("Page is loaded, checking if page is ready .................")
                myElem = WebDriverWait(self.sessions[current_session]['driver'], delay).until(EC.presence_of_element_located((By.XPATH, self.sessions[current_session]['xpath_code_tab'])))
                logging.info("Page is ready!")
            except TimeoutException:
                error_msg = "Loading took too much time, please try using a different browser!"
                logging.info(error_msg)
                send_alert(error_msg)
                break
            if mode == "submit":
                pid = session_json.settings["sessions"][self.current_session]['pid']
                activate_window(pid = pid)
                submit_to_studio(command, self.sessions[current_session]['driver'], self.platform, current_session_type)
                break
            else:
              break

        elif found_loading:
            try:
              url_code = urllib.request.urlopen(url).getcode()
            except:
              send_alert("Cannot connect to server, check if server is running or if you provide the correct link!")
              return
            logging.info("Page is still loading, waiting ...................")
            time.sleep(2)
        else:
            self.sessions[current_session]['driver'].get(self.sessions[current_session]['studio_address'])
            
  def create_new_driver(self):
    session_json = SessionInfo(json_path, default=False)
    browser = session_json.get("browser")
    session_name = self.current_session
    if self.platform == "osx":
      if browser == "chrome":
        browserdriver = os.path.join(package_path, "binaries/chromedriver")
      elif browser == "firefox":
        browserdriver = os.path.join(package_path, "binaries/geckodriver")
      else:
        send_alert("Webdriver %s is not currently supported!" % browser)
    elif self.platform == "windows":
      if browser == "ie":
        browserdriver = os.path.join(package_path, "binaries/IEDriverServer.exe")
      elif browser == "chrome":
        browserdriver = os.path.join(package_path, "binaries/chromedriver.exe")
      elif browser == "firefox":
        browserdriver = os.path.join(package_path, "binaries/geckodriver.exe")        
      else:
        send_alert("Webdriver %s is not currently supported!" % browser)
        return
    try:
      if browser == "ie":
        self.sessions[session_name]['driver'] = webdriver.Ie(browserdriver)
      elif browser == "chrome":
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-infobars")
        self.sessions[session_name]['driver'] = webdriver.Chrome(browserdriver, chrome_options=chrome_options)
      elif browser == "firefox":
        self.sessions[session_name]['driver'] = webdriver.Firefox(executable_path=browserdriver)        
    except Exception as e:
      logging.exception("")
      send_alert(str(e))
      return
    driver = self.sessions[session_name]['driver']
    self.sessions[session_name]["url"] = driver.command_executor._url
    self.sessions[session_name]["session_id"] = driver.session_id
    pid = get_driver_pid(driver)
    session_json.set("pid", pid, self.current_session)

  def classic_create(self):
    session_is_default = (self.current_session.split(":")[1] == "default")
    if session_is_default:
      active_sas_pids = find_sas_pid()
      if len(active_sas_pids) == 0:
        pass
      else:
        return

    logging.info("Creating sas classic ... ...")
    session_json = SessionInfo(json_path, default=False)
    sas_path = session_json.get("sas_path")
    if not os.path.isfile(sas_path):
      send_alert("SAS path incorrect!")
      return
    proc = subprocess.Popen('\"%s\" -rsasuser -sasinitialfolder = \"%s\"' % (sas_path, self.sessions[self.current_session]['root_path']))
    session_json.set("pid", proc.pid, self.current_session)

  def classic_submit(self):
    session_is_default = self.current_session.split(":")[1] == "default"
    session_json = SessionInfo(json_path, default=False)

    logging.info("Submitting to sas classic ... ...")
    active_sas_pids = find_sas_pid()
    if session_is_default:
      if len(active_sas_pids) == 0:
        self.classic_create()
      else:
        activate_window(path=self.sas_path)
        submit_to_classic()
    else:
      logging.info("submitting to non-default sas session")
      pid = session_json.settings["sessions"][self.current_session]['pid']
      if pid in active_sas_pids:
        pass
      else:
        session_json.delete_session(self.current_session)
        send_alert("The requested session is not current running!")
        return
      activate_window(pid=pid)
      submit_to_classic()




################################################################
# Using loop to read code send from sublime                    #
################################################################
                        

try:
    sessions = SasSession()

    while True:
        next_line = sys.stdin.readline()
        if not next_line:
            break
        try:
            mode, session_name, command = eval(next_line)
            logging.info(mode)
            logging.info("\n"+80*">"+"\n"+command.rstrip()+"\n"+80*"<")
            if mode == "create":
                sessions.create_new_session(session_name, command)
            if mode == "submit":
                sessions.submit(command)
            if mode == "kill":
                sessions.kill(session_name)
            if mode == "switch":
                sessions.switch(session_name)
        except:
            logging.exception('')
except:
    logging.exception("")
    # pass

sys.stderr.write('run_sas_remote.py: exiting\n')
sys.stderr.flush()
