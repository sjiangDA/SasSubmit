import sublime
import sublime_plugin
import os, inspect
import re
import subprocess
import time
from .settings import SessionInfo
import threading
import json
import logging
import sys
from .code_getter import CodeGetter
from Default.goto_line import GotoLineCommand


############################################################
# Set global variables
############################################################
# Get environment variables
package_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
print(100*"-")
platform = sublime.platform()
if platform == "windows":
    exe_path = os.path.join(package_path, "command_sender\\dist\\command_sender.exe")
elif platform == "osx":
    exe_path = os.path.join(package_path, "command_sender/dist/command_sender.app/Contents/MacOS/command_sender")
else:
    sublime.error_message("SasSubmit currently not surports your platform!")

json_path = os.path.join(package_path, "settings_session.json")

# Setting logging
logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    filename=os.path.join(package_path, "command_initializer.log"),
    filemode="w")

print(os.path.join(package_path, "command_initializer.log"))
PATTERN = re.compile(r"""
    (?P<quote>["'])
    (?P<quoted_var>
        \$ (?: [_a-z][_a-z0-9]*  | \{[^}]*\} )
    )
    (?P=quote)
    |
    (?P<var>
        \$ (?: [_a-z][_a-z0-9]*  | \{[^}]*\} )
    )
""", re.VERBOSE)

global_vars = {}

# Initialize session information
session_info = SessionInfo(json_path, default=True)
session_info.save()


############################################################
# Define help functions
############################################################

def escape_dquote(cmd):
    cmd = cmd.replace('"', '\\"')
    cmd = cmd.replace("\'", "\'")
    return cmd

def escape_squote(cmd):
    cmd = cmd.replace('\\', '\\\\')
    cmd = cmd.replace("\'", "\'")
    return cmd


def send_command_to_sas(mode, session_name, command):
    try:
        command = "%r"%command
        cmd = 'list(["{}", "{}" ,{}])\n'.format(mode, session_name, command)
        global_vars['procs'].stdin.write(cmd.encode("ascii"))
        global_vars['procs'].stdin.flush()
    except:
        logging.exception("")

def create_new_session(session, view):
    settings = sublime.load_settings("SasSubmit.sublime-settings")

    session_info = SessionInfo(json_path)
    session_info.load_default()
    session_info.save()

    # warn existing users of the new version:
    update_warning = settings.get("update_warning_1810")
    if update_warning:
        sublime.message_dialog("You have updated to the latest version of SasSubmit!\nIn this version the configuration of SAS keys has changed, please follow instructions on 'https://packagecontrol.io/packages/SasSubmit' to update your SAS configuration.\nTo disable this message, go to Perferences>Package Settings>SasSubmit>Settings and change 'update_warning_1810' to be false")
        return

    sessions_list = session_info.get("sessions")
    current_session = session

    filepath = view.file_name()
    try:
        root_path = os.path.dirname(filepath)
    except:
        sublime.message_dialog("Please open one file to start SAS session!")
        return
    session_info.set("current_session", current_session)

    if settings.get("log_timestamped"):
        timestr = time.strftime("_%Y%m%d_%H%M%S")
    else:
        timestr = ""
    session_info.set("root_path", root_path, current_session)
    # command = "\"C:/ProgramData/Anaconda2/envs/py35/python.exe\" -u \"%s\" \"%s\"" % (os.path.join(package_path, "command_sender\\command_sender.py"), package_path)
    # command = "\"C:/Users/sjiang/AppData/Local/conda/conda/envs/py35/python\" -u \"%s\" \"%s\"" % (os.path.join(package_path, "command_sender\\command_sender.py"), package_path)
    command = ["%s" % exe_path, "%s" % package_path]
    print(command)
    if "procs" in global_vars:
        pass
    else:
        global_vars['procs'] = subprocess.Popen(command, 
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            )

    cmd = "x \'cd \"%s\"\';" % root_path
    sublime.set_clipboard(cmd.replace("\n", "\r\n"))
    send_command_to_sas("create", current_session, cmd)

def parse_session_name(string):
    splits = string.split(":")
    if (len(splits) > 2) | (len(splits) == 0):
        sublime.message_dialog("Incorrect format of session name!\nCorrect format is XXXX:YYYY")
    session = splits[0].strip()
    instance = time.strftime("%m%d%H%M%S")
    if (len(splits) == 1) & (session == "classic"):
        instance = "default"
    if len(splits) == 2:
        _instance = splits[1].strip() 
        if _instance != "":
            instance = _instance
    session = "%s:%s" % (session, instance)
    return session


