import json
import os
import sublime
if sublime.platform() == "osx":
	acceptable_browsers = ['chrome','safari']
	setting_keys = ["browser","studio_address"]
else:
	acceptable_browsers = ['chrome','ie','firefox']
	setting_keys = ["default_session","subl_path","sas_path","browser","firefox_path","chrome_path","ie_path","studio_address"]

	
class SessionInfo:
	def __init__(self, default=False):
		self.path = os.path.join(sublime.packages_path(),"SasSubmit","settings_session.json")
		try:
			# read settings from file when exist
			with open(self.path, "r") as f:
				self.settings = json.load(f)
		except:
			# when not exist
			self.settings = {}
			self.settings['root_path'] = ""
			self.settings['sessions'] = {}
			self.settings['current_session'] = None
		# update settings
		self.load_settings()

	def load_settings(self):
		try:
			settings = sublime.load_settings("SasSubmit.sublime-settings")
			for key in setting_keys:
				self.settings[key] = settings.get(key)
			self.settings['platform'] = sublime.platform()
		except:
			pass

	def save(self):
		with open(self.path, "w") as f:
			json.dump(self.settings, f, sort_keys=True, indent=4)

	def get(self, key, session = None):
		if key in self.settings:
			if key == "browser":
				if "program" in self.settings:
					if self.settings["program"] in acceptable_browsers:
						return self.settings["program"]
			return self.settings[key]
		elif session in self.settings["sessions"]:
			return self.settings["sessions"][session].get(key, None)
		else:
			return None

	def new(self, session):
		if session in self.settings["sessions"]:
			pass
		else:
			self.settings['sessions'][session] = {}

			
	def set(self, key, value, session = None, save=True):
		if session:
			if session in self.settings['sessions']:
				self.settings['sessions'][session][key] = value
			else:
				sublime.message_dialog("Session '%s' does not exist" % session)
				return
		else:
			self.settings[key] = value
		if save:
			self.save()

	def delete_session(self, session):
		self.settings["sessions"].pop(session, None)
		self.save()

# session_info = SessionInfo()
# session_info.get("browser")