
from flair.data_fetcher import  NLPTaskDataFetcher, NLPTask
from flair.embeddings import TokenEmbeddings, WordEmbeddings, StackedEmbeddings, PooledFlairEmbeddings, FlairEmbeddings
from typing import List

import torch,flair


data_folder = '/home/s2149133/research/patent_data/final_splits'


columns = {0: 'text', 1: 'pos', 2: 'ner'}


from flair.data import Corpus
from flair.datasets import ColumnCorpus


corpus: Corpus = ColumnCorpus(data_folder, columns,
                              train_file='train',
                              test_file='test',
                              dev_file='dev')



# 2. what tag do we want to predict?
tag_type = 'ner'



# 3. make the tag dictionary from the corpus
tag_dictionary = corpus.make_tag_dictionary(tag_type=tag_type)


domain_embeddings_forward = FlairEmbeddings('/LMs/resources/taggers/language_model/best-lm.pt')
domain_embeddings_backward = FlairEmbeddings('/LMs/resources/taggers/language_model/best-lm.pt')




embedding_types: List[TokenEmbeddings] = [
    # GloVe embeddings
    WordEmbeddings('glove') ,
    # contextual string embeddings, forward
    FlairEmbeddings('news-forward'),
    # contextual string embeddings, backward
    FlairEmbeddings('news-backward'),
    domain_embeddings_forward,
    domain_embeddings_backward
]

embeddings: StackedEmbeddings = StackedEmbeddings(embeddings=embedding_types)

# initialize sequence tagger
from flair.models import SequenceTagger

tagger: SequenceTagger = SequenceTagger(hidden_size=256,
                                        embeddings=embeddings,
                                        tag_dictionary=tag_dictionary,
                                        tag_type=tag_type)

# initialize trainer
from flair.trainers import ModelTrainer

trainer: ModelTrainer = ModelTrainer(tagger, corpus)

trainer.train('resources/taggers/patents_domain_embs_small',checkpoint=True,
embeddings_in_memory=True,max_epochs=100)
