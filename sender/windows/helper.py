import re
import win32process
import win32gui
import win32com
from win32com.client import GetObject
import win32api, win32con


def move_mouse_to(x,y,with_click=True):
    win32api.SetCursorPos((x,y))
    if with_click:
	    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
	    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)

class SingleHwnd:
	def __init__(self, hwnd):
		if win32gui.IsWindow(hwnd):
			self.hwnd = hwnd
		else:
			raise ValueError("Invalid hwnd!")
	def get_title(self):
		return win32gui.GetWindowText(self.hwnd)
	def title_contains(self, tstr):
		if re.search(tstr, self.title):
			return True
		else:
			return False
	def title_icontains(self, tstr):
		if re.search(tstr, self.get_title().lower()):
			return True
		else:
			return False
	def activate(self, with_mouse=False, with_alt=True, x_w=0.5, y_w=0.5):
		rect = win32gui.GetWindowRect(self.hwnd)
		newx = int(x_w*rect[0]+(1-x_w)*rect[2])
		newy = int(y_w*rect[1]+(1-y_w)*rect[3])
		if newx + newy == 0:
			raise ValueError("Window cannot be found!")
		try:
			shell = win32com.client.Dispatch("WScript.Shell")
			if with_alt:
				shell.SendKeys('%')
			if win32gui.IsIconic(self.hwnd):
				win32gui.ShowWindow(self.hwnd, 9)
			win32gui.SetForegroundWindow(self.hwnd)
		except Exception as e:
			raise ValueError("Activate window failed!")

		if with_mouse:
			move_mouse_to(newx,newy)
	def activate_if_title_icontains(self, tstr, with_mouse=False, x_w=0.5, y_w=0.5):
		if self.title_icontains(tstr):
			self.activate(with_mouse=with_mouse, x_w=x_w, y_w=y_w)
		else:
			raise ValueError("Title of the window does not contain %s" % tstr)

	def get_pid(self):
		_, pid = win32process.GetWindowThreadProcessId(self.hwnd)
		return pid

class SingleProcess:
	def __init__(self, process):
		if isinstance(process, int):
			self.process = WinProcess().filter_by_pids(process)[0].process
		else:
			self.process = process
	def __str__(self):
		return self.get_pid()
	def get_property(self, name):
		return self.process.Properties_(name).Value
	def get_name(self):
		return self.get_property("Name")
	def get_cmdline(self):
		return self.get_property("CommandLine")
	def get_pid(self):
		return self.get_property("ProcessID")
	def get_hwnds(self):
		def callback (hwnd, hwnds):
			if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
				_, found_pid = win32process.GetWindowThreadProcessId(hwnd)
				if found_pid == self.get_pid():
					hwnds.append(SingleHwnd(hwnd))
			return True
		hwnds = []
		win32gui.EnumWindows(callback, hwnds)
		return hwnds
		
class WinProcess:
	def __init__(self):
		WMI = GetObject('winmgmts:')
		processes = WMI.InstancesOf('Win32_Process')
		self.processes = dict([(p.Properties_("ProcessID").Value, SingleProcess(p)) for p in processes])
	def pids(self):
		return self.processes.keys()
	def filter_by_pids(self, pids):
		try:
			if isinstance(pids, list):
				return [self.processes[p] for p in pids]
			elif isinstance(pids, int):
				return [self.processes[pids]]
			else:
				return []
		except:
			return []
	def filter_by_name(self, name, require_hwnd = False):
		return [self.processes[p] for p in self.get_pids_by_name(name, require_hwnd = require_hwnd)]

	def filter_for_sas(self):
		return self.filter_by_pids(self.get_pids_for_sas())

	def get_pids_by_name(self, name, require_hwnd = False):
		pids_all = [p for p in self.processes.keys() if self.processes[p].get_name() == name]
		if require_hwnd:
			pids_all = [p for p in pids_all if len(self.processes[p].get_hwnds()) > 0]
		return pids_all

	def get_pids_for_sas(self):
		pids = []
		for p in self.filter_by_name("sas.exe"):
			cmdline = p.get_cmdline()
			if not re.search('-noautoexec', cmdline):
				pids.append(p.get_pid())
		return pids

	def check_pid_belongs_to_program(self, pid, name):
		try:
			if self.filter_by_pids(pid)[0].get_name() == name:
				return True
			else:
				return False
		except:
			return False

class WindowMgr:
	#set the wildcard string you will search for
	def find_window_wildcard(self, wildcard):
		self.handles = []
		win32gui.EnumWindows(self.window_enum_callback, wildcard)
		return self.handles
	#enumurate through all the windows until you find the one you need
	def window_enum_callback(self, hwnd, wildcard):
		if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) != None:
			self.handles.append(hwnd) ##pass back the id of the window

class SessionMeta:
  def __init__(self):
    self.meta = {}
  def new_instance(self, instance):
    self.meta[instance] = {}
  def set(self, instance, key, value):
    if instance in self.meta.keys():
      self.meta[instance][key] = value
  def get(self, instance, key):
    return self.meta[instance][key]
