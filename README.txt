Running simultions:
1) Install YADE-DEM, the code was tested to work with
    YADE version 2022.01a, and
    yade daily build 20260115-8983~7c8d01e~noble1
2) Execute yade simulation from command line
     Ubuntu 24.04:
          yadedaily simWheelTestRig.py
     Ubuntu 20.04:
           yade     simWheelTestRig.py
     This will use the default parameter file "paramsKyoto.json"
     An alternative parameter file with larger box and wheel can be used:
           yade     simWheelTestRig.py paramsSimpleLargeCylinder.json
3) 


YADE 3D display keyboard shortcuts
  x ... makes x-axis to point up
  y ... makes y-axis to point up
  z ... makes z-axis to point up
  c ... centers the view
  o ... zoom in angle view
  p ... zoom out angle view
    ... when display window has focus, press h to see all the shortcuts
  
