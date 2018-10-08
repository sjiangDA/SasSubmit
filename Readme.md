# IMPORTANT CHANGES!!!
Note to EXISTING users:
In the current version, I have changed the keys in SAS for submission from "F1" to "F4". After this change, the "Help" window will not pop up when SAS Enhanced Editor is open. Please change in your SAS by editing "F4" to be "log; gsubmit buf = default". You can keep "F1" configuration as it were or whatever you want it to be.

For new users, please follow the steps in the installation section.

# Descriptions
This program currently supports submitting SAS command in:
* **'classic' mode**: Running SAS program in the classic SAS window
    ![Submit to local](figures/submit_to_classic.gif)
* **'studio' mode**: Submitting SAS command to SAS studio running in browser
    ![Submit to studio](figures/submit_to_studio.gif)
* **'studio_ue' mode**: Submitting SAS command to SAS studio university edition running in browser

Only Windows operating system is supported at this moment. Supports for macos will be added in the future.

# Installation
Download this package and put into Sublime "packages\\" folder or install it using Sublime package control. The latest version of Google Chrome browser needs to be installed. The Sublime packge [`SAS Programming`](https://github.com/rpardee/sas) or [`SAS Syntax and Theme`](https://packagecontrol.io/packages/SAS%20Syntax%20and%20Theme) need to be installed prior to this package.

## Basic setup
* Make a copy of the SasSubmit.sublime-settings and put it into Sublime "Packages/User/" folder. Or open the menu "Preferences/Pacakge Settings/SasSubmit/Settings", then copy from the default settings and paste into the user settings. Make changes only to the user settings.

## Classic mode
* Configure SAS, this only need to be done once.
    - Change the shortcuts in SAS to be:
        + F4: log; gsubmit buf = default
    - Please follow these steps: 
        + Open SAS, in the command box in the top left of SAS program, type in `keys` and press `Enter`
        <p align="center">
          <img src="figures/configure_sas_01.png">
        </p>
        + This will open a "KEYS <DMKEYS>" window, make the changes.
        <p align="center">
          <img src="figures/configure_sas_02.png">
        </p>

## SAS studio university edition
* Start SAS studio university edition.
![SAS studio university edition start](figures/studio_ue_open.png)
* Open the link [http://localhost:10080](http://localhost:10080) in your browser
* Click on the link to start SAS studio.
* The link changes to the format like "http://localhost:10080/SASStudio/371/". Change the settings `studio_address_ue` to this link because it directly link to your SAS studio.
* If you prefer using a browser other than Chrome, you can change the settings `browser` to be "ie" (Internet explorer). Before you do that, make sure you download the compatible webdriver executable and put it into the `SasSubmit\binaries` folder. For 'ie', it can be downloaded from [here](http://selenium-release.storage.googleapis.com/3.9/IEDriverServer_Win32_3.9.0.zip) if you are using 32 bit IE, or [here](http://selenium-release.storage.googleapis.com/3.9/IEDriverServer_x64_3.9.0.zip) if you are using 64 bit IE.

## SAS studio
* Start SAS studio installed with SAS 9.4. It should open a page in     your browser. The link of the web page is in the format of `http://localhost:####/?sutoken=***************************************`, where `####` is a port number and `***************************************` is the token of you SAS studio. Change `studio_address` in settings to be this link.
* SAS studio do not need to be installed on your local computer. You can remotely connect to a computer running SAS studio via port forwarding.

# Usage
* Open command Platte and type in `create session`. 
* On the lower screen find the "Session to Create:" box, and type in the session you want to create. If you type anything else it would fail.
    -  "studio" stands for SAS studio
    -  "studio_ue" stands for SAS studio university edition
    -  "classic" stands for the traditionally used SAS program
* You can create multiple sessions for each type of session. Specifically for "classic" session, 
    - if you type "classic" in the "create session" prompt, it will create a "classic:default" session. For "classic:default" session, SasSubmit will submit SAS command to the most recently activated SAS window.
    - if you type "classic:XXXXX", where "XXXXX" is not "default", for example, "classic:project_1", it will create a "classic:XXXXX" session. These types of session is not the same as "classic:default" as the location of your SAS program will be remembered in these sessions.
* Wait for the session to be created. 
* When the session is ready submit code using `F3`.
* Keep your Sublime application running, otherwise the connection between sublime and all existing sessions will be broken. Also keep the Chrome window open by the session open, otherwise that session would be killed.
* You can create multiple sessions, and you can also switch to different sessions by opening command Platte and type in "choose session".

# Debug
This plugin is still in the alpha stage and I haven't tested thoroughly. If you have problem such as session cannot be created or submitting does not work, please first read Sublime "Packages/SasSubmit/SasSubmit.log"or submit an issue. 
Push is welcome!