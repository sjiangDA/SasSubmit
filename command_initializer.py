import sublime
import sublime_plugin
import os, inspect
import re
import subprocess
import time
from .reload_log import *
from .settings import SessionInfo
import threading
import json
import logging
import sys
from .code_getter import CodeGetter
from Default.goto_line import GotoLineCommand

sas_log_name = None
package_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
platform = sublime.platform()
if platform == "windows":
    exe_path = os.path.join(package_path, "command_sender\\dist\\command_sender.exe")
elif platform == "osx":
    exe_path = os.path.join(package_path, "command_sender/dist/command_sender.app/Contents/MacOS/command_sender")
else:
    sublime.error_message("SasSubmit currently not surports your platform!")

json_path = os.path.join(package_path, "settings_session.json")

logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    filename=os.path.join(package_path, "main_python.log"),
    filemode="w")
logging.info(sys.version)
logging.info("-------------------")
logging.info(json_path)
logging.info(package_path)

session_info = SessionInfo(json_path, default=True)
session_info.save()

def escape_dquote(cmd):
    cmd = cmd.replace('"', '\\"')
    cmd = cmd.replace("\'", "\'")
    return cmd

def escape_squote(cmd):
    cmd = cmd.replace('\\', '\\\\')
    cmd = cmd.replace("\'", "\'")
    return cmd

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

def send_command_to_sas(mode, session_name, command):
    try:
        command = "%r"%command
        # cmd = escape_dquote(cmd)
        cmd = 'list(["{}", "{}" ,{}])\n'.format(mode, session_name, command)
        global_vars['procs'].stdin.write(cmd.encode("ascii"))
        global_vars['procs'].stdin.flush()
    except:
        logging.exception("")

def create_new_session(session_name, view):
    settings = sublime.load_settings("SasSubmit.sublime-settings")
    python_path = settings.get("python_path")

    session_info = SessionInfo(json_path)
    session_info.load_default()
    session_info.save()

    sessions_list = session_info.get("sessions")
    current_session = session_name

    filepath = view.file_name()
    try:
        root_path = os.path.dirname(filepath)
    except:
        session_info.set("error_msg", "Please open one file to start SAS session!")
        view.run_command("sas_submit_general_alert")
        return
    session_info.set("current_session", current_session)

    if settings.get("log_timestamped"):
        timestr = time.strftime("_%Y%m%d_%H%M%S")
    else:
        timestr = ""
    sas_log_name = os.path.join(root_path, "SAS_"+current_session+timestr+".log")
    session_info.set("sas_log_name", sas_log_name, current_session) 
    session_info.set("root_path", root_path, current_session)
    # command = ["python3 -u \'%s\' \'%s\'" % (os.path.join(package_path, "command_sender/command_sender.py"), package_path)]
    # command = ["%s" % exe_path, "%s" % package_path]
    command = ["\'%s\' \'%s\'" % (exe_path, package_path)]
    # subprocess.check_call(command)
    if "procs" in global_vars:
        pass
    else:
        global_vars['procs'] = subprocess.Popen(command, 
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            )

    cmd = "x \'cd \"%s\"\';" % root_path
    sublime.set_clipboard(cmd)
    send_command_to_sas("create", current_session, cmd)


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
            print("Start converting... ...")
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
        logging.info("current_session is %s" % current_session)
        if current_session:
            pass
        else:
            create_new_session("classic", self.view)
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
        sublime.set_clipboard(cmd)
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


class SasSubmitCreateSessionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("SasSubmit.sublime-settings")
        def on_done(input_string):
            if (sublime.platform() == "osx") & (input_string not in ["studio", "studio_ue"]):
                sublime.error_message("Session %s was not supported on osx platform!" % input_string)
                return
            create_new_session(input_string, self.view)

        def on_change(input_string):
            pass

        def on_cancel():
            pass

        window = self.view.window()
        window.show_input_panel("Session to Create:", settings.get("default_session"),
                                 on_done, on_change, on_cancel)



class SasSubmitStartRefreshLogCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        session_info = SessionInfo(json_path, default=False)
        current_session = session_info.get("current_session")
        filename = session_info.settings['sessions'][current_session]['sas_log_name']
        log_found = False
        for window in sublime.windows():
            if window.find_open_file(filename):
                log_found = True
                print("start refreshing sas log %s..." % filename)
                print("window = %s..." % window.id())
                log_view = window.find_open_file(filename)
                enable_autorefresh_for_view(log_view)

        if not log_found:
            print("File not found, open it again ... ...")
            sublime.active_window().open_file(filename)



class SasSubmitStopRefreshLogCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        session_info = SessionInfo(json_path, default=False)
        current_session = session_info.get("current_session")
        filename = session_info.settings['sessions'][current_session]['sas_log_name']
        for window in sublime.windows():
            if window.find_open_file(filename):
                log_found = True
                print("stop refreshing sas log %s..." % filename)
                print("window = %s..." % window.id())

                log_view = window.find_open_file(filename)
                disable_autorefresh_for_view(log_view)


class SasSubmitGeneralAlertCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        session_info = SessionInfo(json_path, default=False)
        error_msg = session_info.get("error_msg")
        sublime.message_dialog(error_msg)

