#!/usr/bin/env python

from turtle import pos, update
from midiutil import MIDIFile
import random

from transformers import DPR_CONTEXT_ENCODER_PRETRAINED_MODEL_ARCHIVE_LIST;
import musicBase as mb
import numpy as np

# definition of Keys - set to C Major as a dummy value
currKey = []
bassKey = mb.Key(mb.noteToMidi("C0"), 'M').buildKey()
trebKey = mb.Key(mb.noteToMidi("C3"), 'M').buildKey()

lengtharray = [0.25, 0.5, 1, 2]

# generation parameters
# val, threshold, progress
variation = [3, 4, 0]
keychange = [0, 35]

# The Mood class, the main representation of the Watson-Tellegen Circumplex
class Mood: 
    def __init__(self, mood, resetMax):
        self.mood = mood
        # determines if a mood should be automatically reset back to 1
        # when it goes over or not, important for generation
        self.resetMax = resetMax
        if (type(mood) != list):
            self.mood = [mood, mood, mood, mood]

    # adds two moods together
    def addMood(self, nextMood):
        for i in range(0, len(self.mood)):
            test = nextMood[i]
            if (abs(test) > 0.01):
                self.mood[i] += test
            
            if (self.resetMax == True):
                if (self.mood[i] > 1):
                    self.mood[i] = 1
                elif (self.mood[i] < -1):
                    self.mood[i] = -1

    # sets the value of the mood to a given list
    def updateMood(self, moodup):
        self.mood = moodup

    # prints the mood
    def printMood(self):
        print(self.mood)

currMood = Mood([0, 0, 0, 0], True)

# this function finds the most mood accurate Key using the score formula
def getKeyFromMood(keyMood, setCurrMood):
    highscore = -9999
    returnKey = []
    for dictKey in mb.Keys:
        score = scoreFormula(mb.Keys[dictKey], keyMood)
        if (score > highscore):
            highscore = score
            returnKey = dictKey
    
    setKey(returnKey, setCurrMood, keyMood)

# This function sets the current Key value
def setKey(dictKey, setCurrMood, keymood):
    keyNote = ''
    if len(dictKey) == 3:
        keyNote = dictKey[0:2]
    else:
        keyNote = dictKey[0]

    global currKey
    currKey = [keyNote, dictKey[-1], mb.Keys[dictKey]]
    global trebKey
    global bassKey
    # treble Key and bass Key are handled separately cause of MIDI stuff
    trebKey = mb.Key(mb.noteToMidi(currKey[0] + "3"), currKey[1]).buildKey()
    bassKey = mb.Key(mb.noteToMidi(currKey[0] + "0"), currKey[1]).buildKey()
    if (setCurrMood == 1):
        currMood.updateMood(mb.Keys[dictKey])

# Updates the generation parameters
def updateParams():
    global variation
    global keychange

    # variation is tied to engagement
    variation[2] += currMood.mood[2]*1.5

    # variation increases if past the threshold
    if (variation[2] > variation[1]):
        if (variation[0] < 4):
            variation[0] += 1
        variation[2] = 0
    elif (variation[2] < -variation[1]):
        if (variation[0] > 2):
            variation[0] -= 1
        variation[2] = 0

    # manages key changes - if the current key has been far from the current mood
    # for too long, then update it
    keyscore = scoreFormula(currMood.mood, currKey[2])
    if keyscore < 0:
        keychange[0] += abs(keyscore)/10
    else:
        keychange[0] += 3

    if (keychange[0] > keychange[1]):
        getKeyFromMood(currMood.mood, 0)
        keychange[0] = 0

    # decay currmood so it doesnt always get stuck on the ends
    # allows more accurate changes in mood
    decay = [0, 0, 0, 0]
    for i in range(4):
        if (currMood.mood[i] > 0):
            decay[i] = -0.01
        else:
            decay[i] = 0.01
        if (currMood.mood[i] == 1):
            decay[i] = -0.2
        elif (currMood.mood[i] == -1):
            decay[i] = 0.2

    currMood.addMood(decay)
    

# Uses a range of values to find the array of possible next notes, 
# then evaluates which one should be added next based on variation
def getNextNote(currMood, targetMood, noteArray, noteRange, bass):
    if (len(noteArray) < variation[0]):
        variation[0] = len(noteArray)  

    # finds the set of possible next notes sorted by score
    posArray = nextPos(currMood.mood, targetMood.mood, noteArray, noteRange, bass)

    highNote = posArray[0]
    select = True
    # checks to see if a note has been used in a short time previously
    # based on variation - leads to an increase in engagement
    # if all notes have been used previously just uses the note with the highest score
    for i in posArray:
        for j in range(len(noteArray) - variation[0], len(noteArray)):
            if (i[0].pitch == noteArray[j].pitch):
                select = False
        if (select == True):
            return i
        else:
            select = True
        
    if (len(posArray) == 0):
        return highNote
    else:
        return posArray[0]
    

