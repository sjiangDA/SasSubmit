set currentApp to path to frontmost application
tell application "Google Chrome" to activate
delay 1
tell application "Google Chrome"
  set tabtitle to title of active tab of front window
end tell

if {tabtitle starts with "SAS Studio"} then
  tell application "System Events"
    keystroke "4" using option down
    keystroke "a" using command down
    keystroke "v" using command down
    key code 99
  end tell
else
  display dialog "SAS Studio is not on the active tab"
end if
activate currentApp