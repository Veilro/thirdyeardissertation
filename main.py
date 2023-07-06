#!/usr/bin/env python

from midiutil import MIDIFile
import random

from torch import baddbmm;
import musicBase as mb
import noteGen as ng
import moodClassification as mc

#Key -2 is base   3 is treble

# calls functions in moodClassification.py to load initial values, the Key, and the Model
startkey, tempo, volume = mc.keyFromFile("input.txt")
mc.loadModel("j-hartmann/emotion-english-distilroberta-base")
ng.getKeyFromMood(mb.Keys[startkey], 1)

# arrays to hold the notes for the treble and bass clef
degrees = []
degreesB = []


targetMood = ng.Mood([0, 0, 0, 0], True)

# note = 0

noteArray = [mb.Note(ng.trebKey[0], 1, 1)]
noteArrayB = [mb.Note(ng.trebKey[0]-24, 1, 1)]

# starting chord to match the initial starting mood
degrees.append(mb.Chord(noteArray[0].pitch, 0 if ng.currMood.mood[3] > 0 else 1, 1, 1))

# MIDI has no way to define a rest other than the absence of a note
# this function adds a rest
def addRest(length, basetog):
    if (basetog == 0):
        if (len(degrees) > 0):
            degrees[-1].reltime += length
    else:
        if (len(degreesB) > 0):
            degreesB[-1].reltime += length

addRest(1, 1)

# Loads the array of targetmoods from the input text
targetarray = mc.getMoodsFromFile("input.txt")
# targetarray = [[1, 0, 0, 0],[1, 0, 0, 0],[1, 0, 0, 0],[1, 0, 0, 0],[1, 0, 0, 0],[1, 0, 0, 0],[1, 0, 0, 0],[1, 0, 0, 0]]
targetMood.addMood(targetarray[0])

trebdur = 0
bassdur = 0

# main loop, iterates over each of the target moods
for i in range(0, len(targetarray)):
    targetMood.printMood()

    # calls the Generation Algorithm to get the next note for the treble clef range
    temp = ng.getNextNote(ng.currMood, targetMood, noteArray, [60, 104], False)

    # If engagement is very low, only add bass clef notes
    if (ng.currMood.mood[2] > -0.75):
        # this prevents the treble and bass notes getting out of sync
        if (trebdur < bassdur + 4):    
            noteArray.append(temp[0])
            degrees.append(temp[0])
            trebdur += temp[0].reltime
    else:
        addRest(temp[0].duration, 0)

    # calls the Generation Algorithm to get the next note for the bass clef range
    tempB = ng.getNextNote(ng.currMood, targetMood, noteArrayB, [24, 59], True)

    # if pleasantness is very high then bass notes will not be added
    if (ng.currMood.mood[3] <= 0.8) :
        # this prevents the treble and bass notes getting out of sync
        if (bassdur < trebdur + 4):
            degreesB.append(tempB[0])
            noteArrayB.append(tempB[0])
            bassdur += tempB[0].reltime
    else:
        addRest(tempB[0].duration, 1)

    # increments currmood by a small fraction of the most recently added note
    ng.currMood.addMood([x / (20 + abs(5*ng.currMood.mood[2]))  for x in temp[2]])

    ng.updateParams()

    targetMood.addMood(targetarray[i])


track    = 0
channel  = 0
time     = 0    # In beats
duration = 1    # In beats

MyMIDI = MIDIFile(2) 
MyMIDI.addTempo(track, time, tempo)

# Adding the note arrays to the MIDI file itself
currtime = 0
currtimeB = 0
# Adding notes to treble clef
for i in range(len(degrees)):
    element = degrees[i]
    if (element.variant == "chord"):
        for j in element.buildTriad():
            MyMIDI.addNote(0, 0, j.pitch, currtime, j.duration, 100)
        currtime = currtime + element.reltime
    else:
        MyMIDI.addNote(0, 0, element.pitch, currtime, element.duration, 100)
        currtime = currtime + element.reltime

# Adding notes to bass clef
for i in range(len(degreesB)):
    element = degreesB[i]
    if (element.variant == "chord"):
        for j in element.buildTriad():
            MyMIDI.addNote(1, 0, j.pitch, currtimeB+1, j.duration, 100)
        currtimeB = currtimeB + element.reltime
    else:
        MyMIDI.addNote(1, 0, element.pitch, currtimeB+1, element.duration, 100)
        currtimeB = currtimeB + element.reltime


with open("output.mid", "wb") as output_file:
    MyMIDI.writeFile(output_file)