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
# sentence type
ST_EM = 0 # empty
ST_SS = 1 # step start
ST_SE = 2 # step end
ST_MS = 3 # macro start
ST_ME = 4 # macro end
ST_MF = 5 # macro function
ST_OT = 6 # other
ST_QT = -1 # quoted
ST_CT = -2 # comment

# Get environment variables
package_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
print(100*"-")
platform = sublime.platform()
if platform == "windows":
    exe_path = os.path.join(package_path, "command_sender\\dist\\command_sender\\command_sender.exe")
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

# print(os.path.join(package_path, "command_initializer.log"))
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
        # global_vars['procs'].stdin.write(cmd.encode("ascii"))
        global_vars['procs'].stdin.write(cmd.encode('UTF-8'))
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
    # command = ["%s" % exe_path, "%s" % package_path]
    command = "\"C:/Users/sjiang/AppData/Local/conda/conda/envs/py36/python.exe\" -u \"%s\" \"%s\"" % (os.path.join(package_path, "command_sender\\command_sender.py"), package_path)
    # print(command)
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
        def run(self, edit, cmd=None, prog=None, confirmation=None):
            session_info = SessionInfo(json_path, default=False)
            current_session = session_info.get("current_session")
            if current_session:
                pass
            else:
                create_new_session("classic:default", self.view)
                return
            getter = CodeGetter.initialize(self.view)
            cmd = getter.get_text()

            sublime.set_clipboard(cmd.replace("\n", "\r\n"))
            send_command_to_sas("submit", current_session, cmd)




