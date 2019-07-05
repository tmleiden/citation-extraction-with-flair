# source: https://sklearn-crfsuite.readthedocs.io/en/latest/tutorial.html#let-s-use-conll-2002-data-to-build-a-ner-system


import os
import re
import numpy

import sklearn_crfsuite
from nltk import word_tokenize
from nltk import pos_tag
from sklearn.externals import joblib

import crf_features

groundtruth_bio_dir = 'data/ground_truth_bio/bio-origin'
unlabeled_txt_dir = 'path-to-directory-with-plain-text-patent-documents '
found_citations_dir = 'found_citations_in_unlabeled_CRF'
model_file_name = "crf_model_stored.pkl"

if not os.path.exists(found_citations_dir):
    os.makedirs(found_citations_dir)


training_filenames = os.listdir(groundtruth_bio_dir)
if '.DS_Store' in training_filenames:
    training_filenames.remove('.DS_Store')

unlabeled_filenames = os.listdir(unlabeled_txt_dir)



def text2features(text):
    return [crf_features.word2features(text, i) for i in range(len(text))]



def text2labels(text):
    return [label for token, postag, label in text]

def text2tokens(text):
    return [token for token, postag, label in text]

def label_count(y,label):
    return y.count(label)

def print_state_features(state_features):
    for (attr, label), weight in state_features:
        print("%0.6f %-8s %s" % (weight, label, attr))

def train():


    print("No pre-trained model. Train a model")

    traintext_per_filename = dict()
    print("Read BIO training files...")
    for filename in training_filenames:
        if '.bio' in filename:
            print(filename)
            items_for_this_file = []
            i = 0
            with open(groundtruth_bio_dir + "/" + filename, 'r', encoding='utf-8') as bio_file:

                for line in bio_file:
                    i += 1
                    columns = line.rstrip().split()

                    if len(columns) == 3:
                        word = columns[0]
                        pos = columns[1]
                        biotag = columns[2]
                        item = (word, pos, biotag)
                        items_for_this_file.append(item)

            traintext_per_filename[filename] = items_for_this_file

    train_texts = list()

    for trainfile in training_filenames:
        train_texts.append(traintext_per_filename[trainfile])

    print("Number of train texts:",len(train_texts))


    print ("Feature extraction for train set...")
    X_train = [text2features(t) for t in train_texts]
    y_train = [text2labels(t) for t in train_texts]


    for j in range(0, len(X_train)):
        X_first = X_train[j]
        y_first = y_train[j]
        for k in range(0,len(X_first)):
            if 'EOS' in X_first[k] and y_first[k] == "B":
                print (y_first[k],X_first[k])



    no_of_entities_per_train_text = [label_count(text_y,'B') for text_y in y_train]
    total_no_enitities_train = numpy.sum(no_of_entities_per_train_text)
    print("Number of citations (B) per text in train set:","(Total:",total_no_enitities_train,")",no_of_entities_per_train_text)


    print ("Initiate classifier...")
    crf = sklearn_crfsuite.CRF(
        algorithm='lbfgs',
        c1=0.1,
        c2=0.1,
        max_iterations=100,
        all_possible_transitions=True
    )

    print ("Fit classifier...")
    crf.fit(X_train, y_train)

    print ("Store the model for later re-use...")
    joblib.dump(crf, model_file_name, compress=9)


    return crf

def apply_model(unlabeled_filenames,crf):

    unlabeledtext_per_filename = dict()
    print ("Read unlabeled txt files...")
    for filename in unlabeled_filenames:
        if '.txt' in filename:
            print(filename)
            patent_id = re.sub(".txt", "", filename)
            items_for_this_file = []
            with open(unlabeled_txt_dir + "/" + filename, 'r', encoding='utf-8') as txtfile:
                text = txtfile.read()
                #tokenlist_from_nltk = []
                #pos_tag_list_from_nltk = []
                print("- POS tagging")
                pos_tagged_txt = pos_tag(word_tokenize(text))
                #print(pos_tagged_sent)
                for word_with_pos in pos_tagged_txt:
                    word = word_with_pos[0]
                    partofspeech = word_with_pos[1]
                    item = (word, partofspeech, "item")
                    items_for_this_file.append(item)

            unlabeledtext_per_filename[filename] = items_for_this_file
            unlabeled_texts = list()
            unlabeled_texts.append(items_for_this_file)
            print("- Feature extraction")
            X_single_unlabeled = [text2features(t) for t in unlabeled_texts]
            print("- Predict labels")
            y_pred = crf.predict(X_single_unlabeled)

            for text_i in range(0,len(unlabeled_texts)):
                # only one text in this array
                patent_id = re.sub(".txt","",filename)
                print("- Write to", found_citations_dir + "/" + patent_id + ".citations.txt")
                citations_in_unlabeled_outfile = open(found_citations_dir+"/"+patent_id+".citations.txt",'w',encoding='utf-8')
                citations_in_unlabeled_outfile.write("\n\n"+patent_id+"\n\n")

                text = unlabeled_texts[text_i]
                #print(patent_id)
                citation_text = ""
                for wordpos_i in range(len(text)):
                    if y_pred[text_i][wordpos_i] == "B":
                        citations_in_unlabeled_outfile.write(citation_text + "\n")
                        citation_text = text[wordpos_i][0]
                    elif y_pred[text_i][wordpos_i] == "I":
                        citation_text += " "+text[wordpos_i][0]
                citations_in_unlabeled_outfile.write(citation_text + "\n")
                citations_in_unlabeled_outfile.close()
                text_i += 1






if __name__ == "__main__":


    #crf = None
    if os.path.isfile(model_file_name):
        print("Load pre-trained crf model from disk...")
        crf = joblib.load(model_file_name)

    else:
        crf = train()



    apply_model(unlabeled_filenames,crf)


