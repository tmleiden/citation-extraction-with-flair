# Required output format for Flair: tags_*.txt
# Example:
# "The importance of this enzyme is demonstrated by the fact that mice that have both copies of the gene encoding
# dihydrolipoamide dehydrogenase inactivated die prenatally (Johnson <B> et <I> al. <I> (1997) <I> Proc <I> Natl
# <I> Acad <I> Sci <I> USA <I> 94:14512-14517).\n', '\n', 'Genes encoding dihydrolipoamide dehydrogenase have

import re
import os
from collections import defaultdict

flair_output_dir = "data/flair_predicted_out/" # output of Flair for the files in the labeled data.
predicted_bio_dir = "data/crf_predicted_bio_out/" # CRF output, including manual BIO labels (ground truth)


def tokenize(t):
    text = t.lower()
    text = re.sub("\n"," ",text)
    text = re.sub(r'<[^>]+>',"",text) # remove all html markup
    text = re.sub('[^a-zèéeêëėęûüùúūôöòóõœøîïíīįìàáâäæãåçćč&@#A-ZÇĆČÉÈÊËĒĘÛÜÙÚŪÔÖÒÓŒØŌÕÎÏÍĪĮÌ0-9-_ \']', "", text)
    wrds = text.split()
    return wrds

def normalize_text (t):
    #print("*",t)
    t = re.sub(r' ([,.;:)])',r'\1',t)
    t = re.sub('([,.;:)]$)','',t)
    t = re.sub(r'([(]) ',r'\1',t)
    t = re.sub('^[0-9]+\. ','',t)
    t = re.sub('^[\[(]','',t)
    t = re.sub('^ ','',t)
    t = re.sub('[\])]$','',t)
    #print("+",t)
    return t

years = ("1980","1981","1982","1983","1984","1985","1986","1987","1988","1989","1990","1991","1992","1993","1994","1995","1996","1997","1998","1999","2000","2001","2002","2003","2004","2005","2006","2007","2008","2009","2010")

def split_citation(citation):
    years_in_citation = []
    citation_words = tokenize(citation)
    part_citations = []
    for word in citation_words:
        if word in years:
            years_in_citation.append(word)
    if len(years_in_citation) > 1:
        #print ("Possibly concatenated citations!",citation)

        citation = re.sub("; *$", "", citation)
        if re.match(".*[0-9]{4}.*;.*[0-9]{4}.*",citation):
            part_citations = citation.split(";")
            print ("Concatenated citations! Split on ';'",part_citations)

            for part_citation in part_citations:
                part_citation = re.sub("^ ", "", part_citation)
                print("-", part_citation)

    else:
        part_citations.append(citation)

    return part_citations


'''Read Flair output with predicted B and I labels && CRF output with true labels'''

count_correct_per_label = defaultdict(int)
count_per_predicted_label = defaultdict(int)
count_per_true_label = defaultdict(int)
count_citations_manually = 0
count_citations_automatically = 0
contain_true_citation = defaultdict(int) #key is predicted citation; value is number of true citations that are contained in it
part_of_predicted_citation = defaultdict(int) #key is true citation; value is number of predicted citations in which it is contained

