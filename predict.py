import os
from flair.data import Sentence
from flair.models import SequenceTagger
from tqdm import tqdm

model = SequenceTagger.load('/resources/taggers/model/best-model.pt')
data_folder = '/patent_data/full_text'
output_folder = '/patent_output/'

import torch,flair


device = None
if torch.cuda.is_available():
    device = torch.device('cuda:0')
else:
    device = torch.device('cpu')

print("Device:",device)
print("GPU count:",torch.cuda.device_count())

flair.device = device


all_filenames = os.listdir(data_folder)


for filename in tqdm(all_filenames):
    if '.txt' in filename:
    print(filename)
            start = time.time()
            entities = []
            tagged_string = []
            with open(data_folder+"/"+filename,'r',encoding='utf-8') as full_patent:
                for line in full_patent:

                    sentence = Sentence(line)
                    model.predict(sentence)
                    tagged_string.append(sentence.to_tagged_string())



        f = open(output_folder+"/tags_"+filename,'w+',encoding='utf-8')
        f.write(str(tagged_string))
        f.close()

                                                                                                                                        64,0-1        Bot
