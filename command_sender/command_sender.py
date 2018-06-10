import logging
import sys
import time
import json
import os, inspect
import re

package_path = sys.argv[1]
sys.path.append(package_path)
json_path = os.path.join(package_path, "settings_session.json")

logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    filename=os.path.join(package_path, "SasSubmit.log"),
    filemode="w")
logging.info(sys.version)
logging.info(json_path)
logging.info("-------------------")
logging.info(os.getcwd())
print(os.getcwd())


import urllib
import urllib.request
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import win32api
import win32com.client as comclt
##############################################################
# Define functions and modules to be used                    #
##############################################################

sys.path.append(package_path)
from settings import SessionInfo

def send_alert(msg):
  session_json = SessionInfo(json_path, default=False)
  subl_path = session_json.get("subl_path")
  session_json.set("error_msg", msg)
  _ = os.popen('\"%s\" --command "sas_submit_general_alert"' % subl_path)

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
  if paste:
      if (platform == "windows") | (platform == "linux"):
          textfields[0].send_keys(Keys.CONTROL, "v")
      elif platform == "osx":
          # command = re.sub("\n\t+", "\n", command)
          # textfields[0].send_keys(command)
          textfields[0].send_keys(Keys.SHIFT, Keys.INSERT)
  else:
      command = re.sub("\n\t+", "\n", command)
      textfields[0].send_keys(command)
  # submit
  logging.info("submitting.....")
  # textfields[0].send_keys(Keys.CONTROL, 'a')
  submit_button = driver.find_element_by_xpath(xpath_submit_button)
  driver.execute_script("arguments[0].click();", submit_button)
  textfields[0].send_keys(Keys.F3)

def get_type_from_session_name(session_name):
  if session_name == "studio":
    return "studio"
  elif session_name == "studio_ue":
    return "studio_ue"
  elif session_name == "classic":
    return "classic"
  else:
    send_alert("The session has to be one of these: studio, studio_ue, classic.", )


class SessionRemote(webdriver.Remote):
    def start_session(self, desired_capabilities, browser_profile=None):
        # Skip the NEW_SESSION command issued by the original driver
        # and set only some required attributes
        self.w3c = True

