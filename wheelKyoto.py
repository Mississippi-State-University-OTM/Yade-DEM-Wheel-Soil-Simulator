# coding: utf-8
# import yade modules that we will use below
from yade import pack,plot,qt
import numpy as np
import math,time

debugSegFault=False
if debugSegFault:
    import faulthandler
    faulthandler.enable()

plotLive=False # show live plot window during simulation
# variable for timecalculator()
timestart=time.time()
# the unit of length is m
width=.1 # width of wheel
radius =.20/2 # case of D = 220 mm with LH = 10 mm
hw=width/2
hr=radius /2
lugh=.01 # lug height
lugt=.005 # lug thickness
angvel =.138*20 # (rad/s)
tractionf=4.9 # traction load: 0.0, 4.9, 9.8, 12.5, 14.7 N
segnum=18 # the number of partitions of wheel (the number of lugs)
pscale=1.0 # particle scale
partnum=round(80000/pscale**3) # the number of particles
print(f"number of particles, requested {partnum}")
wheelweight=.5 # the weight of wheel
wheeldensity=wheelweight/((width*radius*4*math.pi*radius/(1.95* segnum)+width*2*lugh*lugt)*segnum)
timestep=.00001 #when changed, interperiod in forcerecorder,xyzforce,slipplot should also be changed
waitfor=200000 # the time step for beginning of wheel rotate
hplus=0.5 # the height of wheel at the start of simulation
# file name of force data file and simulation data file
fileName='PIDrotate_tractionF_'+str(tractionf)+'N' # may be changed
savefileName='save' # may be changed

# specify materials
O.materials.append(FrictMat(density=wheeldensity,frictionAngle=math.atan(.5), young=1e9,poisson=0.3,label='wheelmat'))
O.materials.append(FrictMat(density=2830,frictionAngle=2*math.pi*36.7/360,young =.5e6,poisson=0.3,label='wallmat'))
O.materials.append(FrictMat(density=2830,frictionAngle=math.atan(.0),young=.5e6, poisson=0.3,label='mat1'))
# create rectangular box from facets
O.bodies.append(geom.facetBox((0,0,0),(.15/2,1./2,.5/2),wallMask=31,material='wallmat'))
# create wheel and lugs
j=0
while -1<j<segnum-1:
    O.bodies.append(box((0,-.35+hr*math.cos((j+.5)*2*math.pi/segnum),-.5/2+.23+.12+hplus+hr*math.sin((j+.5)*2*math.pi/segnum)),
                        (hw,hr,2*math.pi*radius/(1.95* segnum)),
                        orientation=Quaternion((1,0,0), (j+.5)*2*math.pi/segnum),
                        color=(.71,.71,.71),material='wheelmat'))
    O.bodies.append(box((0,-.35+radius*math.cos(j*2*math.pi/segnum),-.5/2+.23+.12+hplus+radius*math.sin(j*2*math.pi/segnum)),
                        (hw,lugh,lugt/2),orientation=Quaternion((1, 0, 0), j*2*math.pi/segnum),
                        color=(.7,.7,.7),material='wheelmat'))
    j+=1
O.bodies.append([box((0,-.35+hr*math.cos((segnum-1+.5)*2*math.pi/segnum),-.5/2+.23+.12+hplus+hr*math.sin((segnum-1+.5)*2*math.pi/segnum)),
                     (hw,hr,2*math.pi*radius/(1.95* segnum)),orientation=Quaternion((1,0,0),(segnum-1+.5)*2*math.pi/segnum),color=(.71,.71,.71),material='wheelmat')])
O.bodies.appendClumped([box((0,-.35+radius*math.cos((segnum-1)*2*math.pi/segnum),-.5/2+.23+.12+hplus+radius*math.sin((segnum-1)*2*math.pi/segnum)),
                            (hw,lugh,lugt/2),orientation=Quaternion((1,0,0), (segnum-1)*2*math.pi/segnum),color=(.7,.7,.7),material='wheelmat')])
o=9+2* segnum
print(f"number of objects {o}")

clump=O.bodies[o+1]
i=10
while 9<i<o:
    O.bodies.addToClump([i],o+1)
    i+=1
# create empty sphere packing
# sphere packing is not equivalent to particles in simulation, it contains only the pure geometry
sp=pack.SpherePack()
S1r=pack.SpherePack([((0,0,0),pscale*.00225)])
S1=pack.SpherePack([((0,0,0),pscale*.0025)])
S1R=pack.SpherePack ([((0,0,0),pscale*.00275)])
# generate randomly spheres with uniform radius distribution
sp.makeClumpCloud((-.15/2, -1./2, -.5/2),
                  ( .15/2,  1./2, -.5/2+.225513+hplus),
                  [S1, S1r, S1R],
                  num=partnum, seed=12345)
