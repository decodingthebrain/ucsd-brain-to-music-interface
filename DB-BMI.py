#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy3 Experiment Builder (v2026.1.3),
    on Mon May  4 11:10:53 2026
If you publish work using this script the most relevant publication is:

    Peirce J, Gray JR, Simpson S, MacAskill M, Höchenberger R, Sogo H, Kastman E, Lindeløv JK. (2019) 
        PsychoPy2: Experiments in behavior made easy Behav Res 51: 195. 
        https://doi.org/10.3758/s13428-018-01193-y

"""

# --- Import packages ---
from psychopy import locale_setup
from psychopy import prefs
from psychopy import plugins
plugins.activatePlugins()
from psychopy import sound, gui, visual, core, data, event, logging, clock, colors, layout, hardware
from psychopy.tools import environmenttools
from psychopy.constants import (
    NOT_STARTED, STARTED, PLAYING, PAUSED, STOPPED, STOPPING, FINISHED, PRESSED, 
    RELEASED, FOREVER, priority
)

import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import (sin, cos, tan, log, log10, pi, average,
                   sqrt, std, deg2rad, rad2deg, linspace, asarray)
from numpy.random import random, randint, normal, shuffle, choice as randchoice
import os  # handy system and path functions
import sys  # to get file system encoding

from psychopy.hardware import keyboard

# Run 'Before Experiment' code from pieegRecord
import spidev
import threading
import csv as csv_module
import time
import os
from psychopy import core
from gpiozero import DigitalInputDevice

# --- Hardware Constants ---
DRDY_PIN = 24  
VREF = 4.5
GAIN = 24

# --- Pi 5 GPIO Setup ---
drdy = DigitalInputDevice(DRDY_PIN, pull_up=True, active_state=False)

# --- PiEEG SPI Setup ---
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 2000000
spi.mode = 0b01

# --- SPI Initialization ---
spi.xfer2([0x06])   # RESET
time.sleep(0.1)
spi.xfer2([0x11])   # SDATAC
time.sleep(0.1)
spi.xfer2([0x43, 0x00, 0xE0]) # CONFIG3
time.sleep(0.01)
spi.xfer2([0x45, 0x07, 0x60, 0x60, 0x60, 0x60, 0x60, 0x60, 0x60, 0x60]) # GAIN=24
time.sleep(0.01)
spi.xfer2([0x10])   # RDATAC
time.sleep(0.1)

# --- Threading Variables ---
eeg_stop_event = threading.Event()
eeg_data = []
eeg_lock = threading.Lock()
eeg_thread = None
drdy_timeouts = 0  # Tracks timing drift/glitches

# --- Failsafe Cleanup ---
def cleanup_spi():
    eeg_stop_event.set()
    if eeg_thread is not None:
        eeg_thread.join(timeout=1.0)
    try:
        spi.close()
        drdy.close() # Free GPIO to prevent hanging on exit
    except:
        pass
runAtExit.append(cleanup_spi)

def record_eeg():
    global eeg_data, drdy_timeouts
    sample_count = 0
    
    while not eeg_stop_event.is_set():
        # Polling: Wait up to 0.1s for DRDY
        drdy.wait_for_active(timeout=0.1)
        
        if not drdy.is_active:
            drdy_timeouts += 1  # Log dropped sample / glitch
            continue 
            
        raw = spi.readbytes(51) 
        timestamp = core.getTime()
        channels = []
        
        for ch in range(16): 
            byte1 = raw[3 + ch * 3]
            byte2 = raw[4 + ch * 3]
            byte3 = raw[5 + ch * 3]
            val = (byte1 << 16) | (byte2 << 8) | byte3
            
            if val >= 0x800000:
                val -= 0x1000000
            uv = val * (VREF / GAIN / (2**23 - 1)) * 1e6
            channels.append(round(uv, 4))
            
        with eeg_lock:
            eeg_data.append([timestamp] + channels)
            
        sample_count += 1
        
        # Lightweight Real-Time Monitoring (Outputs to PsychoPy Runner Console)
        # Prints a heartbeat every 250 samples (~1 second)
        if sample_count % 250 == 0:
            print(f"[PiEEG Heartbeat] {sample_count} samples. Ch1: {channels[0]:.2f} uV | Timeouts: {drdy_timeouts}")
# --- Setup global variables (available in all functions) ---
# create a device manager to handle hardware (keyboards, mice, mirophones, speakers, etc.)
deviceManager = hardware.DeviceManager()
# ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
# store info about the experiment session
psychopyVersion = '2026.1.3'
expName = 'DB-BMI'  # from the Builder filename that created this script
expVersion = ''
# a list of functions to run when the experiment ends (starts off blank)
runAtExit = []
# information about this experiment
expInfo = {
    'participant': f"{randint(0, 999999):06.0f}",
    'session': '001',
    'date|hid': data.getDateStr(),
    'expName|hid': expName,
    'expVersion|hid': expVersion,
    'psychopyVersion|hid': psychopyVersion,
}

# --- Define some variables which will change depending on pilot mode ---
'''
To run in pilot mode, either use the run/pilot toggle in Builder, Coder and Runner, 
or run the experiment with `--pilot` as an argument. To change what pilot 
#mode does, check out the 'Pilot mode' tab in preferences.
'''
# work out from system args whether we are running in pilot mode
PILOTING = core.setPilotModeFromArgs()
# start off with values from experiment settings
_fullScr = True
_winSize = (1024, 768)
# if in pilot mode, apply overrides according to preferences
if PILOTING:
    # force windowed mode
    if prefs.piloting['forceWindowed']:
        _fullScr = False
        # set window size
        _winSize = prefs.piloting['forcedWindowSize']
    # replace default participant ID
    if prefs.piloting['replaceParticipantID']:
        expInfo['participant'] = 'pilot'

def showExpInfoDlg(expInfo):
    """
    Show participant info dialog.
    Parameters
    ==========
    expInfo : dict
        Information about this experiment.
    
    Returns
    ==========
    dict
        Information about this experiment.
    """
    # show participant info dialog
    dlg = gui.DlgFromDict(
        dictionary=expInfo, sortKeys=False, title=expName, alwaysOnTop=True
    )
    if dlg.OK == False:
        core.quit()  # user pressed cancel
    # return expInfo
    return expInfo


def setupData(expInfo, dataDir=None):
    """
    Make an ExperimentHandler to handle trials and saving.
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    dataDir : Path, str or None
        Folder to save the data to, leave as None to create a folder in the current directory.    
    Returns
    ==========
    psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    """
    # remove dialog-specific syntax from expInfo
    for key, val in expInfo.copy().items():
        newKey, _ = data.utils.parsePipeSyntax(key)
        expInfo[newKey] = expInfo.pop(key)
    
    # data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
    if dataDir is None:
        dataDir = _thisDir
    filename = u'data/%s_%s_%s' % (expInfo['participant'], expName, expInfo['date'])
    # make sure filename is relative to dataDir
    if os.path.isabs(filename):
        dataDir = os.path.commonprefix([dataDir, filename])
        filename = os.path.relpath(filename, dataDir)
    
    # an ExperimentHandler isn't essential but helps with data saving
    thisExp = data.ExperimentHandler(
        name=expName, version=expVersion,
        extraInfo=expInfo, runtimeInfo=None,
        originPath='/Users/earanda/DB-BDJI-PSYCHOPY/DB-BMI.py',
        savePickle=True, saveWideText=True,
        dataFileName=dataDir + os.sep + filename, sortColumns='time'
    )
    # store pilot mode in data file
    thisExp.addData('piloting', PILOTING, priority=priority.LOW)
    thisExp.setPriority('thisRow.t', priority.CRITICAL)
    thisExp.setPriority('expName', priority.LOW)
    # return experiment handler
    return thisExp


def setupLogging(filename):
    """
    Setup a log file and tell it what level to log at.
    
    Parameters
    ==========
    filename : str or pathlib.Path
        Filename to save log file and data files as, doesn't need an extension.
    
    Returns
    ==========
    psychopy.logging.LogFile
        Text stream to receive inputs from the logging system.
    """
    # set how much information should be printed to the console / app
    if PILOTING:
        logging.console.setLevel(
            prefs.piloting['pilotConsoleLoggingLevel']
        )
    else:
        logging.console.setLevel('warning')
    # save a log file for detail verbose info
    logFile = logging.LogFile(filename+'.log')
    if PILOTING:
        logFile.setLevel(
            prefs.piloting['pilotLoggingLevel']
        )
    else:
        logFile.setLevel(
            logging.getLevel('info')
        )
    
    return logFile


def setupWindow(expInfo=None, win=None):
    """
    Setup the Window
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    win : psychopy.visual.Window
        Window to setup - leave as None to create a new window.
    
    Returns
    ==========
    psychopy.visual.Window
        Window in which to run this experiment.
    """
    if PILOTING:
        logging.debug('Fullscreen settings ignored as running in pilot mode.')
    
    if win is None:
        # if not given a window to setup, make one
        win = visual.Window(
            size=_winSize, fullscr=_fullScr, screen=0,
            winType='pyglet', allowGUI=False, allowStencil=False,
            monitor='testMonitor', color=(-1.0000, -1.0000, -1.0000), colorSpace='rgb',
            backgroundImage='', backgroundFit='none',
            blendMode='avg', useFBO=True,
            units='height',
            checkTiming=False  # we're going to do this ourselves in a moment
        )
    else:
        # if we have a window, just set the attributes which are safe to set
        win.color = (-1.0000, -1.0000, -1.0000)
        win.colorSpace = 'rgb'
        win.backgroundImage = ''
        win.backgroundFit = 'none'
        win.units = 'height'
    if expInfo is not None:
        # get/measure frame rate if not already in expInfo
        if win._monitorFrameRate is None:
            win._monitorFrameRate = win.getActualFrameRate(infoMsg='Attempting to measure frame rate of screen, please wait...')
        expInfo['frameRate'] = win._monitorFrameRate
    win.hideMessage()
    if PILOTING:
        # show a visual indicator if we're in piloting mode
        if prefs.piloting['showPilotingIndicator']:
            win.showPilotingIndicator()
        # always show the mouse in piloting mode
        if prefs.piloting['forceMouseVisible']:
            win.mouseVisible = True
    
    return win


def setupDevices(expInfo, thisExp, win):
    """
    Setup whatever devices are available (mouse, keyboard, speaker, eyetracker, etc.) and add them to 
    the device manager (deviceManager)
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window in which to run this experiment.
    Returns
    ==========
    bool
        True if completed successfully.
    """
    # --- Setup input devices ---
    ioConfig = {}
    ioSession = ioServer = eyetracker = None
    
    # store ioServer object in the device manager
    deviceManager.ioServer = ioServer
    
    # create a default keyboard (e.g. to check for escape)
    if deviceManager.getDevice('defaultKeyboard') is None:
        deviceManager.addDevice(
            deviceClass='keyboard', deviceName='defaultKeyboard', backend='ptb'
        )
    # return True if completed successfully
    return True

def pauseExperiment(thisExp, win=None, timers=[], currentRoutine=None):
    """
    Pause this experiment, preventing the flow from advancing to the next routine until resumed.
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window for this experiment.
    timers : list, tuple
        List of timers to reset once pausing is finished.
    currentRoutine : psychopy.data.Routine
        Current Routine we are in at time of pausing, if any. This object tells PsychoPy what Components to pause/play/dispatch.
    """
    # if we are not paused, do nothing
    if thisExp.status != PAUSED:
        return
    
    # start a timer to figure out how long we're paused for
    pauseTimer = core.Clock()
    # pause any playback components
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.pause()
    # make sure we have a keyboard
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        defaultKeyboard = deviceManager.addKeyboard(
            deviceClass='keyboard',
            deviceName='defaultKeyboard',
            backend='PsychToolbox',
        )
    # run a while loop while we wait to unpause
    while thisExp.status == PAUSED:
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=['escape']):
            endExperiment(thisExp, win=win)
        # dispatch messages on response components
        if currentRoutine is not None:
            for comp in currentRoutine.getDispatchComponents():
                comp.device.dispatchMessages()
        # sleep 1ms so other threads can execute
        clock.time.sleep(0.001)
    # if stop was requested while paused, quit
    if thisExp.status == FINISHED:
        endExperiment(thisExp, win=win)
    # resume any playback components
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.play()
    # reset any timers
    for timer in timers:
        timer.addTime(-pauseTimer.getTime())


def run(expInfo, thisExp, win, globalClock=None, thisSession=None):
    """
    Run the experiment flow.
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    psychopy.visual.Window
        Window in which to run this experiment.
    globalClock : psychopy.core.clock.Clock or None
        Clock to get global time from - supply None to make a new one.
    thisSession : psychopy.session.Session or None
        Handle of the Session object this experiment is being run from, if any.
    """
    # mark experiment as started
    thisExp.status = STARTED
    # update experiment info
    expInfo['date'] = data.getDateStr()
    expInfo['expName'] = expName
    expInfo['expVersion'] = expVersion
    expInfo['psychopyVersion'] = psychopyVersion
    # make sure window is set to foreground to prevent losing focus
    win.winHandle.activate()
    # make sure variables created by exec are available globally
    exec = environmenttools.setExecEnvironment(globals())
    # get device handles from dict of input devices
    ioServer = deviceManager.ioServer
    # get/create a default keyboard (e.g. to check for escape)
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        deviceManager.addDevice(
            deviceClass='keyboard', deviceName='defaultKeyboard', backend='PsychToolbox'
        )
    eyetracker = deviceManager.getDevice('eyetracker')
    # make sure we're running in the directory for this experiment
    os.chdir(_thisDir)
    # get filename from ExperimentHandler for convenience
    filename = thisExp.dataFileName
    frameTolerance = 0.001  # how close to onset before 'same' frame
    endExpNow = False  # flag for 'escape' or other condition => quit the exp
    # get frame duration from frame rate in expInfo
    if 'frameRate' in expInfo and expInfo['frameRate'] is not None:
        frameDur = 1.0 / round(expInfo['frameRate'])
    else:
        frameDur = 1.0 / 60.0  # could not measure, so guess
    
    # Start Code - component code to be run after the window creation
    
    # --- Initialize components for Routine "Welcome" ---
    instructionsText = visual.TextStim(win=win, name='instructionsText',
        text='You will close your eyes and listen to a song\n\nAfter the song, a beep will play signalling to open your eyes.\n\nYou will rate the song from 1-7.\n\n\n',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color=(1.0000, 1.0000, 1.0000), colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    welcomeText = visual.TextStim(win=win, name='welcomeText',
        text='Welcome to Decoded Brain Brain-Music-Interface\n',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-1.0);
    # Run 'Begin Experiment' code from code_2
    counter = 0
    
    # --- Initialize components for Routine "CloseEyes_Song" ---
    CloseEyesText = visual.TextStim(win=win, name='CloseEyesText',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-1.0);
    # set audio backend
    sound.Sound.backend = 'ptb'
    song1 = sound.Sound(
        'A', 
        secs=-1, 
        stereo=True, 
        hamming=True, 
        speaker=None,    name='song1'
    )
    song1.setVolume(1.0)
    # Run 'Begin Experiment' code from code
    counter += 1
    
    # --- Initialize components for Routine "RateSong" ---
    beep = sound.Sound(
        'A', 
        secs=1.0, 
        stereo=True, 
        hamming=True, 
        speaker=None,    name='beep'
    )
    beep.setVolume(1.0)
    RateSongText = visual.TextStim(win=win, name='RateSongText',
        text='Rate the song from 1 (Strongly Dislike) - 7 (Strongly Like)\n\nPress [1], [2], [3], [4], [5], [6], or [7]',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-1.0);
    key_resp = keyboard.Keyboard(deviceName='defaultKeyboard')
    
    # --- Initialize components for Routine "Familiarity" ---
    FamiliarityText = visual.TextStim(win=win, name='FamiliarityText',
        text='Were you already familiar with this song? \n\nPress [y] for yes, [n] for no',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    key_resp_2 = keyboard.Keyboard(deviceName='defaultKeyboard')
    
    # --- Initialize components for Routine "ThankYou" ---
    ThankYouText = visual.TextStim(win=win, name='ThankYouText',
        text='Thank you for listening\n\nPlease come back soon!',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # create some handy timers
    
    # global clock to track the time since experiment started
    if globalClock is None:
        # create a clock if not given one
        globalClock = core.Clock()
    if isinstance(globalClock, str):
        # if given a string, make a clock accoridng to it
        if globalClock == 'float':
            # get timestamps as a simple value
            globalClock = core.Clock(format='float')
        elif globalClock == 'iso':
            # get timestamps in ISO format
            globalClock = core.Clock(format='%Y-%m-%d_%H:%M:%S.%f%z')
        else:
            # get timestamps in a custom format
            globalClock = core.Clock(format=globalClock)
    if ioServer is not None:
        ioServer.syncClock(globalClock)
    logging.setDefaultClock(globalClock)
    if eyetracker is not None:
        eyetracker.enableEventReporting()
    # routine timer to track time remaining of each (possibly non-slip) routine
    routineTimer = core.Clock()
    win.flip()  # flip window to reset last flip timer
    # store the exact time the global clock started
    expInfo['expStart'] = data.getDateStr(
        format='%Y-%m-%d %Hh%M.%S.%f %z', fractionalSecondDigits=6
    )
    
    # --- Prepare to start Routine "Welcome" ---
    # create an object to store info about Routine Welcome
    Welcome = data.Routine(
        name='Welcome',
        components=[instructionsText, welcomeText],
    )
    Welcome.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for Welcome
    Welcome.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    Welcome.tStart = globalClock.getTime(format='float')
    Welcome.status = STARTED
    thisExp.addData('Welcome.started', Welcome.tStart)
    Welcome.maxDuration = None
    # keep track of which components have finished
    WelcomeComponents = Welcome.components
    for thisComponent in Welcome.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "Welcome" ---
    thisExp.currentRoutine = Welcome
    Welcome.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine and routineTimer.getTime() < 16.0:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *instructionsText* updates
        
        # if instructionsText is starting this frame...
        if instructionsText.status == NOT_STARTED and tThisFlip >= 3-frameTolerance:
            # keep track of start time/frame for later
            instructionsText.frameNStart = frameN  # exact frame index
            instructionsText.tStart = t  # local t and not account for scr refresh
            instructionsText.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(instructionsText, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'instructionsText.started')
            # update status
            instructionsText.status = STARTED
            instructionsText.setAutoDraw(True)
        
        # if instructionsText is active this frame...
        if instructionsText.status == STARTED:
            # update params
            pass
        
        # if instructionsText is stopping this frame...
        if instructionsText.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > instructionsText.tStartRefresh + 13.0-frameTolerance:
                # keep track of stop time/frame for later
                instructionsText.tStop = t  # not accounting for scr refresh
                instructionsText.tStopRefresh = tThisFlipGlobal  # on global time
                instructionsText.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'instructionsText.stopped')
                # update status
                instructionsText.status = FINISHED
                instructionsText.setAutoDraw(False)
        
        # *welcomeText* updates
        
        # if welcomeText is starting this frame...
        if welcomeText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            welcomeText.frameNStart = frameN  # exact frame index
            welcomeText.tStart = t  # local t and not account for scr refresh
            welcomeText.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(welcomeText, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'welcomeText.started')
            # update status
            welcomeText.status = STARTED
            welcomeText.setAutoDraw(True)
        
        # if welcomeText is active this frame...
        if welcomeText.status == STARTED:
            # update params
            pass
        
        # if welcomeText is stopping this frame...
        if welcomeText.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > welcomeText.tStartRefresh + 3.0-frameTolerance:
                # keep track of stop time/frame for later
                welcomeText.tStop = t  # not accounting for scr refresh
                welcomeText.tStopRefresh = tThisFlipGlobal  # on global time
                welcomeText.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'welcomeText.stopped')
                # update status
                welcomeText.status = FINISHED
                welcomeText.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=Welcome,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            Welcome.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if Welcome.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in Welcome.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "Welcome" ---
    for thisComponent in Welcome.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for Welcome
    Welcome.tStop = globalClock.getTime(format='float')
    Welcome.tStopRefresh = tThisFlipGlobal
    thisExp.addData('Welcome.stopped', Welcome.tStop)
    # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
    if Welcome.maxDurationReached:
        routineTimer.addTime(-Welcome.maxDuration)
    elif Welcome.forceEnded:
        routineTimer.reset()
    else:
        routineTimer.addTime(-16.000000)
    thisExp.nextEntry()
    
    # set up handler to look after randomisation of conditions etc
    trials = data.TrialHandler2(
        name='trials',
        nReps=5, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=data.importConditions('dur_song_diversity_100.csv - Sheet1.csv'), 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(trials)  # add the loop to the experiment
    thisTrial = trials.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
    if thisTrial != None:
        for paramName in thisTrial:
            globals()[paramName] = thisTrial[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisTrial in trials:
        trials.status = STARTED
        if hasattr(thisTrial, 'status'):
            thisTrial.status = STARTED
        currentLoop = trials
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
        if thisTrial != None:
            for paramName in thisTrial:
                globals()[paramName] = thisTrial[paramName]
        
        # --- Prepare to start Routine "CloseEyes_Song" ---
        # create an object to store info about Routine CloseEyes_Song
        CloseEyes_Song = data.Routine(
            name='CloseEyes_Song',
            components=[CloseEyesText, song1],
        )
        CloseEyes_Song.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from pieegRecord
        with eeg_lock:
            eeg_data.clear()
        
        drdy_timeouts = 0 # Reset glitch tracker for this trial
        eeg_stop_event.clear()
        
        eeg_thread = threading.Thread(target=record_eeg, daemon=True)
        eeg_thread.start()
        CloseEyesText.setText('Please close your eyes\n\nThe song will begin to play shortly\n')
        song1.setSound(filePath, hamming=True)
        song1.setVolume(1.0, log=False)
        song1.seek(0)
        # store start times for CloseEyes_Song
        CloseEyes_Song.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        CloseEyes_Song.tStart = globalClock.getTime(format='float')
        CloseEyes_Song.status = STARTED
        thisExp.addData('CloseEyes_Song.started', CloseEyes_Song.tStart)
        CloseEyes_Song.maxDuration = None
        # keep track of which components have finished
        CloseEyes_SongComponents = CloseEyes_Song.components
        for thisComponent in CloseEyes_Song.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "CloseEyes_Song" ---
        thisExp.currentRoutine = CloseEyes_Song
        CloseEyes_Song.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisTrial, 'status') and thisTrial.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *CloseEyesText* updates
            
            # if CloseEyesText is starting this frame...
            if CloseEyesText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                CloseEyesText.frameNStart = frameN  # exact frame index
                CloseEyesText.tStart = t  # local t and not account for scr refresh
                CloseEyesText.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(CloseEyesText, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'CloseEyesText.started')
                # update status
                CloseEyesText.status = STARTED
                CloseEyesText.setAutoDraw(True)
            
            # if CloseEyesText is active this frame...
            if CloseEyesText.status == STARTED:
                # update params
                pass
            
            # if CloseEyesText is stopping this frame...
            if CloseEyesText.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > CloseEyesText.tStartRefresh + 5.0-frameTolerance:
                    # keep track of stop time/frame for later
                    CloseEyesText.tStop = t  # not accounting for scr refresh
                    CloseEyesText.tStopRefresh = tThisFlipGlobal  # on global time
                    CloseEyesText.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'CloseEyesText.stopped')
                    # update status
                    CloseEyesText.status = FINISHED
                    CloseEyesText.setAutoDraw(False)
            
            # *song1* updates
            
            # if song1 is starting this frame...
            if song1.status == NOT_STARTED and tThisFlip >= 5-frameTolerance:
                # keep track of start time/frame for later
                song1.frameNStart = frameN  # exact frame index
                song1.tStart = t  # local t and not account for scr refresh
                song1.tStartRefresh = tThisFlipGlobal  # on global time
                # add timestamp to datafile
                thisExp.addData('song1.started', tThisFlipGlobal)
                # update status
                song1.status = STARTED
                song1.play(when=win)  # sync with win flip
            
            # if song1 is stopping this frame...
            if song1.status == STARTED:
                if bool(False) or song1.isFinished:
                    # keep track of stop time/frame for later
                    song1.tStop = t  # not accounting for scr refresh
                    song1.tStopRefresh = tThisFlipGlobal  # on global time
                    song1.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'song1.stopped')
                    # update status
                    song1.status = FINISHED
                    song1.stop()
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=CloseEyes_Song,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                CloseEyes_Song.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if CloseEyes_Song.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in CloseEyes_Song.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "CloseEyes_Song" ---
        for thisComponent in CloseEyes_Song.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # Run 'End Routine' code from pieegRecord
        # 1. Stop the thread gracefully
        eeg_stop_event.set()
        
        if eeg_thread is not None:
            eeg_thread.join(timeout=2.0) 
        
        # 2. Extract data safely under lock, then release lock immediately
        with eeg_lock:
            data_to_save = list(eeg_data) # Create a static copy
            eeg_data.clear()              # Clear main list for next trial
        
        # 3. Perform slow File I/O outside of the lock
        if data_to_save:
            os.makedirs('data', exist_ok=True)
            song_basename = os.path.splitext(os.path.basename(filePath))[0]
            eeg_filename = f"data/{expInfo['participant']}_{expName}_trial{trials.thisN}_{song_basename}_eeg.csv"
            
            with open(eeg_filename, 'w', newline='') as f:
                writer = csv_module.writer(f)
                writer.writerow([
                    'timestamp_s', 
                    'ch1_uV', 'ch2_uV', 'ch3_uV', 'ch4_uV', 
                    'ch5_uV', 'ch6_uV', 'ch7_uV', 'ch8_uV',
                    'ch9_uV', 'ch10_uV', 'ch11_uV', 'ch12_uV', 
                    'ch13_uV', 'ch14_uV', 'ch15_uV', 'ch16_uV'
                ])
                writer.writerows(data_to_save)
                    
            thisExp.addData('eeg_file', eeg_filename)
            thisExp.addData('eeg_samples', len(data_to_save))
            thisExp.addData('drdy_timeouts', drdy_timeouts) # Log dropped frames
        else:
            thisExp.addData('eeg_file', 'NO_DATA')
            thisExp.addData('eeg_samples', 0)
            thisExp.addData('drdy_timeouts', drdy_timeouts)
        # store stop times for CloseEyes_Song
        CloseEyes_Song.tStop = globalClock.getTime(format='float')
        CloseEyes_Song.tStopRefresh = tThisFlipGlobal
        thisExp.addData('CloseEyes_Song.stopped', CloseEyes_Song.tStop)
        song1.pause()  # ensure sound has stopped at end of Routine
        # the Routine "CloseEyes_Song" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "RateSong" ---
        # create an object to store info about Routine RateSong
        RateSong = data.Routine(
            name='RateSong',
            components=[beep, RateSongText, key_resp],
        )
        RateSong.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        beep.setSound('beep-09.mp3', secs=1.0, hamming=True)
        beep.setVolume(1.0, log=False)
        beep.seek(0)
        # create starting attributes for key_resp
        key_resp.keys = []
        key_resp.rt = []
        _key_resp_allKeys = []
        # store start times for RateSong
        RateSong.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        RateSong.tStart = globalClock.getTime(format='float')
        RateSong.status = STARTED
        thisExp.addData('RateSong.started', RateSong.tStart)
        RateSong.maxDuration = None
        # keep track of which components have finished
        RateSongComponents = RateSong.components
        for thisComponent in RateSong.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "RateSong" ---
        thisExp.currentRoutine = RateSong
        RateSong.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisTrial, 'status') and thisTrial.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *beep* updates
            
            # if beep is starting this frame...
            if beep.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                beep.frameNStart = frameN  # exact frame index
                beep.tStart = t  # local t and not account for scr refresh
                beep.tStartRefresh = tThisFlipGlobal  # on global time
                # add timestamp to datafile
                thisExp.addData('beep.started', tThisFlipGlobal)
                # update status
                beep.status = STARTED
                beep.play(when=win)  # sync with win flip
            
            # if beep is stopping this frame...
            if beep.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > beep.tStartRefresh + 1.0-frameTolerance or beep.isFinished:
                    # keep track of stop time/frame for later
                    beep.tStop = t  # not accounting for scr refresh
                    beep.tStopRefresh = tThisFlipGlobal  # on global time
                    beep.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'beep.stopped')
                    # update status
                    beep.status = FINISHED
                    beep.stop()
            
            # *RateSongText* updates
            
            # if RateSongText is starting this frame...
            if RateSongText.status == NOT_STARTED and tThisFlip >= 1.0-frameTolerance:
                # keep track of start time/frame for later
                RateSongText.frameNStart = frameN  # exact frame index
                RateSongText.tStart = t  # local t and not account for scr refresh
                RateSongText.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(RateSongText, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'RateSongText.started')
                # update status
                RateSongText.status = STARTED
                RateSongText.setAutoDraw(True)
            
            # if RateSongText is active this frame...
            if RateSongText.status == STARTED:
                # update params
                pass
            
            # *key_resp* updates
            waitOnFlip = False
            
            # if key_resp is starting this frame...
            if key_resp.status == NOT_STARTED and tThisFlip >= 1.0-frameTolerance:
                # keep track of start time/frame for later
                key_resp.frameNStart = frameN  # exact frame index
                key_resp.tStart = t  # local t and not account for scr refresh
                key_resp.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(key_resp, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'key_resp.started')
                # update status
                key_resp.status = STARTED
                # keyboard checking is just starting
                waitOnFlip = True
                win.callOnFlip(key_resp.clock.reset)  # t=0 on next screen flip
                win.callOnFlip(key_resp.clearEvents, eventType='keyboard')  # clear events on next screen flip
            if key_resp.status == STARTED and not waitOnFlip:
                theseKeys = key_resp.getKeys(keyList=['1','2','3','4','5', '6','7'], ignoreKeys=["escape"], waitRelease=False)
                _key_resp_allKeys.extend(theseKeys)
                if len(_key_resp_allKeys):
                    key_resp.keys = _key_resp_allKeys[-1].name  # just the last key pressed
                    key_resp.rt = _key_resp_allKeys[-1].rt
                    key_resp.duration = _key_resp_allKeys[-1].duration
                    # a response ends the routine
                    continueRoutine = False
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=RateSong,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                RateSong.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if RateSong.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in RateSong.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "RateSong" ---
        for thisComponent in RateSong.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for RateSong
        RateSong.tStop = globalClock.getTime(format='float')
        RateSong.tStopRefresh = tThisFlipGlobal
        thisExp.addData('RateSong.stopped', RateSong.tStop)
        beep.pause()  # ensure sound has stopped at end of Routine
        # check responses
        if key_resp.keys in ['', [], None]:  # No response was made
            key_resp.keys = None
        trials.addData('key_resp.keys',key_resp.keys)
        if key_resp.keys != None:  # we had a response
            trials.addData('key_resp.rt', key_resp.rt)
            trials.addData('key_resp.duration', key_resp.duration)
        # the Routine "RateSong" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "Familiarity" ---
        # create an object to store info about Routine Familiarity
        Familiarity = data.Routine(
            name='Familiarity',
            components=[FamiliarityText, key_resp_2],
        )
        Familiarity.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # create starting attributes for key_resp_2
        key_resp_2.keys = []
        key_resp_2.rt = []
        _key_resp_2_allKeys = []
        # store start times for Familiarity
        Familiarity.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        Familiarity.tStart = globalClock.getTime(format='float')
        Familiarity.status = STARTED
        thisExp.addData('Familiarity.started', Familiarity.tStart)
        Familiarity.maxDuration = None
        # keep track of which components have finished
        FamiliarityComponents = Familiarity.components
        for thisComponent in Familiarity.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "Familiarity" ---
        thisExp.currentRoutine = Familiarity
        Familiarity.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisTrial, 'status') and thisTrial.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *FamiliarityText* updates
            
            # if FamiliarityText is starting this frame...
            if FamiliarityText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                FamiliarityText.frameNStart = frameN  # exact frame index
                FamiliarityText.tStart = t  # local t and not account for scr refresh
                FamiliarityText.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(FamiliarityText, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'FamiliarityText.started')
                # update status
                FamiliarityText.status = STARTED
                FamiliarityText.setAutoDraw(True)
            
            # if FamiliarityText is active this frame...
            if FamiliarityText.status == STARTED:
                # update params
                pass
            
            # *key_resp_2* updates
            waitOnFlip = False
            
            # if key_resp_2 is starting this frame...
            if key_resp_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                key_resp_2.frameNStart = frameN  # exact frame index
                key_resp_2.tStart = t  # local t and not account for scr refresh
                key_resp_2.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(key_resp_2, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'key_resp_2.started')
                # update status
                key_resp_2.status = STARTED
                # keyboard checking is just starting
                waitOnFlip = True
                win.callOnFlip(key_resp_2.clock.reset)  # t=0 on next screen flip
                win.callOnFlip(key_resp_2.clearEvents, eventType='keyboard')  # clear events on next screen flip
            if key_resp_2.status == STARTED and not waitOnFlip:
                theseKeys = key_resp_2.getKeys(keyList=['y','n'], ignoreKeys=["escape"], waitRelease=False)
                _key_resp_2_allKeys.extend(theseKeys)
                if len(_key_resp_2_allKeys):
                    key_resp_2.keys = _key_resp_2_allKeys[-1].name  # just the last key pressed
                    key_resp_2.rt = _key_resp_2_allKeys[-1].rt
                    key_resp_2.duration = _key_resp_2_allKeys[-1].duration
                    # a response ends the routine
                    continueRoutine = False
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=Familiarity,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                Familiarity.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if Familiarity.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in Familiarity.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "Familiarity" ---
        for thisComponent in Familiarity.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for Familiarity
        Familiarity.tStop = globalClock.getTime(format='float')
        Familiarity.tStopRefresh = tThisFlipGlobal
        thisExp.addData('Familiarity.stopped', Familiarity.tStop)
        # check responses
        if key_resp_2.keys in ['', [], None]:  # No response was made
            key_resp_2.keys = None
        trials.addData('key_resp_2.keys',key_resp_2.keys)
        if key_resp_2.keys != None:  # we had a response
            trials.addData('key_resp_2.rt', key_resp_2.rt)
            trials.addData('key_resp_2.duration', key_resp_2.duration)
        # the Routine "Familiarity" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        # mark thisTrial as finished
        if hasattr(thisTrial, 'status'):
            thisTrial.status = FINISHED
        # if awaiting a pause, pause now
        if trials.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            trials.status = STARTED
        thisExp.nextEntry()
        
    # completed 5 repeats of 'trials'
    trials.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # --- Prepare to start Routine "ThankYou" ---
    # create an object to store info about Routine ThankYou
    ThankYou = data.Routine(
        name='ThankYou',
        components=[ThankYouText],
    )
    ThankYou.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for ThankYou
    ThankYou.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    ThankYou.tStart = globalClock.getTime(format='float')
    ThankYou.status = STARTED
    thisExp.addData('ThankYou.started', ThankYou.tStart)
    ThankYou.maxDuration = None
    # keep track of which components have finished
    ThankYouComponents = ThankYou.components
    for thisComponent in ThankYou.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "ThankYou" ---
    thisExp.currentRoutine = ThankYou
    ThankYou.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine and routineTimer.getTime() < 5.0:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *ThankYouText* updates
        
        # if ThankYouText is starting this frame...
        if ThankYouText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            ThankYouText.frameNStart = frameN  # exact frame index
            ThankYouText.tStart = t  # local t and not account for scr refresh
            ThankYouText.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(ThankYouText, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'ThankYouText.started')
            # update status
            ThankYouText.status = STARTED
            ThankYouText.setAutoDraw(True)
        
        # if ThankYouText is active this frame...
        if ThankYouText.status == STARTED:
            # update params
            pass
        
        # if ThankYouText is stopping this frame...
        if ThankYouText.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > ThankYouText.tStartRefresh + 5-frameTolerance:
                # keep track of stop time/frame for later
                ThankYouText.tStop = t  # not accounting for scr refresh
                ThankYouText.tStopRefresh = tThisFlipGlobal  # on global time
                ThankYouText.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'ThankYouText.stopped')
                # update status
                ThankYouText.status = FINISHED
                ThankYouText.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=ThankYou,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            ThankYou.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if ThankYou.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in ThankYou.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "ThankYou" ---
    for thisComponent in ThankYou.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for ThankYou
    ThankYou.tStop = globalClock.getTime(format='float')
    ThankYou.tStopRefresh = tThisFlipGlobal
    thisExp.addData('ThankYou.stopped', ThankYou.tStop)
    # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
    if ThankYou.maxDurationReached:
        routineTimer.addTime(-ThankYou.maxDuration)
    elif ThankYou.forceEnded:
        routineTimer.reset()
    else:
        routineTimer.addTime(-5.000000)
    thisExp.nextEntry()
    # Run 'End Experiment' code from pieegRecord
    try:
        spi.close()
        drdy.close()
    except:
        pass
    
    # mark experiment as finished
    endExperiment(thisExp, win=win)


def saveData(thisExp):
    """
    Save data from this experiment
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    """
    filename = thisExp.dataFileName
    # these shouldn't be strictly necessary (should auto-save)
    thisExp.saveAsWideText(filename + '.csv', delim='auto')
    thisExp.saveAsPickle(filename)


def endExperiment(thisExp, win=None):
    """
    End this experiment, performing final shut down operations.
    
    This function does NOT close the window or end the Python process - use `quit` for this.
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window for this experiment.
    """
    # stop any playback components
    if thisExp.currentRoutine is not None:
        for comp in thisExp.currentRoutine.getPlaybackComponents():
            comp.stop()
    if win is not None:
        # remove autodraw from all current components
        win.clearAutoDraw()
        # Flip one final time so any remaining win.callOnFlip() 
        # and win.timeOnFlip() tasks get executed
        win.flip()
    # return console logger level to WARNING
    logging.console.setLevel(logging.WARNING)
    # mark experiment handler as finished
    thisExp.status = FINISHED
    # run any 'at exit' functions
    for fcn in runAtExit:
        fcn()
    logging.flush()


def quit(thisExp, win=None, thisSession=None):
    """
    Fully quit, closing the window and ending the Python process.
    
    Parameters
    ==========
    win : psychopy.visual.Window
        Window to close.
    thisSession : psychopy.session.Session or None
        Handle of the Session object this experiment is being run from, if any.
    """
    thisExp.abort()  # or data files will save again on exit
    # make sure everything is closed down
    if win is not None:
        # Flip one final time so any remaining win.callOnFlip() 
        # and win.timeOnFlip() tasks get executed before quitting
        win.flip()
        win.close()
    logging.flush()
    if thisSession is not None:
        thisSession.stop()
    # terminate Python process
    core.quit()


# if running this experiment as a script...
if __name__ == '__main__':
    # call all functions in order
    expInfo = showExpInfoDlg(expInfo=expInfo)
    thisExp = setupData(expInfo=expInfo)
    logFile = setupLogging(filename=thisExp.dataFileName)
    win = setupWindow(expInfo=expInfo)
    setupDevices(expInfo=expInfo, thisExp=thisExp, win=win)
    run(
        expInfo=expInfo, 
        thisExp=thisExp, 
        win=win,
        globalClock='float'
    )
    saveData(thisExp=thisExp)
    quit(thisExp=thisExp, win=win)
