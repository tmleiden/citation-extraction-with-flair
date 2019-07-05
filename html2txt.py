import os
import re
from bs4 import BeautifulSoup as BSHTML
from bs4.element import Comment
from nltk import sent_tokenize
import datetime

start = datetime.datetime.now()


html_directory = "data/patent_htmls/"
text_out_directory = re.sub("patent_htmls","plain_text",html_directory)
if not os.path.exists(text_out_directory):
    os.makedirs(text_out_directory)

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

filecount = 0
for filename in os.listdir(html_directory):
    if "US" in filename:
        fileStem = re.sub('\.html','',filename)
        #out_folia_file = folia_out_directory+"/"+fileStem+".folia.xml"
        out_text_file = text_out_directory+"/"+fileStem+".txt"
        file = open(html_directory+filename,'r',encoding='utf-8')

        patent_number = re.sub("US","",filename)
        patent_number = re.sub(".html","",patent_number)

        filecount += 1
        print(filecount,filename)

        """
        Parse the HTML structure and split the text in paragraphs
        """
        htmlcontent = file.read().replace('\n', '')
        htmlcontent = re.sub('</?i>','',htmlcontent)
        htmlstruct = BSHTML(htmlcontent,"lxml")


        paragraphs = []
        for cell in htmlstruct.findAll(['p', 'h1', 'h2', 'h3', 'heading']):
            #print (cell)
            visible_texts = filter(tag_visible, cell)
            paragraph = ""
            for t in visible_texts:
                if t.string is not None:
                    paragraph += t.string

            paragraphs.append(paragraph)


        out_text = open(out_text_file,'wb')
        pi = 1
        for p in paragraphs:

            ''' sentence splitting with nltk '''
            sentences = sent_tokenize(p,'english')
            for sent in sentences:
                out_text.write(sent.encode('UTF-8')+"\n\n".encode('UTF-8'))


            pi += 1

        out_text.close()

end = datetime.datetime.now()

print(end-start)