# evaluates the note moods using the score formula in order to find
# which notes can be used next
def nextPos(currMood, targetMood, noteArray, noteRange, bass):
    posarray = []
    highscore = -999
    # iterates through each possible next note to get the mood of each
    for i in range(noteRange[0], noteRange[1]):
        for j in lengtharray:
            temp = mb.Note(i, j, j)
            if (bass == True):
                mood = getMood(noteArray, temp, trebKey, 1)
            else:
                mood = getMood(noteArray, temp, bassKey, 1)
            score = scoreFormula(targetMood, mood)
            posarray.append([temp, score, mood])
            if (score > highscore):
                highscore = score

    returnarray = []

    posarray = sorted(posarray, key = lambda x: x[1], reverse = True)

    # finds the highest note in case no notes are suitable
    highNote = [posarray[0]]
    # appends all non-zero scored notes to an array
    for i in posarray:
        if (i[1] > 0):
            returnarray.append(i)
    if (len(returnarray) == 0):
        return highNote
    else:
        returnarray = sorted(returnarray, key = lambda x: x[1], reverse = True)
        return returnarray

# The score formula, finds the similarity between two moods
def scoreFormula(currMood, nextMood):
    score = 0
    for i in range(0, 4):
        diff = abs(currMood[i] - nextMood[i])
        # large differences between notes are penalised heavily
        if (diff > 1):
            score += -50 * diff
        else:
            score += (1 - diff) * 10

    return score

# finds the mood of a note based upon previous context of the song
def getMood(prevArray, note, currkey, weighting):
    noteMood = Mood([0, 0, 0, 0], False)
    if (prevArray == []): 
        return noteMood

    # if note is in currkey, lower negative effect, if it isn't, very high negative effect
    if (note.pitch in currkey):
        noteMood.addMood([0.2, -0.4, -0.15, 0.2])
    else:
        # if previous note in currkey or outside, the degree of negative effect changes
        if (prevArray[-1].pitch in currkey):
            noteMood.addMood([-0.2, 0.5, 0.05, -0.2])
        else:
            noteMood.addMood([-0.3, 0.3, 0.1, -0.2])

    # if same note, more of the same, less engagement - works across octaves
    if (note.pitch % 12 == prevArray[-1].pitch % 12):
        noteMood.addMood([0, 0, -0.2, 0])

    # gets the note interval value between current note and previous note
    if (len(prevArray) > 0):
        noteMood.addMood(intervalCalc(prevArray, note))

    # if note is different from previous note, slight increase in engagement
    if (note.pitch % 12 != prevArray[-1].pitch % 12):
        noteMood.addMood([0, 0, 0.05, 0])

    # higher pitch than previous not = more positive/pleasant effect - though a small effect
    if (note.pitch > prevArray[-1].pitch):
        noteMood.addMood([0.1, 0, 0.05, 0.1])

    # lower pitch than previous not = lower positive/pleasant effect
    if (note.pitch < prevArray[-1].pitch):
        noteMood.addMood([-0.05, 0, 0.05, -0.15])

    # octave jumps generate anxiety and increase engagement
    if (abs(note.pitch - prevArray[-1].pitch) > 13):
        noteMood.addMood([0, 0.15, 0.2, -0.05])
    else:
        noteMood.addMood([0, 0, -0.1, 0])

    # checks if part of minor or major chord
    # major chords are higher pleasantness, minor chords are less pleasantness
    # if part of either chord, reduced negative effect
    majorPrev = mb.Chord(prevArray[len(prevArray)-1].pitch, 0, 0, 0)
    if (majorPrev.hasNote(note)):
        noteMood.addMood([0.2, -0.15, 0.05, 0.2])
    
    minorPrev = mb.Chord(prevArray[len(prevArray)-1].pitch, 1, 0, 0)
    if (minorPrev.hasNote(note)):
        noteMood.addMood([-0.05, -0.1, -0.05, -0.2])

    # if part of tonic triad (basically the key chord) then greatly reduced 
    # negative effect and increased pleasantness
    keyChord = mb.Chord(trebKey[0], 0, 0, 0)
    if (keyChord.hasNote(note)):
        noteMood.addMood([0.3, -0.25, -0.1, 0.3])

    # Note pitch values:
    # too low makes it low pleasantness and low positive effect
    # too high causes anxiety/high negative effect
    # just in the sweetspot makes it high pleasantness
    if (note.pitch < 36):
        noteMood.addMood([-0.2, 0.4, 0, -0.2])
    elif (note.pitch < 48):
        noteMood.addMood([-0.1, 0.2, 0, -0.15])
    elif (note.pitch < 72):
        noteMood.addMood([0, 0, 0.05, -0.05])
    elif (note.pitch < 84):
        noteMood.addMood([0.2, -0.1, 0, 0.3])
    elif (note.pitch < 96):
        noteMood.addMood([0.25, -0.1, 0, 0.3])
    else:
        noteMood.addMood([0, 0.15, 0, 0.1])

    # check previous average pitch 
    sum = 0
    if (len(prevArray) < 4):
        max = len(prevArray)
    else:
        max = 4
    for i in range(1, max):
        sum += prevArray[-i].pitch
    sum /= max

    # checks if note average pitch is lower than the past five notes
    # if so, then lower pleasantness, otherwise higher
    if (note.pitch > sum):
        noteMood.addMood([0.1, 0, 0, 0.15])
    elif (note.pitch < sum):
        noteMood.addMood([-0.05, 0, -0.05, -0.15])

    # large octave jumps generally cause anxiety, so increased negative effect,
    # scaling with how large the actual jump is
    if abs(prevArray[-1].pitch - note.pitch) > 24:
        noteMood.addMood([0.05, 0.25, 0.15, 0])
    elif abs(prevArray[-1].pitch - note.pitch) > 12:
        noteMood.addMood([0.05, 0.1, 0.1, 0])
    else:
        noteMood.addMood([0, -0.05, 0, 0])


    # high engagement = more variable
    # high positive = tends to be shorter notes, quaver runs usually
    # low positive means longer notes and sometimes syncopation
    # high negative = slightly tends to be several shorter notes in a row

    # if the duration varies then higher engagement and negative effect
    if (note.duration != prevArray[-1].duration):
        noteMood.addMood([0, 0.05, 0.1, 0])
    else:
        noteMood.addMood([0, -0.1, -0.05, 0])
    
    # if the previous note was long, then lower engagement
    if (prevArray[-1].duration > 1):
        noteMood.addMood([-0.05, 0, -0.1, -0.05])
        # if this note is also long, then very low engagement and positive effect
        if (note.duration > 1):
            noteMood.addMood([-0.1, 0, -0.3, -0.05])

    # if current note is long, then lower positive effect and engagement
    if (note.duration > 1):
        noteMood.addMood([-0.1, 0, -0.1, 0])
    else:
        noteMood.addMood([0.1, 0, 0, 0])
        # if very short then higher positive effect and higher negative effect
        if (note.duration < 0.5):
            noteMood.addMood([0.1, 0.1, 0, 0])

    # if both notes are short, higher positive effect and higher negative effect
    if (note.duration < 1 and prevArray[-1].duration < 1):
        noteMood.addMood([0.1, 0.1, 0, 0])
        if (note.duration == prevArray[-1].duration):
            noteMood.addMood([0.1, -0.1, 0, 0.1])

    # low pleasantness slightly tends to syncopated long wait short long
    if (len(prevArray) > 2 and note.duration > 1 and prevArray[-1].duration < 2 and prevArray[-2].duration == 2):
        noteMood.addMood([-0.2, 0, -0.1, -0.2])
    
    # resets all mood values to 1 or -1 if they are over
    updatearray = []
    for val in noteMood.mood:
        if (val > 1):
            updatearray.append(1)
        elif (val < -1):
            updatearray.append(-1)
        else:
            updatearray.append(val)

    noteMood.updateMood(updatearray)
    return noteMood.mood