class SasSession:
  def __init__(self):
    session_json = SessionInfo(json_path, default=False)
    self.platform = session_json.get("platform")
    self.sessions = {}
  def create_new_driver(self):
    session_json = SessionInfo(json_path, default=False)
    session_name = self.current_session
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-infobars")
    try:
      driver = webdriver.Chrome(os.path.join(package_path, "binaries\\chromedriver.exe"), chrome_options=chrome_options)
    except:
      send_alert("Cannot start chromedriver, check if 'chromedriver.exe' is in Sublime 'packages\\SasSubmit\\binaries\\' folder!")
    self.sessions[session_name]['driver'] = driver
    self.sessions[session_name]["url"] = driver.command_executor._url
    self.sessions[session_name]["session_id"] = driver.session_id

  def connect_to_existing_driver(self):
    session_name = self.current_session
    self.sessions[session_name]['driver'] = SessionRemote(command_executor=self.sessions[session_name]['url'], desired_capabilities={})
    self.sessions[session_name]['driver'].session_id = self.sessions[session_name]['session_id']

  def assign_info(self):
    session_json = SessionInfo(json_path, default=False)
    current_session = self.current_session
    current_session_type = self.sessions[current_session]['type']
    
    root_path = session_json.settings["sessions"][current_session]['root_path']
    self.sessions[current_session]['root_path'] = root_path
    self.sessions[current_session]['sas_log_name'] = session_json.settings['sessions'][current_session]['sas_log_name']
    if current_session_type == "studio":
      self.sessions[current_session]['xpath_code_tab'] = session_json.get("xpath_code_tab")
      self.sessions[current_session]['studio_address'] = session_json.get("studio_address")
    elif current_session_type == "studio_ue":
      self.sessions[current_session]['xpath_code_tab'] = session_json.get("xpath_code_tab_ue")
      self.sessions[current_session]['studio_address'] = session_json.get("studio_address_ue")

  def create_new_session(self, session_name):
    self.current_session = session_name
    self.sessions[session_name] = {}
    type = get_type_from_session_name(self.current_session)
    self.sessions[session_name]['type'] = type
    self.assign_info()
    if type in ["studio", "studio_ue"]:
      self.studio_create_or_submit("create")
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

  def classic_create(self):
    logging.info("Creating sas classic ... ...")
    session_json = SessionInfo(json_path, default=False)
    loading_time = session_json.get("loading_time")
    # command = 'cd \'%s\' & \'C:\\Program Files\\SASHome\\SASFoundation\\9.4\\sas.exe\' -rsasuser' % self.sessions[self.current_session]['root_path']
    # logging.info(command)
    _ = os.popen('cd \"%s\" & \"C:\\Program Files\\SASHome\\SASFoundation\\9.4\\sas.exe\" -rsasuser' % self.sessions[self.current_session]['root_path'])
    time.sleep(loading_time)
    driver = comclt.Dispatch("Wscript.Shell")
    driver.AppActivate("SAS")
    win32api.Sleep(1000)
    driver.SendKeys("{F5}")
    win32api.Sleep(100)
    driver.SendKeys("^{F4}")
    win32api.Sleep(100)
    driver.SendKeys("{F7}")
    win32api.Sleep(100)
    driver.SendKeys("^{F4}")

  def classic_submit(self):
    try: 
        driver = comclt.GetActiveObject("SAS.Application")
    except:
        send_alert("No SAS program opening!")
    logging.info("Submitting to sas classic ... ...")
    driver = comclt.Dispatch("Wscript.Shell")
    driver.AppActivate("SAS")
    win32api.Sleep(500)
    driver.SendKeys("{F6}")
    win32api.Sleep(100)
    driver.SendKeys("{F1}")

  def studio_create_or_submit(self, mode, command=None):
    session_json = SessionInfo(json_path, default=False)
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
            # logging.exception("")
            logging.info("Old connection is not working any more")
            send_alert("urllib.error.URLError: Previous Studio connection was killed!")
            break
        except selenium.common.exceptions.WebDriverException:
            # logging.exception("")
            logging.info("Browser was killed!")
            send_alert("selenium.common.exceptions.WebDriverException: Previous Studio connection was killed!")
            break
        except:
            # logging.exception("")
            logging.info("Cannot get current url from broswer, probably because it's not open!")
            send_alert("Cannot get current url from broswer, probably because it's not open!")
            break
            # if 'url' in self.sessions[current_session]:
            #     self.connect_to_existing_driver()
            #     break
            # else:
            #     self.create_new_driver()
            #     break
        if current_session_type == "studio_ue":
          found_loading = re.search('localhost.*', url)
          found_loaded = re.search('localhost.*main\?locale', url)
        else:
          found_loading = re.search('localhost.*\?sutoken', url)
          found_loaded = re.search('localhost.*main\?locale', url)
        # also need to check if the url matches the one specified in user settings
        # if it matches but it cannot open probabaly the url in settings is not working
        if found_loaded:
            delay = 60
            try:
                logging.info("waiting for page to be loaded ......")
                myElem = WebDriverWait(self.sessions[current_session]['driver'], delay).until(EC.presence_of_element_located((By.XPATH, self.sessions[current_session]['xpath_code_tab'])))
                logging.info("Page is ready!")
            except TimeoutException:
                logging.info("Loading took too much time!")
                send_alert("Loading took too much time!")
                continue
            if mode == "create":
                if (current_session_type == "studio") & (self.platform != "osx"):
                    submit_to_studio(command, self.sessions[current_session]['driver'], self.platform, current_session_type)
                break

            else:
                submit_to_studio(command, self.sessions[current_session]['driver'], self.platform, current_session_type)
                break

        elif found_loading:
            try:
              url_code = urllib.request.urlopen(url).getcode()
            except:
              send_alert("Cannot connect to server, check if server is running or if you provide the correct link!")
              return
            time.sleep(2)
        else:
            self.sessions[current_session]['driver'].get(self.sessions[current_session]['studio_address'])


################################################################
# Using loop to read code send from sublime                    #
################################################################
                        

try:
    sessions = SasSession()

    while True:
        next_line = sys.stdin.readline()
        logging.info("reading new line ... ...")
        if not next_line:
            break
        logging.info(next_line)
        try:
            mode, session_name, command = eval(next_line)
            logging.info(mode)
            logging.info(command.encode("ascii"))
            if mode == "create":
                sessions.create_new_session(session_name)
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
