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
			xpath_json = json.loads(open(os.path.join(os.path.dirname(self.path), "settings\\driver_settings.json")).read())
			for key in xpath_json.keys():
				self.settings[key] = xpath_json[key]
			self.settings['root_path'] = ""
			self.settings['sessions'] = {}
			self.settings['current_session'] = ""
			self.settings['platform'] = sublime.platform()
		else:
			with open(self.path, "r") as f:
				self.settings = json.load(f)

	def load_default(self):
		settings = sublime.load_settings("SasSubmit.sublime-settings")
		for key in ["default_session", "log_timestamped", "subl_path", "sas_path", "browser", "browser_path",
			"log_exclude", "studio_address", "studio_address_ue"]:
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

	def delete_session(self, session):
		self.settings["sessions"].pop(session, None)
		self.save()