for filename in os.listdir(flair_output_dir):
#for filename in ["ent_US7892537B1.txt"]:
#for filename in ["ent_US8273354B2.txt"]:
#for filename in ["tags_US8133710B2.txt"]:
    if "tags_" in filename and not "citations" in filename:
        patent_id = re.sub("tags_", "", filename)
        patent_id = re.sub(".txt", "", patent_id)
        filename_bio = patent_id+".bio.pred"

        print(filename_bio)

        ''' Process BIO file (output of CRF with the true labels) '''

        true_label_sequence = []
        true_word_sequence = []
        true_entities = []
        with open(predicted_bio_dir + "/" + filename_bio, 'r', encoding='utf-8') as predictions_file:
            entity = []
            for line in predictions_file:
                (word, pos, predicted_label_CRF, true_label) = line.rstrip().split('\t')
                true_word_sequence.append(word)
                true_label_sequence.append(true_label)

                if true_label == 'B':
                    if len(entity) > 0:
                        # print("NEXT; SAVE")
                        true_entities.append(normalize_text(" ".join(entity)))
                    entity = [word]
                elif true_label == 'I':
                    entity.append(word)
            if len(entity) > 0:
                #print("LAST; SAVE")
                true_entities.append(normalize_text(" ".join(entity)))

        predictions_file.close()

        count_citations_manually += len(true_entities)


        count_per_true_label['B'] += true_label_sequence.count('B')
        count_per_true_label['I'] += true_label_sequence.count('I')

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



        #count_citations_automatically += len(predicted_entities)

        predicted_entities_after_splitting = []
        for entity in predicted_entities:

            part_citations = split_citation(entity)
            for part_citation in part_citations:
                predicted_entities_after_splitting.append(normalize_text(part_citation))
                print("PREDICTED:", normalize_text(part_citation))

        count_citations_automatically += len(predicted_entities_after_splitting)

        print ("LENGTHS",len(predicted_word_sequence),len(predicted_label_sequence),len(true_word_sequence),len(true_label_sequence))




        ''' Map the Flair output to the CRF/ground truth IOB sequence'''

        #for j in range(0,len(predicted_word_sequence)):

        j=0
        k=0
        while j < len(predicted_word_sequence)-2 and k < len(true_word_sequence)-2:
            #print(predicted_word_sequence[j], predicted_label_sequence[j], true_word_sequence[k],true_label_sequence[k])
            if predicted_label_sequence[j] == true_label_sequence[k] and predicted_label_sequence[j] in ('B','I'):
                count_correct_per_label[predicted_label_sequence[j]] += 1
            #if predicted_word_sequence[j] == true_word_sequence[k]:

            if predicted_word_sequence[j] != true_word_sequence[k]:
                #print("NOT EQUAL; FIX")
                if predicted_word_sequence[j+1] == true_word_sequence[k+2]:
                    k += 1
                elif predicted_word_sequence[j+2] == true_word_sequence[k+1]:
                    k -= 1
            j += 1
            k += 1




        ''' Compare full citations '''


        for true_citation in true_entities:
            for predicted_citation in predicted_entities_after_splitting:
                if true_citation in predicted_citation:
                    contain_true_citation[predicted_citation] += 1
                    part_of_predicted_citation[true_citation] += 1
                    #print("IN:",true_citation,predicted_citation)







no_of_predicted_citations_that_contain_true_citation = len(contain_true_citation)
no_of_true_citations_that_are_in_predicted_citation = len(part_of_predicted_citation)
print()
#for predicted_citation in contain_true_citation:
    #print(contain_true_citation[predicted_citation],"true citations are contained in this predicted citation:",predicted_citation)
print()
#for true_citation in part_of_predicted_citation:
    #print(part_of_predicted_citation[true_citation],"predicted citations contain this true citation:",true_citation)




print("Number of automatically identified citations:\t",count_citations_automatically)
print("Number of manually identified citations:\t",count_citations_manually)

print("Number of automatically identified citations that contain a true citation:",no_of_predicted_citations_that_contain_true_citation)
print("Number of true citations that are part of an automatically identified citation:",no_of_true_citations_that_are_in_predicted_citation)

precision_full = float(no_of_predicted_citations_that_contain_true_citation)/float(count_citations_automatically)
recall_full = float(no_of_true_citations_that_are_in_predicted_citation)/float(count_citations_manually)
print("Precision for complete citations:",precision_full)
print("Recall for complete citations:",recall_full)

print("\nlabel","count_true","count_predicted","count_correct","precision","recall",sep="\t")
for label in count_correct_per_label:
    precision = float(count_correct_per_label[label])/float(count_per_predicted_label[label])
    recall = float(count_correct_per_label[label])/float(count_per_true_label[label])
    print (label,count_per_true_label[label],count_per_predicted_label[label],count_correct_per_label[label],"%.3f"%precision,"%.3f"%recall,sep="\t")

precision = (float(count_correct_per_label['I'])+float(count_correct_per_label['B']))/(float(count_per_predicted_label['I'])+float(count_per_predicted_label['B']))
recall = (float(count_correct_per_label['I'])+float(count_correct_per_label['B']))/(float(count_per_true_label['I'])+float(count_per_true_label['B']))
print('B+I',count_per_true_label['I']+count_per_true_label['B'],count_per_predicted_label['I']+count_per_predicted_label['B'],count_correct_per_label['I']+count_correct_per_label['B'],"%.3f"%precision,"%.3f"%recall,sep="\t")


print()
print(count_per_true_label)
print(count_per_predicted_label)


print("\nlabel","count_true","count_predicted","count_correct","precision","recall",sep="\t")
