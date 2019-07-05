# source: https://sklearn-crfsuite.readthedocs.io/en/latest/tutorial.html#let-s-use-conll-2002-data-to-build-a-ner-system


import os
import numpy
import scipy.stats
from sklearn.metrics import make_scorer
#from sklearn.grid_search import RandomizedSearchCV
from collections import Counter
import sklearn_crfsuite
from sklearn_crfsuite import metrics

import crf_features

groundtruth_bio_dir = 'data/ground_truth_bio/bio-origin'

output_dir = 'data/crf_predicted_bio_out'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

fivefoldcrosval = True
leaveoneout = False

if fivefoldcrosval:
    print ("5-fold cross validation")
elif leaveoneout:
    print ("leave one out validation")
else:
    print ("set either fivefoldcrosval or leaveoneout")
    quit()

folds = dict()
folds[1] = ["US8168418B2.bio","US8293506B2.bio","US8114637B2.bio","US8048987B2.bio"]
folds[2] = ["US8227661B2.bio","US8106171B2.bio","US8273354B2.bio","US7892537B1.bio"]
folds[3] = ["US8409856B2.bio","US8133710B2.bio","US8158424B2.bio","US7972611B2.bio"]
folds[4] = ["US8338131B2.bio","US8258289B2.bio","US8058419B2.bio","US8299100B2.bio","US8158348B2.bio"]
folds[5] = ["US8148089B2.bio","US7943822B2.bio","US8124829B2.bio","US8088361B2.bio","US8092995B2.bio"]




all_filenames = os.listdir(groundtruth_bio_dir)
if '.DS_Store' in all_filenames:
    all_filenames.remove('.DS_Store')
#print(all_filenames)




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


def train_and_validate(train_texts,test_texts,testfile):

    print("Number of train texts:",len(train_texts))
    print("Number of test texts:",len(test_texts))


    print ("Feature extraction...")
    X_train = [text2features(t) for t in train_texts]
    y_train = [text2labels(t) for t in train_texts]


    X_test = [text2features(t) for t in test_texts]
    y_test = [text2labels(t) for t in test_texts]

    for j in range(0, len(X_train)):
        X_first = X_train[j]
        y_first = y_train[j]
        for k in range(0,len(X_first)):
            if 'EOS' in X_first[k] and y_first[k] == "B":
                print (y_first[k],X_first[k])



    no_of_entities_per_train_text = [label_count(text_y,'B') for text_y in y_train]
    no_of_entities_per_test_text = [label_count(text_y,'B') for text_y in y_test]
    total_no_enitities_train = numpy.sum(no_of_entities_per_train_text)
    total_no_enitities_test = numpy.sum(no_of_entities_per_test_text)
    print("Number of citations (B) per text in train set:","(Total:",total_no_enitities_train,")",no_of_entities_per_train_text)
    print("Number of citations (B) per text in test set:","(Total:",total_no_enitities_test,")",no_of_entities_per_test_text)


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
    labels = list(crf.classes_)

    """
    print("Tune hyperparameters")
    # define fixed parameters and parameters to search
    crf = sklearn_crfsuite.CRF(
        algorithm='lbfgs',
        max_iterations=100,
        all_possible_transitions=True
    )
    params_space = {
        'c1': scipy.stats.expon(scale=0.5),
        'c2': scipy.stats.expon(scale=0.05),
    }

    # use the same metric for evaluation
    f1_scorer = make_scorer(metrics.flat_f1_score,
                            average='weighted', labels=labels)
    recall_scorer = make_scorer(metrics.flat_recall_score,
                            average='weighted', labels=labels)

    # search
    rs = RandomizedSearchCV(crf, params_space,
                            cv=3,
                            verbose=1,
                        #    n_jobs=-1,
                        #    n_iter=50,
                            scoring=recall_scorer)
    rs.fit(X_train, y_train)


    print('best params:', rs.best_params_)
    print('best CV score:', rs.best_score_)
    print('model size: {:0.2f}M'.format(rs.best_estimator_.size_ / 1000000))

    # group B and I results


    crf = rs.best_estimator_
    """

    print ("Predict labels for test text...")

    labels.remove('O')
    sorted_labels = sorted(
        labels,
        key=lambda name: (name[1:], name[0])
    )

    y_pred = crf.predict(X_test)

    print(metrics.flat_classification_report(
        y_test, y_pred, labels=sorted_labels, digits=3
    ))


    with open(output_dir+"/"+str(testfile)+".pred",'w',encoding='utf-8') as predicted_out:
        text_i = 0
        for text in test_texts:
            for wordpos_i in range(len(text)):
                #print (text[wordpos_i][0],text[wordpos_i][1],y_pred[text_i][wordpos_i])
                predicted_out.write(text[wordpos_i][0]+"\t"+text[wordpos_i][1]+"\t"+y_pred[text_i][wordpos_i]+"\t"+y_test[text_i][wordpos_i]+"\n")
            text_i += 1

    predicted_out.close()

    #metrics.flat_f1_score(y_test, y_pred, average='weighted', labels=labels)



    print("\nTop positive:")
    print_state_features(Counter(crf.state_features_).most_common(10))

    print("\nTop negative:")
    print_state_features(Counter(crf.state_features_).most_common()[-10:])


if __name__ == "__main__":

    texts_per_fold = dict()
    example_texts = []
    text_per_filename = dict()
    print ("Read BIO files...")
    for filename in all_filenames:
        if '.bio' in filename:
            print(filename)
            items_for_this_file = []
            i = 0
            with open(groundtruth_bio_dir+"/"+filename,'r',encoding='utf-8') as bio_file:

                for line in bio_file:
                    i += 1
                    columns = line.rstrip().split()

                    if len(columns) == 3:
                        word = columns[0]
                        pos = columns[1]
                        biotag = columns[2]

                        item = (word,pos,biotag)
                        items_for_this_file.append(item)

                    #else:
                        #print("line does not have 3 columns!",filename,i,line)

            #if filename in train_files:
            #    train_texts.append(items_for_this_file)
            #elif filename in test_files:
            #    test_texts.append(items_for_this_file)
            #else:
            #    print("file",filename,"not in train or test")

            text_per_filename[filename] = items_for_this_file
            #print ("+",filename)
            if fivefoldcrosval:
                for fold in folds:
                    files_for_this_fold = folds[fold]
                    if filename in files_for_this_fold:
                        texts_for_this_fold = list()
                        if fold in texts_per_fold:
                            texts_for_this_fold= texts_per_fold[fold]
                        texts_for_this_fold.append(items_for_this_file)
                        texts_per_fold[fold] = texts_for_this_fold



    if fivefoldcrosval:
        #for testfold in [2]:
        for testfold in folds:
            test_texts = list()
            train_texts = list()
            print ("\n--------\ntestfold:",testfold,"number of texts:",len(texts_per_fold[testfold]),"\n--------\n")

            for text in texts_per_fold[testfold]:
                test_texts.append(text)
            for fold in folds:
                if fold != testfold:
                    for text in texts_per_fold[fold]:
                        train_texts.append(text)
            train_and_validate(train_texts,test_texts,testfold)

    elif leaveoneout:
        tcount = 0
        for testfile in all_filenames:
            tcount += 1
            print ("\n--------\ntest file:",testfile,"(",tcount,"of",len(all_filenames),")\n--------\n")
            test_texts = list()
            train_texts = list()
            testtext = text_per_filename[testfile]
            test_texts.append(testtext)
            for trainfile in all_filenames:
                if trainfile != testfile:
                    train_texts.append(text_per_filename[trainfile])

            train_and_validate(train_texts,test_texts,testfile)

