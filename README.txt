Instructions for using Yade DEM soil-wheel simulator

1) Install Yade:
      https://yade-dem.org/doc/
   The MSSTATE simulator "simWheelTestRigMSSTATE.py" works with
      A) Yade 2022.01a
      B) Yade daily build 20260115-8983~7c8d01e~noble1
   The University of Tokyo simulator "simWheelTestRigKyoto.py"
      (Nakanishi, JoT 2020 
         https://doi.org/10.1016/j.jterra.2020.10.001
       adapted to Python3) was tested to work with
      A) Yade 2022.01a

2) Execute the simulator using Yade from command line:
     A) Ubuntu 20.04 (YADE 2020.01a):
           "yade     simWheelTestRig.py"
     B) Ubuntu 24.04:
          "yadedaily simWheelTestRig.py"
     Press the "Play button" on the Yade controller to start.
       By default, the parameter file "paramsKyoto.json" is used.
       An alternative parameter can be supplied from command-line:
           "yade     simWheelTestRig.py <paramsKyotoModfied.json>"

YADE 3D display keyboard shortcuts:
  x ... makes x-axis to point up
  y ... makes y-axis to point up
  z ... makes z-axis to point up
  c ... centers the view
  o ... zoom in angle view
  p ... zoom out angle view
    ... when display window has focus, press "h" to see all the shortcuts
