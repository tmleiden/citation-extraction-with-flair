import re
import os
from collections import defaultdict

predicted_bio_dir = "data/crf_predicted_bio_out"
auto_output_dir = "data/predicted_CRF_citations"

if not os.path.exists(auto_output_dir):
    os.makedirs(auto_output_dir)


manual_outfile = open("data/manually_extracted_citations.txt",'w',encoding='utf-8')

def get_citation_texts(label_sequence,word_sequence):
    citation_sequence = []
    all_citation_texts = []
    for k in range(0,len(word_sequence)):
        if label_sequence[k] in ('B','O'):
            # end of previous citation; save citation text
            if len(citation_sequence) > 2:
                citation_text = ' '.join(citation_sequence)
                all_citation_texts.append(normalize_text(citation_text))
            citation_sequence = []
            if label_sequence[k] == 'B':
                # new citation
                citation_sequence.append(word_sequence[k])
        elif label_sequence[k] == 'I':
            citation_sequence.append(word_sequence[k])
    return all_citation_texts


def normalize_text (t):
    t = re.sub(r' ([,.;:)])',r'\1',t)
    t = re.sub(r'([(]) ',r'\1',t)
    return t




all_filenames_bio = os.listdir(predicted_bio_dir)
#all_filenames.remove('.DS_Store')

count_correct_per_label = dict()
count_per_predicted_label = dict()
count_per_true_label = dict()
count_citations_manually = 0
count_citations_automatically = 0

contain_true_citation = defaultdict(int) #key is predicted citation; value is number of true citations that are contained in it
part_of_predicted_citation = defaultdict(int) #key is true citation; value is number of predicted citations in which it is contained

#true_positives = 0

for filename_bio in all_filenames_bio:

    if "US" in filename_bio:
        found_manually = dict() # for uniqueness
        found_automatically = dict() # for uniqueness
        print(filename_bio)
        patent_id = re.sub('.bio.pred','',filename_bio)

        auto_outfile = open(auto_output_dir+"/" + patent_id + ".citations.txt", 'w', encoding='utf-8')
        auto_outfile.write("\n\n"+patent_id+"\n\n")
        manual_outfile.write("\n\n"+patent_id+"\n\n")
        predicted_label_sequence = []
        true_label_sequence = []
        word_sequence = []
        with open(predicted_bio_dir+"/"+filename_bio,'r',encoding='utf-8') as predictions_file:
            for line in predictions_file:
                (word,pos,predicted_label,true_label) = line.rstrip().split('\t')

                predicted_label_sequence.append(predicted_label)
                true_label_sequence.append(true_label)
                word_sequence.append(word)

                count_for_predicted_label = 0
                if predicted_label in count_per_predicted_label:
                    count_for_predicted_label = count_per_predicted_label[predicted_label]
                count_for_predicted_label += 1
                count_per_predicted_label[predicted_label] = count_for_predicted_label

                count_for_true_label = 0
                if true_label in count_per_true_label:
                    count_for_true_label = count_per_true_label[true_label]
                count_for_true_label += 1
                count_per_true_label[true_label] = count_for_true_label

                if predicted_label == true_label:
                    count_correct_for_label = 0
                    if predicted_label in count_correct_per_label:
                        count_correct_for_label = count_correct_per_label[predicted_label]
                    count_correct_for_label += 1
                    count_correct_per_label[predicted_label] = count_correct_for_label

        predicted_citation_texts = get_citation_texts(predicted_label_sequence,word_sequence)
        true_citation_texts = get_citation_texts(true_label_sequence,word_sequence)

        predictions_file.close()

        for citation_text in sorted(predicted_citation_texts):
            found_automatically[citation_text] = 1


        for citation_text in sorted(found_automatically):
            auto_outfile.write(citation_text+"\n")


        for citation_text in sorted(true_citation_texts):
            found_manually[citation_text] = 1

        for citation_text in sorted(found_manually):
            manual_outfile.write(citation_text+"\n")

        count_citations_automatically += len(found_automatically)
        count_citations_manually += len(found_manually)

        for true_citation in found_manually:
            for predicted_citation in found_automatically:
                if true_citation in predicted_citation:
                    contain_true_citation[predicted_citation] += 1
                    part_of_predicted_citation[true_citation] += 1


manual_outfile.close()

print("Number of automatically identified citations:\t",count_citations_automatically)
print("Number of manually identified citations:\t",count_citations_manually)
#print("Found by both:\t",true_positives)

no_of_predicted_citations_that_contain_true_citation = len(contain_true_citation)
no_of_true_citations_that_are_in_predicted_citation = len(part_of_predicted_citation)

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

