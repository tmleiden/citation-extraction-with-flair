import re
import csv

punctuation = (',','.','"',':',';',')','(')

def isnumber (w):
    return bool(re.match("[0-9.,-]+",w))

def isyear (w):
    return bool(re.match("(\(?19[0-9][0-9]|20[012][0-9])\)?",w))

def isname (w):
    return bool(re.match("[A-Z][a-z-]+",w))

def ispages (w):
    return bool(re.match("[0-9]+-[0-9]+",w))

def haspunctuation (w):
    return bool(re.match(".*[,.\"':;()]+.*",w))




def word2features(text, i):
    word = text[i][0]
    postag = text[i][1]
    features = {
        'bias': 1.0,
        'word.lower()': word.lower(),
        'word[-3:]': word[-3:], # last 3 characters of word
        'word[-2:]': word[-2:],
        'word.isupper()': word.isupper(),
        'word.istitle()': word.istitle(),
        'word.isdigit()': word.isdigit(),
        'word.ispunct' : word in punctuation,
        'word.isnumber' : isnumber(word),
        'word.isyear' : isyear(word),
        'word.isname' : isname(word),
        'word.ispages' : ispages(word),
#        'word.isauthorname' : word in authornames,
#        'word.isjournalword' : word.lower() in journalwords,
        # these features were removed because we cannot distribute the WoS files with this information
        'postag': postag,
        #'postag[:2]': postag[:2], # first two characters of postag
    }

    if i > 0:
        word1 = text[i-1][0]
        postag1 = text[i-1][1]
        features.update({
            '-1:word.lower()': word1.lower(),
            '-1:word.istitle()': word1.istitle(),
            '-1:word.isupper()': word1.isupper(),
            '-1:word.ispunct' : word1 in punctuation,
            '-1:word.isnumber' : isnumber(word1),
            '-1:postag': postag1,
            #'-1:postag[:2]': postag1[:2],
        })
    else:
        features['BOS'] = True
    if i > 1:
        word2 = text[i-2][0]
        postag2 = text[i-2][1]
        features.update({
            '-2:word.lower()': word2.lower(),
            '-2:word.istitle()': word2.istitle(),
            '-2:word.isupper()': word2.isupper(),
            '-2:word.ispunct' : word2 in punctuation,
            '-2:word.isnumber' : isnumber(word2),
            '-2:postag': postag2,
            #'-1:postag[:2]': postag1[:2],
        })

    if i < len(text)-1:
        word1 = text[i+1][0]
        postag1 = text[i+1][1]
        features.update({
            '+1:word.lower()': word1.lower(),
            '+1:word.istitle()': word1.istitle(),
            '+1:word.isupper()': word1.isupper(),
            '+1:word.ispunct' : word1 in punctuation,
            '+1:word.isnumber' : isnumber(word1),
            '+1:postag': postag1,
            #'+1:postag[:2]': postag1[:2],
        })
    else:
        features['EOS'] = True
    if i < len(text)-2:
        word2 = text[i+2][0]
        postag2 = text[i+2][1]
        features.update({
            '+2:word.lower()': word2.lower(),
            '+2:word.istitle()': word2.istitle(),
            '+2:word.isupper()': word2.isupper(),
            '+2:word.ispunct' : word2 in punctuation,
            '+2:word.isnumber' : isnumber(word2),
            '+2:postag': postag2,
            #'+1:postag[:2]': postag1[:2],
        })

    return features

