import json
import os
try:
	import sublime
except:
	pass
	
class SessionInfo:
	def __init__(self, path, default=False):
		self.path = path
		if default:
			self.settings = {}
			self.load_default()
			self.settings['root_path'] = ""
			self.settings['sessions'] = {}
			self.settings['current_session'] = ""
			self.settings['sas_log_name'] = ""
			self.settings['platform'] = sublime.platform()
		else:
			with open(self.path, "r") as f:
				self.settings = json.load(f)

	def load_default(self):
		settings = sublime.load_settings("SasSubmit.sublime-settings")
		for key in ["default_session", "log_timestamped", "subl_path", "sas_path", "browser", "loading_time", 
			"log_exclude", "studio_address", "xpath_code_tab", "xpath_clear_button", 
			"xpath_code_field", "xpath_submit_button", "studio_address_ue", 
			"xpath_code_tab_ue", "xpath_clear_button_ue", "xpath_code_field_ue", 
			"xpath_submit_button_ue"]:
			self.settings[key] = settings.get(key)
	def save(self):
		with open(self.path, "w") as f:
			json.dump(self.settings, f, sort_keys=True, indent=4)

	def get(self, key):
		return(self.settings[key])
	def set(self, key, value, session = None, save=True):
		if session:
			if session in self.settings['sessions']:
				pass
			else:
				self.settings['sessions'][session] = {}
			self.settings['sessions'][session][key] = value
				
		else:
			self.settings[key] = value
		if save:
			self.save()

