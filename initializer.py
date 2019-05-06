import sublime
import sublime_plugin
import os, inspect
import re
import subprocess
import time
import json
import logging

from .settings import SessionInfo
from .getter.blockgetter import BlockGetter
from .helper import parse_session_name, move_cursor_to_next
# from Default.goto_line import GotoLineCommand


############################################################
# Set global variables
############################################################


# Get environment variables
package_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if sublime.platform() == "windows":
  from .sender.windows import SessionWrapper, WinProcess
  programs_list = list(["classic","ie","chrome","firefox"])
elif sublime.platform() == "osx":
  from .sender.osx import SessionWrapper
  programs_list = list(["chrome","safari"])
else:
  sublime.message_dialog("Platform %s is not supported!" % sublime.platform())


sas_session = SessionWrapper()

# Setting logging
logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    filename=os.path.join(package_path, "command_initializer.log"),
    filemode="w")
logging.info(100*"-")

global_vars = {}



############################################################
# Define help functions
############################################################
def get_root_path(view):
    filepath = view.file_name()
    try:
        root_path = os.path.dirname(filepath)
        return root_path
    except:
        sublime.message_dialog("Please open one file to start SAS session!")
        return



def create_new_session(session_name, instance, view):
    logging.info("Creating new session ... session_name is %s, instance is %s." % (session_name, instance))
    if session_name == "studio":
        current_session = "studio"
    else:
        current_session = "%s:%s" % (session_name, instance)
    root_path = get_root_path(view)
    sas_session.new(current_session, root_path)

def run_submit_command(view):
    session_info = SessionInfo()
    current_session = session_info.get("current_session")
    logging.info("Submitting, current_session is %s" % current_session)
    try:
        if current_session:
            pass
        elif sublime.platform() == "osx":
            pass
        else:
            raise Exception("")
        if current_session in session_info.settings['sessions']:
            pass
        elif sublime.platform() == "osx":
            pass
        else:
            raise Exception("")
    except:
        logging.info("Session not exist, using session from settings")
        settings = sublime.load_settings("SasSubmit.sublime-settings")
        session_name = settings.get("default_session")
        program = session_info.get("program")
        logging.info("program is %s" % program)
        if program is None:
            pass
        else:
            if program in programs_list:
                session_name = "studio"
            else:
                session_name = "classic"
        if session_name == "studio":
            create_new_session("studio", "", view)
            current_session = "studio"
        elif session_name == "classic":
            create_new_session("classic", "default", view)
            current_session = "classic:default"
        else:
            sublime.message_dialog("Default session in settings file is not valid!")
            return
    root_path = get_root_path(view)
    sublime.set_timeout_async(sas_session.submit(current_session, root_path))
    # sas_session.submit(current_session)

############################################################
# Define Sublime commands                                  # 
############################################################

class SasSubmitCreateSessionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("SasSubmit.sublime-settings")
        def on_done(input_string):
            session_meta = parse_session_name(input_string)
            if session_meta is None:
                return
            session = session_meta['session']
            session_name = session_meta['session_name']
            instance = session_meta['instance']
            create_new_session(session_name, instance, self.view)

        def on_change(input_string):
            pass
        def on_cancel():
            pass
        window = self.view.window()
        window.show_input_panel("Session to Create:", settings.get("default_session"),
                                 on_done, on_change, on_cancel)

class SasSubmitCommand(sublime_plugin.TextCommand):
        def run(self, edit, cmd=None, prog=None, confirmation=None):            
            sel = [s for s in self.view.sel()][0]
            if len(sel) > 0:
                pass
            else:
                sel = self.view.line(sel)
            cmd = self.view.substr(sel)
            sublime.set_clipboard(cmd.replace("\n", "\r\n"))
            run_submit_command(self.view)

class SasSubmitParagraphCommand(sublime_plugin.TextCommand):
    def run(self, edit, cmd=None, prog=None, confirmation=None):
        sel = [s for s in self.view.sel()][0]
        if len(sel) > 0:
            cmd = self.view.substr(sel)
        else:
            getter = BlockGetter()
            cmd = getter.expand_region_selection(sel)
        sublime.set_clipboard(cmd.replace("\n", "\r\n"))
        run_submit_command(self.view)
        
class SasSubmitChooseSessionCommand(sublime_plugin.TextCommand):
    def show_quick_panel(self, options, done, **kwargs):
        sublime.set_timeout(
            lambda: self.view.window().show_quick_panel(options, done, **kwargs), 10)
    def normalize(self, content):
        return content

    def run(self, edit):
        session_info = SessionInfo()
        sessions_list = list(session_info.get("sessions").keys())
        if sublime.platform() == "osx":
            pass
        else:
            wp = WinProcess()
            for session_i in sessions_list:
                if session_i in ["studio", "classic:default"]:
                    pass
                else:
                    pid_i = session_info.get('pid', session_i)
                    if wp.check_pid_belongs_to_program(pid_i, "sas.exe"):
                        pass
                    else:
                        session_info.delete_session(session_i)

        current_session = session_info.get("current_session")
        sessions_list = list(session_info.get("sessions").keys())

        def on_done(action):
            if action == -1:
                return
            else:
                result = sessions_list[action]
                current_session = self.normalize(result)
                session_info.set("current_session", current_session)
        try:
            selected_index = sessions_list.index(current_session)
        except:
            selected_index = 0
        self.show_quick_panel(sessions_list, on_done, selected_index=selected_index)

class SasSubmitChooseProgramCommand(sublime_plugin.TextCommand):
    def show_quick_panel(self, options, done, **kwargs):
        sublime.set_timeout(
            lambda: self.view.window().show_quick_panel(options, done, **kwargs), 10)
    def normalize(self, content):
        return content

    def run(self, edit):
        session_info = SessionInfo()
        def on_done(action):
            if action == -1:
                return
            else:
                result = programs_list[action]
                session_info.set("program", result)
                if result == "classic":
                    current_session = "classic:default"
                    logging.info("setting current_session to %s" % current_session)
                    session_info.set("current_session", current_session)
                else:
                    current_session = "studio"
                    session_info.set("current_session", current_session)
                    session_info.set("browser", result)
        self.show_quick_panel(programs_list, on_done, selected_index=0)



class SasSubmitSetDirectoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        session_info = SessionInfo()
        current_session = session_info.get("current_session")
        filepath = self.view.file_name()
        try:
            root_path = os.path.dirname(filepath)
        except:
            sublime.message_dialog("Please open one file to start SAS session!")
            return
        cmd = "x \'cd \"%s\"\';" % root_path
        sublime.set_clipboard(cmd.replace("\n", "\r\n"))
        time.delay(0.1)
        sas_session.submit(current_session)


class SasSubmitActivateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sel = [s for s in self.view.sel()][0]
        if len(sel) > 0:
            right_after = sel.end() + 1
            sel = [s for s in self.view.sel()][0]
            self.view.sel().add(sublime.Region(right_after,right_after))
            self.view.sel().subtract(sel)
        self.view.show(self.view.sel())