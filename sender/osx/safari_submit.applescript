set currentApp to path to frontmost application
tell application "Safari" to activate
delay 1
tell application "Safari"
	set tabtitle to name of front document
end tell

if {tabtitle starts with "SAS Studio"} then
	tell application "System Events"
		delay 0.1
		key code 21 using option down
		delay 0.1
		keystroke "a" using command down
		delay 0.1
		keystroke "v" using command down
		key code 99
	end tell
else
	display dialog "SAS Studio is not on the active tab"
end if
activate currentApp