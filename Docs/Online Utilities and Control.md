UrsaPQ - Control and online data display
======

The utils contained in the Utils folder allow for remote control of the experiment and for online viewing of the aquired data. To control the setup, use the `ursapqConsole.py` GUI. To view the online data, use `ursapqOnlineView.py`.  

Python API are available for programmatic control of the experiment. See the TBA docs page for more info.


## Install
If using one of the desy user console computers, skip this part. Everything is already installed for fl24user. See the "Desy User consoles" docs page for usage info.

Clone this repo and create a config.json file in the `Utils/` folder with the following info. This will give read only access.
```
  {
    "UrsapqServer_IP"   : <IP ADDRESS OF URSAPQ MANAGER>,      # IP address of unix server in experimental rack  
    "UrsapqServer_Port" : <PORT (USUALLY 2222)>,
    "UrsapqServer_AuthKey" : <AUTH KEY>                        # Contained in the config script of the Unix server
  }
```
Additional paramters are needed to allow write access:

```
  "UrsapqServer_WritePort" :  <PORT (USUALLY 2223)>,
  "UrsapqServer_WriteKey"  : <AUTH KEY>                        # Contained in the config script of the Unix server
```

# UrsaPQ Console
This applet allows a cross-platform access to the experimental setup server. Users can monitor parameters and set values from multiple locations.
It functions as graphical user interface for the `ursapqUtils` module.

## Usage
Run the program with:

`python3 ursapqConsole.py`

On windows doubleclicking the `ursapqConsole.pyw` file launches the app suppressing the terminal window.

# UrsaPQ Online Data View
This applet allows a cross-platform access to the online data, after some basic processing. Multiple users can use the app simultaneusly. 

## Usage
Run the program with:

`python3 ursapqOnlineView.py`

Two windows will appear. One window contains the TOF traces from the MCP in the chamber and the trace from the optical laser. The other window will display a single shot spectras for even and odd (pumped and umpumped) shots and a difference spectrum (even-odd).

The slider can be used to control how much averaging should be done. Incoming data gets filtered with a lorenzian low pass filter, the slider value is the time constant of the lorentzian in seconds. Higher values lead to less noise but slower response to changes. Low values for quick response but more noise.

By default the single shot plots show the X axis as electron volts. Run `python3 ursapqOnlineView.py --tof` to see the time of flight instead.

# Cameras
Cameras can be viewed directly from the unix server, or by connecting to it via ssh using:

`ssh experimental@131.169.215.77 -X`

## Webcams
To view the two webcams, use `guvcview -d /dev/video1` and `guvcview -d /dev/video0`. 

## Telescope
To view the telescope camera, you can run pylon viewer with: `/opt/pylon/bin/pylonviewer`. Click on the name of the camera in the drop down menu and then press the video icon on the toolbar to start streaming the images.

The default image is rotated upside down. You can turn it by selecting the "bottom up" option in the advanced options. I suggest you also turn on auto exposure and auto white balance.


