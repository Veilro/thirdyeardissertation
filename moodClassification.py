# Import required packages
import tokenizers
import torch.nn as nn
import numpy as np
import noteGen as ng
import pandas as pd
import math
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer

# This file carries out the text analysis, and generating the target moods

# Code used is from HuggingFace data loading.
# Create class for data preparation
class SimpleDataset:
    def __init__(self, tokenized_texts):
        self.tokenized_texts = tokenized_texts
    
    def __len__(self):
        return len(self.tokenized_texts["input_ids"])
    
    def __getitem__(self, idx):
        return {k: v[idx] for k, v in self.tokenized_texts.items()}

# Load tokenizer and model, create trainer
def loadModel(model_name):
  # model_name = "j-hartmann/emotion-english-distilroberta-base"
  global model
  global tokenizer
  global trainer
  tokenizer = AutoTokenizer.from_pretrained(model_name)
  model = AutoModelForSequenceClassification.from_pretrained(model_name)
  trainer = Trainer(model=model) 

# Finds the overall label of a file, then uses this label to determine the initial key, tempo and volume values
def keyFromFile(filename):
  file = open(filename, "r")
  fstring = file.read()
  file.close()

  label = predict([fstring])[1][0]

  # Each key associated with the 6 Basic Emotions and the neutral class
  # Explained in greater depth in the report
  if (label == "joy"):
    return "EM", 110, 110
  elif (label == "neutral"):
    return "CM", 80, 90
  elif (label == "disgust"):
    return "Gm", 75, 100
  elif (label == "fear"):
    return "D#m", 100, 110
  elif (label == "sadness"):
    return "Fm", 70, 80
  elif (label == "anger"):
    return "BM", 105, 120
  else: #surprise
    return "DM", 95, 100

# This function creates the target mood array using the slices taken from the input text. 
def getMoodsFromFile(filename):
  file = open(filename, "r")
  fstring = file.read()
  file.close()

  wordsplit = fstring.split()

  # the maximum slicelength is 30 in order to capture the smaller changes in mood for larger texts 
  if (len(wordsplit) > 30):
    slicelength = 30
  else:
    slicelength = max(7, math.ceil(len(wordsplit)/(math.sqrt(len(wordsplit)/4))))
  inputmoods = []

  # iterates through the words to split the text into the required slices 
  for i, word in enumerate(wordsplit):
    inputmoods.append(word)
    for j in range(1, slicelength, int(slicelength/2)):
        if (i - j >= 0):
            inputmoods[i - j] = inputmoods[i - j] + " " + str(word)

  # removes end slices that are not of the correct length
  pred_texts = inputmoods[:-(slicelength-1)]
  
  return convertToCircumplex(predict(pred_texts)[0])

# converts the output of the neural network into the Watson Tellegen Circumplex representation
def convertToCircumplex(dataframe):
  mood = ng.Mood([0, 0, 0, 0], False)
  moodarray = []

  # the impact that each label has on the circumplex, adjusted to cover the entire range of moods
  angervals = [0.6, 0.1, 0.2, 0]
  disgustvals = [-0.2, 0.3, -0.1, -0.2]
  fearvals = [0.2, 1, 0.2, -0.1]
  joyvals = [1, -0.3, 0.2, 1]
  neutralvals = [-0.1, -0.2, -0.2, 0]
  sadnessvals = [-0.6, -0.2, -0.1, -1]
  surprisevals = [0.3, 0, 0.75, 0.1]

  valarray = [angervals, disgustvals, fearvals, joyvals, neutralvals, sadnessvals, surprisevals]

  moodOutput = open("moodOutput", "w")

  moodAverage = ng.Mood([0, 0, 0, 0], False)

  # multiplies the confidence of the predictions for each label by the label circumplex values to find
  for i in range(len(dataframe)):
    mood.updateMood([0,0,0,0])
    for j in range(0, 7):
      mood.addMood([x * (dataframe.iloc[i, j]) for x in valarray[j]])
    moodarray.append(mood.mood)
    moodAverage.addMood(mood.mood)
    moodOutput.write(str(mood.mood) + "\n")

  moodOutput.close()

  moodAverage = [x / len(moodarray) for x in moodAverage.mood]

  return moodarray

# this function carries out the prediction, based upon Hugging Face's sample code
def predict(string):
  # Tokenize texts and create prediction data set
  tokenized_texts = tokenizer(string,truncation=True,padding=True)
  pred_dataset = SimpleDataset(tokenized_texts)

  # Run predictions
  predictions = trainer.predict(pred_dataset)
  # Transform predictions to labels
  preds = predictions.predictions.argmax(-1)
  labels = pd.Series(preds).map(model.config.id2label)
  scores = (np.exp(predictions[0])/np.exp(predictions[0]).sum(-1,keepdims=True)).max(1)

  # scores raw
  temp = (np.exp(predictions[0])/np.exp(predictions[0]).sum(-1,keepdims=True))
  
  anger = []
  disgust = []
  fear = []
  joy = []
  neutral = []
  sadness = []
  surprise = []

  # extract scores (as many entries as exist in pred_texts)
  for i in range(len(string)):
    # labels.append
    anger.append(temp[i][0])
    disgust.append(temp[i][1])
    fear.append(temp[i][2])
    joy.append(temp[i][3])
    neutral.append(temp[i][4])
    sadness.append(temp[i][5])
    surprise.append(temp[i][6])

  # Create DataFrame with the confidences in each predicted label
  df = pd.DataFrame(list(zip(anger, disgust, fear, joy, neutral, sadness, surprise)), columns=['anger', 'disgust', 'fear', 'joy', 'neutral', 'sadness', 'surprise'])
  return df, labels

loadModel("j-hartmann/emotion-english-distilroberta-base")

print(keyFromFile("input.txt"))