#!/usr/bin/env python

from midiutil import MIDIFile
import random;

# This file contains the base classes for generating music - representations for notes, chords and keys

# the chord structure for major, minor and diminished chords
diff = [[0, 4, 7], [0, 3, 7], [0, 3, 6]]
Keys = {}

# The class to represent a single musical note, contains pitch of the note, duration of the note, 
# and reltime, which denotes the distance between this note and the next note, in order to introduce rests in the midi file.
class Note:
    def __init__(self, pitch, duration, reltime):
        self.pitch = pitch
        self.duration = duration
        self.reltime = reltime
        self.variant = "note"


# This class builds simple triad chords from notes.
# Root refers to the root note of the chord
# Type refers to if the chord is major, minor or diminished
# Duration and Reltime refer to the same as the Note class
class Chord:
    def __init__(self, root, type, duration, reltime):
        self.root = root
        self.duration = duration
        self.reltime = reltime
        self.type = type
        self.variant = "chord"

    # builds the chord using the type patterns defined previously.
    def buildTriad(self):
        chord = []
        # major, minor, diminished
        chord.append(Note(self.root+diff[self.type][0], self.duration, self.reltime))
        chord.append(Note(self.root+diff[self.type][1], self.duration, self.reltime))
        chord.append(Note(self.root+diff[self.type][2], self.duration, self.reltime))
        return chord

    # helper function to find if a note is in chord - ignores duration
    def hasNote(self, note):
        for i in range(0, 3):
            if (note.pitch % 12 == self.buildTriad()[i].pitch % 12):
                return True
        return False

# This class defines a musical key based upon a root pitch, and a major/minor type
class Key:
    def __init__(self, root, type):
        self.root = root
        self.type = type

    # uses the major and minor key patterns to build a scale
    def buildKey(self):
        major = [0, 2, 2, 1, 2, 2, 2, 1]
        minor = [0, 2, 1, 2, 2, 1, 2, 2]
        currnote = self.root
        count = 0
        maxnote = 0
        key = []
        # separation of base clef and treble clef just to help with midi output
        if (self.root >= 60):
            maxnote = 95
        else:
            maxnote = 60

        #can go up to 127 but that is too high
        # iterates the scale up until the max note based off the root to build a full
        # set of possible notes for the key
        while (currnote < maxnote):
            if (self.type == 'M'):
                currnote = currnote + major[count]
            elif (self.type == 'm'):
                currnote = currnote + minor[count]
            key.append(currnote)
            if (count == 7):
                count = 1
            else:
                count = count + 1
        return key

# helper function to convert MIDI values into their associated notes - makes life easier
def midiToNote(convert):
    part1 = ""
    if (convert % 12 == 0):
        part1 = "C"
    elif (convert % 12 == 1):
        part1 = "C#"
    elif (convert % 12 == 2):
        part1 = "D"
    elif (convert % 12 == 3):
        part1 = "D#"
    elif (convert % 12 == 4):
        part1 = "E"
    elif (convert % 12 == 5):
        part1 = "F"
    elif (convert % 12 == 6):
        part1 = "F#"
    elif (convert % 12 == 7):
        part1 = "G"
    elif (convert % 12 == 8):
        part1 = "G#"
    elif (convert % 12 == 9):
        part1 = "A"
    elif (convert % 12 == 10):
        part1 = "A#"
    elif (convert % 12 == 11):
        part1 = "B"
    
    part2 = (convert // 12) - 2

    return part1 + str(part2)

# helper function to convert note values into the associated MIDI values
def noteToMidi(convert):
    part1 = ""
    check = convert[:1]
    if (convert[0] == "C"):
        part1 = 0
    elif (convert[0] == "D"):
        part1 = 2
    elif (convert[0] == "E"):
        part1 = 4
    elif (convert[0] == "F"):
        part1 = 5
    elif (convert[0] == "G"):
        part1 = 7
    elif (convert[0] == "A"):
        part1 = 9
    elif (convert[0] == "B"):
        part1 = 11
    
    if (convert[1] == "#"):
        part1 = part1 + 1

    part2 = int(convert[-1])
    if (convert[-2] == "-"):
        part2 = -part2
    
    return int(part1) + 12*(part2+2)


# Initialises the Key mood values on project load
file = open("baseKeys.txt", "r")
lines = file.readlines()
file.close()

for line in lines:
    line = line.rstrip("\n")
    temp = line.split("/")
    Keys[str(temp[0])] = eval(temp[1])
