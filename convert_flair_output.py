
import json
import os
import re
from collections import defaultdict

flair_output_dir = "data/allpatents_tagged/"
found_citations_dir = 'data/found_citations_in_unlabeled_Flair2'

count_per_predicted_label = defaultdict(int)


for filename in os.listdir(flair_output_dir):
    if "tags_" in filename and not "citations" in filename:
        patent_id = re.sub("tags_", "", filename)
        patent_id = re.sub(".txt", "", patent_id)
        citations_in_unlabeled_outfile = open(found_citations_dir + "/" + patent_id + ".citations.txt", 'w',
                                              encoding='utf-8')
        citations_in_unlabeled_outfile.write("\n\n" + patent_id + "\n\n")

        ''' Process Flair output file with labels'''
        with open(flair_output_dir+filename,'r',encoding='utf-8') as flairfile:
            print (filename)
            flair_text = flairfile.read()
        flairfile.close()

        predicted_word_sequence = []
        predicted_label_sequence = []
        predicted_pos_sequence = []
        predicted_entities = []

        flair_text = re.sub('^\[\'','',flair_text)
        flair_text = re.sub('\'\]$','',flair_text)
        flair_text = re.sub(r"\\n",'',flair_text)
        flair_text = re.sub(r"', \"","', '",flair_text)
        flair_text = re.sub("\", '","', '",flair_text)
        paragraphs = flair_text.split("', '")


        for par in paragraphs:
            if len(par) > 0:

                #print(par)
                words_and_tags = par.split(" ")

                entity = []

                for i in range(0,len(words_and_tags)):
                    #print(i,words_and_tags[i])
                    if i < len(words_and_tags)-1 and words_and_tags[i+1] == "<B>":
                        if len(entity) > 0:
                            #print("NEXT; SAVE",i,entity)
                            predicted_entities.append(" ".join(entity))
                        entity = []
                        predicted_word_sequence.append(words_and_tags[i])
                        predicted_label_sequence.append("B")
                        #i += 1 # current item is not a token
                        entity.append(words_and_tags[i])
                        #print ("Start of citation:",i,words_and_tags[i])
                        count_per_predicted_label['B'] += 1

                    elif i < len(words_and_tags)-1 and words_and_tags[i+1] == "<I>":
                        predicted_label_sequence.append("I")
                        #if i < len(words_and_tags)-1:
                        #    i += 1 # current item is not a token
                        predicted_word_sequence.append(words_and_tags[i])
                        entity.append(words_and_tags[i])
                        #print("In citation:",i,words_and_tags[i])
                        count_per_predicted_label['I'] += 1
                    elif (i == len(words_and_tags)-1 or (i < len(words_and_tags)-1 and words_and_tags[i+1] not in ('<B>','<I>')))\
                            and words_and_tags[i] not in ('<B>','<I>'):
                        #print("Outside citation:",i,words_and_tags[i])
                        predicted_label_sequence.append("O")
                        predicted_word_sequence.append(words_and_tags[i])
                    #else:
                    #    print("skip, not a token but a tag",i,words_and_tags[i])
                if len(entity) > 0:
                    #print("LAST; SAVE",i,entity)
                    predicted_entities.append(" ".join(entity))




        for entity in predicted_entities:
            #print("-",entity)
            citations_in_unlabeled_outfile.write(entity + "\n")

        citations_in_unlabeled_outfile.close()