# add the sphere pack to the simulation
sp.toSimulation(color=(.6,.57,.53))
nb=len(O.bodies);
print(f"number of bodies {nb}")

# engines which run while simulation
O.engines = [
    ForceResetter(),
    InsertionSortCollider([Bo1_Sphere_Aabb(),Bo1_Facet_Aabb(),Bo1_Box_Aabb()]),
    InteractionLoop(
        [Ig2_Sphere_Sphere_ScGeom(),Ig2_Facet_Sphere_ScGeom(),
         Ig2_Box_Sphere_ScGeom(),Ig2_Box_Sphere_ScGeom6D()],
        [Ip2_FrictMat_FrictMat_MindlinPhys(en=.3,krot=.00005,label='ContactModel')],
        [Law2_ScGeom_MindlinPhys_Mindlin(label='Mindlin',includeMoment=True)]
    ),
    PyRunner(command='addforce()',iterPeriod=1,firstIterRun=waitfor,dead=False), # dead=True for constant wheel slip
    PyRunner(command='addvforce()',iterPeriod=1,firstIterRun=waitfor//2+20000,dead=False),
    TorqueEngine(ids=[o+1],moment=(0,0,0)), # give torque on wheel, which controlled by PIDcontroller()
    NewtonIntegrator(gravity=(0,0,-9.81),damping=0.0), # calculate forces and give gravity force
    RotationEngine(ids = [o+1], angularVelocity = 0,dead=False), # used to fix wheel at consolidation step
    PyRunner(command='tirepos0()',iterPeriod=1,nDo=waitfor -1,dead=False),
    PyRunner(command='tirepos()',iterPeriod=1,firstIterRun=waitfor),
    PyRunner(command='savefile1s()', iterPeriod=1,firstIterRun=waitfor//2,nDo=1,dead=False),
    PyRunner(command='savefile2s()', iterPeriod=1,firstIterRun=waitfor  ,nDo=1,dead=False),
    PyRunner(command='O.bodies[100].material.frictionAngle=2*math.pi*36.7/360',iterPeriod=1,firstIterRun=waitfor//2,nDo=1,dead=False),
    PyRunner(command='O.engines[7].dead=True', iterPeriod=1,firstIterRun=waitfor//2,nDo=1,dead=False),
    PyRunner(command='heightadjuster()', iterPeriod=1,firstIterRun=waitfor//2,nDo=1,dead=False),
    PyRunner(command='time1s=time.time()', iterPeriod=1,firstIterRun=waitfor//2,nDo = 1,dead=False),
    PyRunner(command='time2s=time.time()', iterPeriod=1,firstIterRun=waitfor,nDo=1,dead=False),
    PyRunner(command='timefinish=time.time()', iterPeriod=1,firstIterRun=450000,nDo = 1,dead=False),
    PyRunner(command='timecalculator()', iterPeriod=1,firstIterRun=450000,nDo=1,dead=False),
    PyRunner(command='plot.saveDataTxt("plot_end.txt")', iterPeriod=1,firstIterRun=450000,nDo=1,dead=False),
    PyRunner(command='plot.plot(noShow=True).savefig("plot_end.pdf")', iterPeriod=1,firstIterRun=450000,nDo=1,dead=False)
]
# specify time increments
O.dt=timestep
initori=clump.state.ori
globals()['initori']=locals()['initori']
# enable energy tracking; any simulation parts supporting it
# can create and update arbitrary energy types, which can be
# accessed as O.energy['energyName'] subsequently
O.trackEnergy=True

# give traction force
def addforce():
    O.forces.addF(o+1,(0,-tractionf,0))
    clump.state.angMom[1]=0
    clump.state.angMom[2]=0

globals()['addforce']=locals()['addforce']
# give vertical force on wheel
def addvforce():
    O.forces.addF(o+1,(0,0,-14.695)) # 19.6 N for 1g

globals()['addvforce']=locals()['addvforce']
# used to fix wheel while wheel driving
def tirepos():
    clump.state.pos=(0,clump.state.pos[1],clump.state.pos[2]) # constant drawbar load

# used to fix wheel at wheel sinkage step
def tirepos0():
    clump.state.ori=initori
    clump.state.pos=(0,-.35,clump.state.pos[2])

def savefile1s():
    O.save(savefileName+'_1s.bz2')

def savefile2s():
    O.save(savefileName+'_2s.bz2')

diff0=0
integral=0
def PIDcontroller():
    ku=300
    pu=.00001
    kp=0.6*ku*.7      # Kp parameter (PID)
    ki=kp/(0.5*pu)*.7 # Ki parameter (PID)
    ki=kp/(0.5*pu)*.7 # Ki parameter (PID)
    kd=kp*0.125*pu*.7 # Kd parameter (PID)
    global diff0
    global integral
    diff=-angvel-clump.state.angVel[0]
    integral+=diff*O.dt
    torque=kp*diff+ki*integral+kd*(diff-diff0)/O.dt
    O.engines [5].moment=(torque,0,0)
    #print O.iter,diff,integral,torque
    diff0=diff

O.engines+=[PyRunner(command='PIDcontroller()',iterPeriod=1,firstIterRun=waitfor+1)]
globals()['diff0']=locals()['diff0']
globals()['integral']=locals()['integral']
globals()['PIDcontroller']=locals()['PIDcontroller']

# move wheel to the surface of soil
def heightadjuster():
    hh=-.5/2
    idx = None
    for i in range(o+2,o+2+partnum):
        if O.bodies[i].state.pos[2]>hh:
            hh=O.bodies[i].state.pos[2]
            idx=i
    if idx is not None:
        r=O.bodies[idx].shape.radius
        O.bodies[o+1].state.pos=Vector3(0,-0.35,hh+r+radius+lugh+.0001)

globals()['heightadjuster']=locals()['heightadjuster']
def timecalculator():
    time0sto1s=time1s-timestart
    time0sto2s=time2s-timestart
    time0stofinish=timefinish-timestart
    time1sto2s=time2s-time1s
    time1stofinish=timefinish-time1s
    time2stofinish=timefinish-time2s
    print('0s to 1s: {0} s'.format(time0sto1s))
    print('0s to 2s: {0} s'.format(time0sto2s))
    print('0s to finish: {0} s'.format(time0stofinish))
    print('2s to finish: {0} s'.format(time2stofinish))
    f = open('calltime_'+fileName+'.txt','w')
    f.write('0s to 1s: {0} s\n'.format(time0sto1s))
    f.write('0s to 2s: {0} s\n'.format(time0sto2s))
    f.write('0s to finish: {0} s\n'.format(time0stofinish))
    f.write('1s to 2s:c{0} s\n'.format(time1sto2s))
    f.write('1s to finish: {0} s\n'.format(time1stofinish))
    f.write('2s to finish: {0} s\n'.format(time2stofinish))
    f.close()

globals()['timecalculator']=locals()['timecalculator']
# record forces, torque and so on.
def xyzforce():
    x2=sum(O.forces.f(k)[0] for k in range(10,o+1))
    y2=sum(O.forces.f(k)[1] for k in range(10,o+1))
    z2=sum(O.forces.f(k)[2] for k in range(10,o+1))
    gt=-O.engines[5].moment[0]/(radius+lugh)
    mr=gt-y2
    pos=O.bodies[o+1].state.pos[2]
    vel=O.bodies[o+1].state.vel[1]
    try:sl=1-(O.bodies[o+1].state.vel[1] / ((radius+lugh) * (-clump.state.angVel[0])))
    except:sl=1-(O.bodies[o+1].state.vel[1]/((radius+lugh)*(angvel)))
    plot.addData(t=O.time,Fx=x2,Fy=y2,Fz=z2,grosstraction=gt,motionresistance=mr,
        i=O.time,height=pos* 1000,velocity=vel,slip=sl*100, angveln=clump.state.
        angVel[0],h=pos)

globals()['xyzforce']=locals()['xyzforce']
globals()['plot']=locals()['plot']
globals()['np']=locals()['np']
globals()['o']=locals()['o']
globals()['segnum']=locals()['segnum']
globals()['tirepos']=locals()['tirepos']
globals()['tirepos0']=locals()['tirepos0']
globals()['clump']=locals()['clump']
globals()['waitfor']=locals()['waitfor']
globals()['savefile1s']=locals()['savefile1s']
globals()['savefile2s']=locals()['savefile2s']
globals()['lugh']=locals()['lugh']
globals()['timestart']=locals()['timestart']
globals()['fileName']=locals()['fileName']
globals()['tractionf']=locals()['tractionf']
globals()['savefileName']=locals()['savefileName']
O.engines+=[PyRunner(command='xyzforce()',iterPeriod=500,firstIterRun=waitfor//2)]
# define how to plot data: 'i' (step number) on the x-axis, unbalanced force
# on the left y-axis, all energies on the right y-axis
# (O.energy.keys is function which will be called to get all defined energies)
# None separates left and right y-axis
plot.plots={
    't':('Fx','Fy','Fz','grosstraction','motionresistance'),'i':('h','slip')
}
# show the plot on the screen, and update while the simulation runs
if plotLive:
    plot.plot()
# save simulation to memory
O.saveTmp()
# display GUI controller
yade.qt.Controller()
# qt.Controller() ## for new version of YADE, says copilot
# run the simulation
# stop the simulation after 450001 time steps
O.stopAtIter=450001 ## set stopAfter before run, says copilot
O.run()
## O.stopAtIter=450001