############################################################
# Define Sublime commands                                  # 
############################################################

class SasSubmitCreateSessionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("SasSubmit.sublime-settings")
        def on_done(input_string):
            session = parse_session_name(input_string)
            session_name = session.split(":")[0]
            if (sublime.platform() == "osx") & (session_name not in ["studio", "studio_ue"]):
                sublime.error_message("Session %s was not supported on osx platform!" % session)
                return
            create_new_session(session, self.view)

        def on_change(input_string):
            pass
        def on_cancel():
            pass
        window = self.view.window()
        window.show_input_panel("Session to Create:", settings.get("default_session"),
                                 on_done, on_change, on_cancel)


class SasSubmitCommand(sublime_plugin.TextCommand):
    def resolve(self, cmd):
        view = self.view
        window = view.window()
        extracted_variables = window.extract_variables()
        if len(view.sel()) == 1:
            row, _ = view.rowcol(view.sel()[0].begin())
            extracted_variables["line"] = str(row + 1)

            word = view.substr(view.sel()[0])
            if not word:
                word = view.substr(view.word(view.sel()[0].begin()))
            extracted_variables["selection"] = word

        fname = view.file_name()
        if fname:
            fname = os.path.realpath(fname)
            for folder in window.folders():
                if fname.startswith(os.path.realpath(folder) + os.sep):
                    extracted_variables["current_folder"] = folder
                    break

        def convert(m):
            quote = m.group("quote")
            if quote:
                var = sublime.expand_variables(m.group("quoted_var"), extracted_variables)
                if quote == "'":
                    return "'" + escape_squote(var) + "'"
                else:
                    return '"' + escape_dquote(var) + '"'
            else:
                return sublime.expand_variables(m.group("var"), extracted_variables)

        cmd = PATTERN.sub(convert, cmd)
        return cmd

    def run(self, edit, cmd=None, prog=None, confirmation=None):
        session_info = SessionInfo(json_path, default=False)
        current_session = session_info.get("current_session")
        print("current_session is %s" % current_session)
        if current_session:
            pass
        else:
            create_new_session("classic:default", self.view)
            return
        # set CodeGetter before get_text() because get_text may change cursor locations.
        if confirmation:
            ok = sublime.ok_cancel_dialog(confirmation)
            if not ok:
                return
        if cmd:
            print("start from ")
            cmd = self.resolve(cmd)
        else:
            getter = CodeGetter.initialize(self.view)
            cmd = getter.get_text()

        sublime.set_clipboard(cmd.replace("\n", "\r\n"))
        send_command_to_sas("submit", current_session, cmd)
        
class SasSubmitChooseSessionCommand(sublime_plugin.TextCommand):
    def show_quick_panel(self, options, done, **kwargs):
        sublime.set_timeout(
            lambda: self.view.window().show_quick_panel(options, done, **kwargs), 10)
    def normalize(self, content):
        return content

    def run(self, edit):
        session_info = SessionInfo(json_path, default=False)
        sessions_list = list(session_info.get("sessions").keys())

        def on_done(action):
            print("action is %s" % action)
            if action == -1:
                return
            else:
                result = sessions_list[action]
                current_session = self.normalize(result)
                print("Current session is %s" % current_session)
                session_info.set("current_session", current_session)
                if current_session == "remote":
                    target = "remote"
                elif current_session == "studio" or current_session == "studio_ue":
                    target = "studio"
                else:
                    target = "local"
                send_command_to_sas("switch", current_session, "None")
        try:
            selected_index = sessions_list.index(session)
        except:
            selected_index = 0
        self.show_quick_panel(sessions_list, on_done, selected_index=selected_index)


class SasSubmitSetDirectoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        session_info = SessionInfo(json_path, default=False)
        current_session = session_info.get("current_session")
        filepath = self.view.file_name()
        try:
            root_path = os.path.dirname(filepath)
        except:
            sublime.message_dialog("Please open one file to start SAS session!")
            return
        cmd = "x \'cd \"%s\"\';" % root_path
        sublime.set_clipboard(cmd.replace("\n", "\r\n"))
        send_command_to_sas("submit", current_session, cmd)

class SasSubmitGeneralAlertCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        error_msg_lines = []
        with open(os.path.join(package_path, ".error_msg.txt"), "r") as f:
            for line in f:
                error_msg_lines.append(line)
        error_msg = "\n".join(error_msg_lines)
        sublime.message_dialog(error_msg)