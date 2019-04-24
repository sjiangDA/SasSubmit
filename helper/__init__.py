import sublime
import time

if sublime.platform() == "osx":
    allowed_sessions = ['studio']
else:
    allowed_sessions = ['classic', 'studio']

def parse_session_name(string):
    splits = string.split(":")
    if (len(splits) > 2) | (len(splits) == 0):
        sublime.message_dialog("Incorrect format of session:instance name!\nCorrect format is 'classic:####' or 'studio'!")
        return
    session_name = splits[0].strip()
    if session_name not in allowed_sessions:
        sublime.message_dialog("Please choose session name from %s!" % " or ".join(allowed_sessions))
        return
    instance = time.strftime("%m%d%H%M%S")
    if len(splits) == 1:
        instance = "default"
    if len(splits) == 2:
        _instance = splits[1].strip() 
        if _instance != "":
            if session_name == "studio":
                sublime.message_dialog("Instance name will be neglected for studio session!")
            else:
                instance = _instance
    if session_name == "studio":
        instance = None
        session = "studio"
    else:
        session = "%s:%s" % (session_name, instance)
    return {"session":session, "session_name":session_name,"instance":instance}



def move_cursor_to_next(view):
    print("moving cursor to next")
    sel = [s for s in view.sel()][0]
    if len(sel) > 0:
        right_after = sel.end() + 1
        sel = [s for s in view.sel()][0]
        view.sel().add(sublime.Region(right_after,right_after))
        view.sel().subtract(sel)
    view.show(view.sel())