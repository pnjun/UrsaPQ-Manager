UrsaPQ - Console
======

This applet allows a cross-platform access to the experimental setup server. Users can monitor parameters and set values. 
It functions as graphical user interface for the `ursapqUtils` module.

## Install
Clone this repo and create a config.json file in the `Utils/ursapqConsoleResources/` folder with the following info:
```
  {
    "UrsapqServer_IP"   : <IP ADDRESS OF URSAPQ MANAGER>,
    "UrsapqServer_Port" : <PORT (USUALLY 2222)>,
    "UrsapqServer_AuthKey" : <AUTH KEY>
  }
```

## Usage
Run the program with:

`python3 ursapqConsole.py`

On windows doubleclicking the `ursapqConsole.pyw` file launches the app as well.