class SasSubmitParagraphCommand(sublime_plugin.TextCommand):
    def extract_sentence(self, pt):
        cview = self.view
        if re.search("comment",cview.scope_name(pt)):
            return cview.extract_scope(pt)
        else:
            pt_pre_nb = pt_pre = pt_post = pt
            while pt_pre > 0:
                singlestr = cview.substr(sublime.Region(pt_pre-1,pt_pre))
                if singlestr == ";":
                    if not re.search("(quoted)", cview.scope_name(pt_pre)):
                        break
                elif re.search("comment", cview.scope_name(pt_pre-1)):
                    pt_pre += 1 
                    break
                pt_pre -= 1
                if len(singlestr.strip()) == 0:
                    pass
                else:
                    pt_pre_nb = pt_pre
            while pt_post < cview.size():
                singlestr = cview.substr(sublime.Region(pt_post,pt_post+1))
                if singlestr == ";":
                    if not re.search("(quoted)", cview.scope_name(pt_post)):
                        pt_post += 1
                        break
                pt_post += 1
            return sublime.Region(pt_pre_nb, pt_post)

    def get_sen_info(self, pt):
        cview = self.view
        sen = self.extract_sentence(pt)
        senstr = cview.substr(sen)
        # print(100*"-")
        # print(senstr)
        if len(senstr.strip()) <= 1:
            sen_type = ST_EM
            return {"sen_begin":sen.begin(), "sen_end":sen.end(), "sen_type":sen_type}
        scn = cview.scope_name(sen.begin()+re.search("\S",senstr).start())
        # print("scope name is %s" % scn)
        # print("scope begin is %s" % sen.begin())

        if re.search("quoted",scn):
            sen_type = ST_QT
        elif re.search("comment",scn):
            sen_type = ST_CT
        elif re.sub("\s", "", senstr) in ("run;","quit;"):
            sen_type = ST_SE
        else:
            keyword = re.search("\S+\w", senstr).group(0).lower()
            if keyword in ("proc","data"):
                sen_type = ST_SS
            elif keyword == "%macro":
                sen_type = ST_MS
            elif keyword == "%mend":
                sen_type = ST_ME
            elif re.search("%", keyword):
                sen_type = ST_MF
            else:
                sen_type = ST_OT
        return {"sen_begin":sen.begin(), "sen_end":sen.end(), "sen_type":sen_type}

    def expand_macro_define(self, pt):
        cview=self.view
        sen = self.extract_sentence(pt)
        sel_begin = min(sen.begin(), pt)
        senstr = cview.substr(sen).lower()
        mn = re.search("(?<=%macro)\s+\S+\w\s*(?=\(|;)", senstr).group(0).strip()
        ml = 1 # level of macro
        pt_pre = pt_cur = sen.end() - 1
        while True:
            sen_info = self.get_sen_info(pt_cur)
            sen_type=sen_info['sen_type']
            if sen_type == ST_MS:
                if pt_cur == pt_pre:
                    pass
                else:
                    ml += 1
            elif sen_type == ST_ME:
                mn_end_rs = re.search("(?<=%mend)\s+\S+\w\s*(?=\(|;)", senstr)
                if mn_end_rs:
                    mn_end = mn_end_rs.group(0).strip()
                    if mn_end is mn:
                        ml = 0
                    else:
                        ml -= 1
                else:
                    ml -= 1
            
            if ml == 0:
                sel_end = sen_info['sen_end']
                break
            if pt_cur >= cview.size():
                sel_end = pt_pre
                break
            pt_pre = sen_info['sen_end']
            pt_cur = pt_pre+1
        return sublime.Region(sel_begin, sel_end)

    def expand_step_scope(self, pt):
        cview=self.view
        sen = self.extract_sentence(pt)
        sel_begin = min(sen.begin(),pt)
        pt_pre = pt_cur = sen.end()-1
        while True:
            sen_info = self.get_sen_info(pt_cur)
            sen_type=sen_info['sen_type']
            if sen_type in (ST_SS, ST_MS):
                if pt_cur == pt_pre:
                    pass
                else:
                    # use last end as the sel_end
                    sel_end = pt_pre
                    break
            elif sen_type == ST_SE:
                # use the current end as the sel_end
                sel_end = sen_info['sen_end']
                break
            else:
                pass
            # save the location of last end
            pt_pre = sen_info['sen_end']
            # move to the next begin
            pt_cur = pt_pre + 1
            if pt_cur >= cview.size():
                sel_end = pt_pre
                break
        return sublime.Region(sel_begin, sel_end)

    def expand_region_selection(self, sel):
        cview=self.view
        pt = sel.begin()
        sen_info = self.get_sen_info(pt)
        sen_type = sen_info['sen_type']
        if sen_type == ST_SS:
            sel_region = self.expand_step_scope(pt)
        elif sen_type == ST_MS:
            sel_region = self.expand_macro_define(pt)
        else:
            sel_region = self.extract_sentence(pt)
        self.view.sel().add(sel_region)
        return cview.substr(sel_region)

    def run(self, edit, cmd=None, prog=None, confirmation=None):
        session_info = SessionInfo(json_path, default=False)
        current_session = session_info.get("current_session")
        if current_session:
            pass
        else:
            create_new_session("classic:default", self.view)
            return
        # if selected?
        sel = [s for s in self.view.sel()][0]
        if len(sel) > 0:
            cmd = self.view.substr(sel)
            sublime.set_clipboard(cmd.replace("\n", "\r\n"))
            send_command_to_sas("submit", current_session, cmd)
        else:
            cmd = self.expand_region_selection(sel)

class SasSubmitActivate(sublime_plugin.TextCommand):
    def run(self, edit, cmd=None, prog=None, confirmation=None):
        sel = [s for s in self.view.sel()][0]
        if len(sel) > 0:
            right_after = sel.end() + 1
            sel = [s for s in self.view.sel()][0]
            self.view.sel().add(sublime.Region(right_after,right_after))
            self.view.sel().subtract(sel)
        self.view.show(self.view.sel())
        
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
            # print("action is %s" % action)
            if action == -1:
                return
            else:
                result = sessions_list[action]
                current_session = self.normalize(result)
                # print("Current session is %s" % current_session)
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