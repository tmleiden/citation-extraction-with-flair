from bs4 import BeautifulSoup as BSHTML

import os
import re

html_directory = "data/patent_htmls/"
fp_citations_dir = 'data/fp_citations_from_html'
if not os.path.exists(fp_citations_dir):
    os.makedirs(fp_citations_dir)



citations_per_patent = dict() # key is patent_number; value is array of citation texts
ref_locations_per_patent = dict() # key is patent_number; value is array of reference locations (1 or 2; front page or in-text)


filecount = 0
for filename in os.listdir(html_directory):

    patent_id = re.sub(".html","",filename)

    html_patent_file = open(html_directory + filename, 'r',encoding='utf-8')
    citations_in_unlabeled_outfile = open(fp_citations_dir + "/" + patent_id + ".fpcitations.txt", 'w',encoding='utf-8')
    citations_in_unlabeled_outfile.write("\n\n"+patent_id+"\n\n")

    filecount += 1

    htmlcontent = html_patent_file.read().replace('\n', '')
    htmlstruct = BSHTML(htmlcontent,"lxml")

    patent_citations_in_html = []
    nonpatent_citations_in_html = []


    """
    Find citations in the HTML metadata (front-page citations)
    """

    for meta in htmlstruct.findAll('meta',attrs={"name":"DC.relation"}):
        #print("patent_citation in meta\t",meta['content'])
        patent_citations_in_html.append(meta['content'])
    for meta in htmlstruct.findAll('meta',attrs={"name":"citation_reference"}):
        #print("nonpatent_citation in meta\t",meta['content'])
        nonpatent_citations_in_html.append(meta['content'])



    print (patent_id,
           len(patent_citations_in_html),
           len(nonpatent_citations_in_html),
           sep="\t"
           )


    for citation_text in sorted(nonpatent_citations_in_html):
        citations_in_unlabeled_outfile.write(citation_text+"\n")

    html_patent_file.close()
    citations_in_unlabeled_outfile.close()

print(filecount,"files read")