# This function handles the interval values - different intervals have different moods
def intervalCalc(prevArray, note):
    interval =  abs((note.pitch - prevArray[-1].pitch) % 12)
    intermood = []

    if (interval == 1):
        intermood = [-0.15, 0.4, 0.15, -0.1]
    elif (interval == 2):
        intermood = [0.05, 0.15, 0, 0]
    elif (interval == 3):
        intermood = [-0.05, 0, -0.1, -0.15]
    elif (interval == 4):
        intermood = [0.1, -0.05, 0, 0.2]
    elif (interval == 5):
        intermood = [-0.05, 0, 0.05, 0.1]
    elif (interval == 6):
        intermood = [0.1, 0.15, 0.1, -0.15]
    elif (interval == 7):
        intermood = [-0.1, 0.1, -0.05, 0.05]
    elif (interval == 8):
        intermood = [-0.1, 0.05, 0.15, -0.15]
    elif (interval == 9):
        intermood = [0.1, -0.1, 0.05, 0.15]
    elif (interval == 10):
        intermood = [-0.1, 0.15, 0.15, 0]
    else:
        intermood = [0.1, -0.1, 0.15, -0.1]

    return intermood


# getKeyFromMood([0.8, -0.8, 0, 0.8])
    

# currMood = [positive, negative, engagement, pleasant]


# print(scoreFormula([0.6, -0.3, 0.8, 0.6], [0.6, -0.3, 0.8, 0.6]))

# def chooseNote(currMood, prevNote):
#     score = 0
#     nextMood = [0, 0, 0, 0]
#     next = [0, 0, 0, 0]
#     note = mb.Note(trebKey[0], 1, 1)
#     for i in trebKey:
#         temp = mb.Note(i, 1, 1)
#         if (scoreFormula(currMood, getMood(prevNote, temp, trebKey, 1)) > score):
#             note = temp
#             next = getMood(prevNote, temp, trebKey, 1)

#     for j in range (0, 3):
#         nextMood[j] = currMood[j] + next[j]

#     return note, nextMood


# [0.6, 0.4, 1, 0.2] = base
# [0.55, 0.4, -1, 0.4] = next1
# [0.6, 0.3, 0.7, 0.3] = next2

# 0.05, 0, 2, 0.2
# 0, 0.1, 0.3, 0.1

