import os
import csv
import re
import jellyfish
from collections import defaultdict


intext_citations_dir = "data/found_citations_in_unlabeled_Flair"

duplicatesfilepath = "data/Flair_duplicates_with_fp.txt"

fp_citations_dir = "data/fp_citations_in_unlabeled"
if not os.path.exists(fp_citations_dir):
    os.makedirs(fp_citations_dir)

statsfile_path = "matching.stats.Flair"
matches_filepath = "all.matches.Flair.out"
nonmatches_filepath = "all.non-matches.Flair.out"


"""

TODO    
- search in year +- 1
+ get definite answer for 'not in database' (no pub by author in journal in year)
+ journal_id can be UNK
+ find the extracted citations that could be parsed but cannot be matched. Missing in the database?

"""


page_number_pattern = re.compile("^[^-]*([0-9]+-[0-9]+)[^-]$")
year_pattern = re.compile("[21][90][8901][0-9]")
years = ("1980","1981","1982","1983","1984","1985","1986","1987","1988","1989","1990","1991","1992","1993","1994","1995","1996","1997","1998","1999","2000","2001","2002","2003","2004","2005","2006","2007","2008","2009","2010")
#years = ["2001"]


local_dir_to_npr_pub = "/Users/suzanverberne/Data/Leiden_Data_Science/Patent_citations/NPR_PUB/"

dir_to_npr_pub = "../NPR_PUB/"
if os.path.isdir(local_dir_to_npr_pub):
    dir_to_npr_pub = local_dir_to_npr_pub


'''Global variables '''

all_citations = list()
citation_ids_per_patent = dict() # dictionary of arrays. key is patent name (e.g. US8227661B2); value is array of line numbers
citation_id_to_citation = dict() # line number -> full extraction citation
citation_id_to_patent = dict()


def tokenize(t):
    text = t.lower()
    text = re.sub("\n"," ",text)
    text = re.sub(r'<[^>]+>',"",text) # remove all html markup
    text = re.sub('[^a-zèéeêëėęûüùúūôöòóõœøîïíīįìàáâäæãåçćč&@#A-ZÇĆČÉÈÊËĒĘÛÜÙÚŪÔÖÒÓŒØŌÕÎÏÍĪĮÌ0-9-_ \']', "", text)
    wrds = text.split()
    return wrds




''' READ JOURNAL DATABASE '''

print ("Read journal database")

journal_names = dict()

journal_abbr_isos = dict()
journal_abbr_11s = dict()
journal_abbr_20s = dict()
journal_abbr_29s = dict()
journal_simplified = dict()

journal_simplified_to_jnl_no = dict()
jnl_title_to_jnl_no = dict()


journal_file = dir_to_npr_pub+"NPR_JNL.csv"



with open(journal_file, 'rt',encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=';', quotechar='"')
    for line in reader:
        if len(line) == 7:
            (jnl_no,jnl_title,abbr_iso,abbr_11,abbr_20,abbr_29,issn) = line
            journal_names[jnl_no] = jnl_title
            journal_abbr_isos[jnl_no] = abbr_iso.strip()
            journal_abbr_11s[jnl_no] = abbr_11.strip()
            journal_abbr_20s[jnl_no] = abbr_20.strip()
            journal_abbr_29s[jnl_no] = abbr_29.strip()

            # Proc. Natl. Acad. Sci. U. S. A.;
            iso_simplified = re.sub("\W","",abbr_iso.lower())
            title_simplified = re.sub("\W","",jnl_title.lower())
            journal_simplified[jnl_no] = iso_simplified
            #print (jnl_no,abbr_iso,"\t\t\t",iso_simplified)
            journal_simplified_to_jnl_no[iso_simplified] = jnl_no
            jnl_title_to_jnl_no[title_simplified] = jnl_no
            #print(jnl_no,iso_simplified)

csvfile.close()
#quit()

''' FUNCTIONS FOR PARSING AND NORMALISATION'''

def normalize_page_numbers (pp):
    page_numbers = re.sub("[;,.)]+.*$", "", pp)

    if "-" in page_numbers:
        #print (page_numbers)
        parts = page_numbers.split("-")
        begin = parts[0]
        end = parts[1]
        if len(end) < len(begin):  # 450-9
            p = len(begin) - len(end)
            end = begin[0:p] + end
            page_numbers = begin + "-" + end
            #print("PP:", pp, "->", page_numbers)

    return page_numbers

def normalize_text (t):
    # needed because NLTK adds whitespacing around punctuation
    t = re.sub(r' ([,.;:)])',r'\1',t)
    t = re.sub(r'([(]) ',r'\1',t)
    return t



def parse_citation_text(citation,citation_id,year):
    #print (citation)
    citation = re.sub("^ +", "", citation)
    citation = re.sub("^\(","",citation)
    citation = re.sub("\)$","",citation)
    citation = re.sub("—","-",citation)
    citation = re.sub("^see ","",citation.lower())


    words = citation.split(" ")
    #print (words)
    print(citation_id, citation_id_to_citation[citation_id].encode('utf-8'))

    '''Parse the citation text'''
    if len(words) < 3:
        print ("Too short to be a citation:",citation.encode('utf-8'))
        return None,None,None,None,None,None,None
    elif words[0] in ("database","clone","epo","database-genbank","european","genbank","jpo","ncbi","office","pct","search","u.s.","uspto-u.s.") or "wipo" in words[0]:
        print("Not a reference to a scientific article:", citation.encode('utf-8'))
        return "Non-science",None,None,None,None,None,None

    elif words[1] not in ("et","and","&") and not re.match("[a-z]\.",words[1]) and not re.match("\([0-9][0-9][0-9][0-9]\)",words[1]) \
        and not re.match("^[a-z'-]+,$",words[0]):
        print("Citation cannot be parsed1:",citation.encode('utf-8'))
        return None,None,None,None,None,None,None
    else:
        first_author = words[0].lower()
        first_author = re.sub(",$", "", first_author)
        first_author = re.sub("\'s$", "", first_author)
        second_author = "UNK"
        journal_id = "UNK"
        issue = "UNK"
        page_numbers = "UNK"
        citation_has_et_al = False # boolean that indicates that the phrase 'et al' was found (indicates > 2 authors)

        '''Try to find: first author, second author, year, journal title, volume/issue, and page number'''
        author_end = None
        #print("2nd word:",words[1])
        if re.match(".*"+year+".*",words[1]):
            author_end = 2
            #print("YEAR in pos 2:",words)
            # ['belousov', '(1997)', 'nucleic', 'acids', 'res.', '25:3440-3444']
        elif re.match("[a-z]\.;",words[1]):
            # Zheng, F.; Yang, W.; Ko, M.-C.; Liu, J.; Cho, H.; Gao, D.; Tong, M.; Tai, H.-H.; Woods, J. H.; Zhan, C.-G. “Most Efficient Cocaine Hydrolase Designed by Virtual Screening of Transition States”, J. Am. Chem. Soc. 2008, 130,
            second_author = words[2]
            #print("2nd author:",second_author)
        for i in range(1, len(words)):
            if words[i - 1] == "et" and re.match("^al.*", words[i]):
                author_end = i + 1
                citation_has_et_al = True
                break
            elif words[i-1] in ("and","&"):
                author_end = i + 1
                second_author = words[i].lower()
                second_author = re.sub(",$", "", second_author)
                second_author = re.sub("\'s$", "", second_author)

        #non_author_words = []
        if author_end is not None:
            #author_et_al_words = words[:author_end]
            non_author_words = words[author_end:]
            #print("AUTHOR:", author_et_al_words, "REST:", non_author_words)
        else:
            #author_name = words[0]
            if len(words) > 1:
                m=1

                while m < len(words)-1 and re.match("[a-z]\.",words[m]):
                    m += 1
                author_end = m
            else:
                author_end = 0

            #author_words = words[:author_end]
            non_author_words = words[author_end:]
            #print("SINGLE AUTHOR:", author_words, "REST:", non_author_words)

        j = 0
        positions_to_remove = []
        for word in non_author_words:
            if page_number_pattern.match(word):
                if ":" in word:
                    #print("::::",word)

                    parts = word.split(":")
                    if len(parts) == 2:
                        (issue,pp) = parts
                        page_numbers = normalize_page_numbers(pp)
                        #print("ISSUE1:", word)
                        #print("PP1:",page_numbers)
                        positions_to_remove.append(j)
                    else:
                        page_numbers = normalize_page_numbers(word)
                        #print("PP2:", page_numbers)
                else:
                    page_numbers = normalize_page_numbers(word)
                    #print("PP3:",page_numbers)

                    positions_to_remove.append(j)
            elif re.match(".*"+year+".*",word):
                #print("YEAR:",word)
                positions_to_remove.append(j)
            elif re.match(".*[0-9]+.*",word):

                if ":" in word:
                    parts = word.split(":")
                    if len(parts) == 2:
                        (issue,pp) = parts
                        page_numbers = normalize_page_numbers(pp)
                        #print("ISSUE2:", issue)
                        #print("PP4:",page_numbers)
                    else:
                        page_numbers = normalize_page_numbers(word)
                        #print("PP5:", page_numbers)
                elif issue == "UNK":
                    # if issue was not identified in one of the previous words, then label the remaining number as issue
                    issue = word
                    #print("ISSUE3:",word)
                    issue = re.sub("[;,.].*$", "", issue)
                positions_to_remove.append(j)
            j += 1
        #print("REMOVE:",positions_to_remove)
        remaining_words = list()
        for k in range(0,len(non_author_words)):
            if k not in positions_to_remove:
                remaining_words.append(non_author_words[k])



        remaining_words_simplified = re.sub("\W", "", "".join(remaining_words).lower())
        ''' Try to match the string of the journal title to the journal data base '''
        #print("REMAINING:", remaining_words,remaining_words_simplified)

        if len(remaining_words_simplified) > 2 and remaining_words_simplified in journal_simplified_to_jnl_no:
            #print("MATCH JOURNAL1:",remaining_words_simplified,journal_simplified_to_jnl_no[remaining_words_simplified])
            journal_id = journal_simplified_to_jnl_no[remaining_words_simplified]
        elif len(remaining_words_simplified) > 2 and remaining_words_simplified in jnl_title_to_jnl_no:
            #print("MATCH JOURNAL2:",remaining_words_simplified,jnl_title_to_jnl_no[remaining_words_simplified])
            journal_id = jnl_title_to_jnl_no[remaining_words_simplified]
            ''' If the string can be matched, extract the journal_id (for lookup in the publication data base)
            If not, the function returns UNK for the journal id '''

        print(citation_id,first_author.encode('utf8'), second_author.encode('utf8'),year, journal_id, issue.encode('utf8'), page_numbers.encode('utf8'),sep="\t")

        return first_author, second_author, citation_has_et_al, year, journal_id, issue, page_numbers

"""
MAIN
"""

'''READ FRONT-PAGE CITATIONS'''
print("Read front-page citations")
fp_citations_per_patent = defaultdict(list)
fp_citation_id_to_citation_words = dict()
count_fp = 0
patent_name = ""
line_nr = 0
fp_citations_files = os.listdir(fp_citations_dir)
no_of_files_read =0
for fp_citations_file in fp_citations_files:
    patent_name = re.sub(".fpcitations.txt", "", fp_citations_file)
    no_of_files_read += 1
    if no_of_files_read%1000==0:
        print("-",no_of_files_read,"files read")
    with open(fp_citations_dir+"/"+fp_citations_file,'rt',encoding='utf-8') as fp_citations:
        for line in fp_citations.readlines():

            if re.match('^US[0-9A-Za-z.]+$',line):

                #print ("-",patent_name,line.rstrip())
                found_patent_name = True

            elif len(line) > 3:
                line_nr += 1
                count_fp += 1
                citation = line.rstrip()
                citation_id = str(line_nr)
                citation_words = tokenize(citation.lower())

                (fp_citations_per_patent[patent_name]).append(citation_id)
                fp_citation_id_to_citation_words[citation_id] = citation_words

    fp_citations.close()


'''READ EXTRACTED IN-TEXT CITATIONS'''

statsfile = open(statsfile_path,'w',encoding='utf-8')

print ("Read extracted in-text citations")
count_total = 0
patent_name = ""
line_nr = 0
no_of_patent_files_read = 0
no_of_skipped_patents = 0
intext_citations_filenames = os.listdir(intext_citations_dir)
for intext_citations_file in intext_citations_filenames:
    if no_of_patent_files_read%1000==0:
        print("-",no_of_patent_files_read,"files read")
    if re.match("^US.*",intext_citations_file):
        #print(intext_citations_file)
        no_of_patent_files_read += 1

        patent_name = re.sub(".citations.txt", "", intext_citations_file)
        if patent_name not in fp_citations_per_patent:
            print("WARNING: patent", patent_name, "not in the collection of front-page citations. SKIP patent")
            no_of_skipped_patents += 1
            continue
        with open(intext_citations_dir+"/"+intext_citations_file,'rt',encoding='utf-8') as citations:
            count_this_patent = 0
            for line in citations.readlines():
                if re.match('^US[0-9A-Za-z.]+$',line):

                    #print ("-",patent_name,line.rstrip())
                    found_patent_name = True

                elif len(line) > 3:
                    count_this_patent += 1
                    line_nr += 1
                    count_total += 1
                    citation = line.rstrip()
                    citation_id = str(line_nr)
                    citation_id_to_patent[citation_id] = patent_name
                    citation = normalize_text(citation)
                    # needed because NLTK adds whitespaces (this was done in eval_and_convert.py, but not in
                    # crfsuite_to_unlabeled_texts.py)
                    citation_words = tokenize(citation)

                    years_in_citation = []
                    for word in citation_words:
                        if word in years:
                            years_in_citation.append(word)
                    if len(years_in_citation) > 1:
                        #print ("Possibly concatenated citations!",citation)

                        citation = re.sub("; *$","",citation)
                        part_citations = []
                        if re.match(".*[0-9]{4}.*;.*[0-9]{4}.*", citation):
                            part_citations = citation.split(";")
                            #print ("Concatenated citations! Split on ';'",part_citations)
                            sub_id = 0
                            for part_citation in part_citations:
                                part_citation = re.sub("^ ","",part_citation)
                                sub_id += 1
                                part_citation_id = citation_id + "_" +str(sub_id)
                                print(part_citation_id, part_citation.encode('utf-8'))
                                citation_id_to_citation[part_citation_id] = part_citation
                                citation_id_to_patent[part_citation_id] = patent_name
                                all_citations.append(part_citation_id)

                        else:
                            #keep line as one citation even though it has multiple years
                            all_citations.append(citation_id)
                            #print(citation_id, citation)
                            citation_id_to_citation[citation_id] = citation
                    else:
                        all_citations.append(citation_id)
                        #print(citation_id, citation)
                        citation_id_to_citation[citation_id] = citation

            statsfile.write(patent_name+"\t"+str(count_this_patent)+"\n")
        citations.close()

''' ANALYZE ALL EXTRACTED CITATIONS '''


count_total_matched = 0
count_strong_match = 0
count_weak_match = 0
count_ambiguous = 0
count_cannot_be_parsed = 0
count_no_science = 0
count_journal_id_not_extracted = 0
count_no_year_in_citation = 0

citations_in_focus_years = defaultdict(list)
extracted_citations_per_author_per_year = dict() # only used for the citations from which the journal could not be deduced
extracted_citations_per_jnl_per_year = dict()
number_of_fields_extracted_per_citation = dict()
citation_ids_per_number_of_fields = defaultdict(list)

reason_for_no_match = dict()

#unique_count_in_years = 0

all_fields_for_extracted_citation = dict() # key is citation_id (line nr in list of citations file); value is tuple (first_author, year, journal_id, issue, page_numbers)

for citation_id in all_citations:
    citation = citation_id_to_citation[citation_id]
    #print(">",citation_id, citation)
    citation_words = tokenize(citation)
    citation_in_focus_years = False
    for year in years:

        ''' Check if the citation comes from the focus years '''
        if year in citation_words:

            (citations_in_focus_years[citation_id]).append(year)
            #print("in year:",year)
            citation_in_focus_years = True



            ''' Parse the citation '''
            #print("Parse",citation)
            first_author, second_author, citation_has_et_al, year, journal_id, issue, page_numbers = parse_citation_text(citation,citation_id,year)
            if first_author == "Non-science":
                #print("Citation is not scientific literature:", citation)
                count_no_science += 1
                del citations_in_focus_years[citation_id]
                #reason_for_no_match[citation_id] = "No scientific literature reference"

            elif first_author is None:
                print("Citation cannot be parsed2:", citation.encode('utf8'))
                count_cannot_be_parsed += 1
                reason_for_no_match[citation_id] = "Extracted citation cannot be parsed\t(perhaps wrongly extracted)"


            else:
                # count number of UNKs:
                number_of_fields_extracted = 5-(first_author, year, journal_id, issue, page_numbers).count("UNK")
                number_of_fields_extracted_per_citation[citation_id] = number_of_fields_extracted
                print(number_of_fields_extracted, "fields extracted")
                (citation_ids_per_number_of_fields[number_of_fields_extracted]).append(citation_id)

                all_fields_for_extracted_citation[citation_id] = [first_author, second_author,citation_has_et_al,year, journal_id, issue, page_numbers]

                extracted_citations_per_author = dict()
                extracted_citations_per_jnl = dict()
                if year in extracted_citations_per_jnl_per_year:
                    extracted_citations_per_jnl = extracted_citations_per_jnl_per_year[year]

                if year in extracted_citations_per_author_per_year:
                    extracted_citations_per_author = extracted_citations_per_author_per_year[year]

                citations_for_jnl_for_year = []
                if journal_id in extracted_citations_per_jnl:
                    citations_for_jnl_for_year = extracted_citations_per_jnl[journal_id]

                # citations per author only used for the citations from which the journal id could not be extracted'
                citations_for_author_for_year = []
                if first_author in extracted_citations_per_author:
                    citations_for_author_for_year = extracted_citations_per_author[first_author]

                if journal_id != "UNK":
                    ''' For all citations from which the journal id could be deduced, store the citation per journal id '''

                    citations_for_jnl_for_year.append(citation_id)
                    extracted_citations_per_jnl[journal_id] = citations_for_jnl_for_year
                    extracted_citations_per_jnl_per_year[year] = extracted_citations_per_jnl
                else:
                    ''' For all citations from which the journal id could not be deduced, store the citation per author '''
                    print("Journal ID cannot be extracted, index by author:", " ".join(citation_words).encode('utf-8'))
                    count_journal_id_not_extracted += 1
                    citations_for_author_for_year.append(citation_id)
                    extracted_citations_per_author[first_author] = citations_for_author_for_year
                    extracted_citations_per_author_per_year[year] = extracted_citations_per_author



            break # do not look for other years in the same citation

    if not citation_in_focus_years:
        any_year_in_citation = False
        for word in citation_words:
            if year_pattern.match(word):
                any_year_in_citation = True

        if not any_year_in_citation:
            #print ("No year in citation:",citation_id," ".join(citation_words).encode('utf-8'))
            count_no_year_in_citation += 1




#print("\nyear\tjnl_no\tcitations")
#for year in extracted_citations_per_jnl_per_year:
#    extracted_citations_per_jnl = extracted_citations_per_jnl_per_year[year]
#    for jnl_no in extracted_citations_per_jnl:
#        print (year,jnl_no,extracted_citations_per_jnl[jnl_no],sep="\t")

statsfile.write("\n\nNumber of patent files in collection:\t"+str(no_of_patent_files_read)+"\n")
statsfile.write("- Files skipped (no fp citations):\t"+str(no_of_skipped_patents)+"\n")

print("\nNumber of patent files in collection:",no_of_patent_files_read,sep="\t")
print("-Files skipped because of incomplete data:",no_of_skipped_patents,sep="\t")

statsfile.write("\nTotal number of fp citations:\t"+str(len(fp_citation_id_to_citation_words))+"\n")
statsfile.write("\nTotal number of extracted citations:\t"+str(count_total)+"\n")
statsfile.write("Not a scientific reference:\t"+str(count_no_science)+"\t(these are not counted)"+"\n")
statsfile.write("No year in citation:\t"+str(count_no_year_in_citation)+"\t(these are not counted)"+"\n")
statsfile.write("Number of extracted citations to scientific papers in focus years:\t"+str(len(citations_in_focus_years))+"\n")

print ("\nTotal number of fp citations:",len(fp_citation_id_to_citation_words),sep="\t")
print ("\nTotal number of extracted citations:",count_total,sep="\t")
print ("Not a scientific reference",count_no_science,"(these are not counted)",sep="\t")
print ("No year in citation:",count_no_year_in_citation,"(these are not counted)",sep="\t")
print ("Number of extracted citations to scientific papers in focus years:",len(citations_in_focus_years),sep="\t")

statsfile.write("\n\tNumber of fields extracted\tNumber of citations\n")
print ("\n\tNumber of fields extracted\tNumber of citations")
sum_parsing_result = 0
for number_of_fields_extracted in sorted(citation_ids_per_number_of_fields):
    count = len(citation_ids_per_number_of_fields[number_of_fields_extracted])
    print("\t",number_of_fields_extracted,"\t",count)
    statsfile.write("\t"+str(number_of_fields_extracted)+"\t"+str(count)+"\n")
    sum_parsing_result += count
#print ("number of unique citations from years 1980-2010:",unique_count_in_years,sep="\t")

statsfile.write("Cannot be parsed:\t"+str(count_cannot_be_parsed)+"\n")
statsfile.write("Can be parsed:\t"+str(sum_parsing_result)+"\n")

print ("Cannot be parsed:",count_cannot_be_parsed,sep="\t")
print ("Can be parsed:",sum_parsing_result,sep="\t")


#print ("\nJournal ID not found (indexed by author name):",count_journal_id_not_extracted,sep="\t")


number_of_citations_with_at_least_one_match = 0
count_no_potential_matches = 0

final_matches = defaultdict(str)

pubid_to_pub_record = dict()


''' MATCHING '''
#for year in sorted(extracted_citations_per_author_per_year):
for year in years:

    ''' 1. Per year, read the publication data base '''
    pubbase_filename = dir_to_npr_pub+"NPR_PUB" + year + ".csv"
    print("\nread", pubbase_filename)
    extracted_citations_per_author = dict()
    extracted_citations_per_jnl = dict()
    if year in extracted_citations_per_author_per_year:
        extracted_citations_per_author = extracted_citations_per_author_per_year[year]
    if year in extracted_citations_per_jnl_per_year:
        extracted_citations_per_jnl = extracted_citations_per_jnl_per_year[year]
    matches_per_extracted_citation = defaultdict(defaultdict) # key is citation_id, value is dict with key pub_id, value integer for the number of matching fields

    #match_scores = defaultdict(int) # key is tuble (citation_id, pub_id), value is integer for the number of matching fields

    lines_csv = []
    with open(pubbase_filename, 'rt',encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar='"')
        for line in reader:
            if len(line) == 8:

                lines_csv.append(line)
    csvfile.close()

    for line in lines_csv:
        ''' 2. Get each publication record from the csv '''
        (pub_id, pub_author_first, author_et_al, title, jnl_no, volume, issue, pages) = line


        #print("-",line)
        pub_author_first = pub_author_first.lower()
        pub_author_first = re.sub(", .*", "", pub_author_first)
        author_et_al = author_et_al.lower()
        more_than_two_authors_in_pub = False
        if ";" in author_et_al:
            more_than_two_authors_in_pub = True
            #print("More than two authors:",author_et_al,line)
        second_author = re.sub(", .*", "", author_et_al)
        #print("2nd author:",second_author,line)

        extracted_citations_for_jnl_this_year = list()
        if jnl_no in extracted_citations_per_jnl:
            ''' 3a. Find the citations that have the journal id of the current publication'''
            extracted_citations_for_jnl_this_year = extracted_citations_per_jnl[jnl_no]

        extracted_citations_for_author_this_year = list()
        if pub_author_first in extracted_citations_per_author:
            ''' 3b. Find the citations that have the author of the current publication'''
            extracted_citations_for_author_this_year = extracted_citations_per_author[pub_author_first]
            #print(">>>", pub_author_first, extracted_citations_for_author_this_year)


        extracted_citations_with_possible_match = list()  # extracted_citations_that_have_author_or_jnl_in_pub_this_year
        for citation_id in extracted_citations_for_author_this_year:
            extracted_citations_with_possible_match.append(citation_id)
        for citation_id in extracted_citations_for_jnl_this_year:
            extracted_citations_with_possible_match.append(citation_id)


        for citation_id in extracted_citations_with_possible_match:
            ''' 4. For each of the citations to this journal, count the number of additional matching fields with the current publication '''
            ''' The maximum number of matched fields is 6: year, journal, pages, issue/volume, first author, second author'''
            extracted_citation_fields = all_fields_for_extracted_citation[citation_id]
            #print("* citation for journal",jnl_no,"for",year,":",extracted_citation_fields)
            (author_extracted, second_author_extracted, citation_has_et_al, year, journal_id, issue_extracted, pages_extracted) = extracted_citation_fields

            if citation_id not in matches_per_extracted_citation:
                matches_per_extracted_citation[citation_id] = defaultdict(int)
            if pub_id not in (matches_per_extracted_citation[citation_id]):
                (matches_per_extracted_citation[citation_id])[pub_id] = 2 # because the year and the journal/author match
                pubid_to_pub_record[pub_id] = line
            if pages_extracted == pages:
                #print("^PAGES",citation_id,extracted_citation_fields,line)
                if citation_id not in matches_per_extracted_citation:
                    matches_per_extracted_citation[citation_id] = defaultdict(int)

                (matches_per_extracted_citation[citation_id])[pub_id] += 2
            if issue_extracted == issue or issue_extracted == volume:
                #print("^ISSUE/VOLUME",citation_id,extracted_citation_fields,line)

                if citation_id not in matches_per_extracted_citation:
                    matches_per_extracted_citation[citation_id] = defaultdict(int)

                (matches_per_extracted_citation[citation_id])[pub_id] += 1
            if second_author_extracted in author_et_al:
                #print("^2ND AUTHOR",citation_id, extracted_citation_fields, line)
                if citation_id not in matches_per_extracted_citation:
                    matches_per_extracted_citation[citation_id] = defaultdict(int)

                (matches_per_extracted_citation[citation_id])[pub_id] += 1
            if more_than_two_authors_in_pub and citation_has_et_al:
                #print("^more than two authors", citation_id, extracted_citation_fields, line)
                (matches_per_extracted_citation[citation_id])[pub_id] += 1
            if citation_id not in extracted_citations_for_author_this_year:
                # do not count the author field as additional match if the citation was found based on author match
                if author_extracted == pub_author_first:

                    #print("^1ST AUTHOR",citation_id, extracted_citation_fields, line)
                    if citation_id not in matches_per_extracted_citation:
                        matches_per_extracted_citation[citation_id] = defaultdict(int)

                    (matches_per_extracted_citation[citation_id])[pub_id] += 1.5

                else:
                    author_levenshtein_distance = jellyfish.levenshtein_distance(author_extracted, pub_author_first)
                    if author_levenshtein_distance < 2 and len(author_extracted) > 6:
                        ''' The first author can also be a fuzzy match with an edit distance of 1'''

                        #print("^AUTHORSIM", extracted_citation_fields, line)
                        if citation_id not in matches_per_extracted_citation:
                            matches_per_extracted_citation[citation_id] = defaultdict(int)

                        (matches_per_extracted_citation[citation_id])[pub_id] += 0.5
                    elif author_extracted in author_et_al:
                        #print("^AUTHOR ET AL", citation_id, extracted_citation_fields, line)
                        # the first author in the citation is the non-first author in the database
                        if citation_id not in matches_per_extracted_citation:
                            matches_per_extracted_citation[citation_id] = defaultdict(int)

                        (matches_per_extracted_citation[citation_id])[pub_id] += 0.5

    #csvfile.close()
    print("\n",year)

    number_of_citations_with_at_least_one_match += len(matches_per_extracted_citation)


    for jnl_no in extracted_citations_per_jnl:
        for citation_id in (extracted_citations_per_jnl[jnl_no]):
            if citation_id not in matches_per_extracted_citation:
                print(citation_id, citation_id_to_citation[citation_id].encode('utf-8'), sep="\t")
                print("NOT FOUND IN DATABASE (no publications in this journal in this year)",jnl_no, sep="\t")
                count_no_potential_matches += 1
                reason_for_no_match[citation_id] = "Publication cannot be found in the publication database\t(no publications in this journal in this year)"
            #else:
            #    print("POTENTIAL MATCHES by JOURNAL", citation_id, citation_id_to_citation[citation_id])


    for author_extracted in extracted_citations_per_author:
        for citation_id in (extracted_citations_per_author[author_extracted]):
            if citation_id not in matches_per_extracted_citation:
                print(citation_id, citation_id_to_citation[citation_id].encode('utf-8'), sep="\t")
                print("NOT FOUND IN DATABASE (no publications by this author in this year)",author_extracted.encode('utf-8'), sep="\t")
                count_no_potential_matches += 1
                reason_for_no_match[
                    citation_id] = "Publication cannot be found in the publication database\t(no publications by this author in this year)"
            #else:
            #    print ("POTENTIAL MATCHES by AUTHOR",citation_id,citation_id_to_citation[citation_id])



    min_strong_match_score = 4
    for citation_id in matches_per_extracted_citation:
        ''' 5. For each citation id that was matched to at least one publication record,
             get all the matched publications and find the best match.'''
        # the journal id and year is always a match. A match score of 1 means that one additional fields matches
        extracted_citation_fields = all_fields_for_extracted_citation[citation_id]
        extracted_page_number = extracted_citation_fields[-1]



        print(citation_id,citation_id_to_citation[citation_id].encode('utf-8'),sep="\t")
        if len(matches_per_extracted_citation[citation_id]) == 1:
            ''' 6a. if there is exactly one potential match then store this publication'''
            for pub_id in (matches_per_extracted_citation[citation_id]):
                match_score = (matches_per_extracted_citation[citation_id])[pub_id]
                print("MATCH1", match_score, pub_id, pubid_to_pub_record[pub_id], sep="\t")
                final_matches[citation_id] = pub_id
                count_total_matched += 1
                if match_score >= min_strong_match_score:
                    ''' if at least 4 fields match then it is a strong match'''
                    count_strong_match += 1
                else:
                    ''' if fewer field s match then it is a weak match'''
                    count_weak_match += 1

        elif len(matches_per_extracted_citation[citation_id]) > 1:
            ''' 6b. if there is more than one potential match, find the publication with the highest number of matching fields'''

            pubs_per_match_score = defaultdict(list)
            highest_match_score = 0
            for pub_id in (matches_per_extracted_citation[citation_id]):
                match_score = (matches_per_extracted_citation[citation_id])[pub_id]
                (pubs_per_match_score[match_score]).append(pub_id)
                if match_score >= highest_match_score:
                    highest_match_score = match_score

            if len((pubs_per_match_score[highest_match_score])) > 1:
                ''' if there are multiple publications with the highest number of matching fields, it is an ambiguous match'''
                page_number_disambiguates = False
                if extracted_page_number != "UNK":
                    ''' if the extracted citation has a page number; use this for disambiguation (exact match)'''
                    #print ("Extracted citation has page number; use for disambiguation:",extracted_page_number)
                    for pub_id in (pubs_per_match_score[highest_match_score]):
                        pub_record = pubid_to_pub_record[pub_id]
                        pub_page_number = pub_record[-1]
                        if not "-" in extracted_page_number:
                            # e.g. Carter et al., Proc. Natl. Acad. Sci. USA, 89:4285 (1992)
                            pub_page_number = re.sub("-.*","",pub_page_number) # only check beginning page no
                        #print(pub_page_number)
                        if extracted_page_number == pub_page_number:
                            print("MATCH3 (page number disambiguation):", highest_match_score, pub_id, pubid_to_pub_record[pub_id], sep="\t")
                            page_number_disambiguates = True
                            final_matches[citation_id] = pub_id
                            count_total_matched += 1

                    if not page_number_disambiguates:
                        ''' if none of the publications has this page number then there the reference is not in the database '''
                        print("NOT FOUND IN DATABASE (no potential publications with these page numbers)", extracted_page_number.encode('utf-8'), sep="\t")
                        count_no_potential_matches += 1
                        reason_for_no_match[citation_id] = "Publication cannot be found in the publication database\t(no potential publications with these page numbers)"

                else:
                    ''' extracted reference does not have page numbers'''
                    if highest_match_score < min_strong_match_score:
                        ''' Ambiguous weak: < 4 matching fields '''
                        print("AMBIGUOUS WEAK (", len((pubs_per_match_score[highest_match_score])), "options with equal match score",highest_match_score,")")
                        count_ambiguous += 1
                        reason_for_no_match[citation_id] = "Ambiguous citation\t"+ str(len((pubs_per_match_score[highest_match_score])))+ " options with equal match score ("+str(highest_match_score)+" fields matched)"
                        if len((pubs_per_match_score[highest_match_score])) < 10:
                            for pub_id in (pubs_per_match_score[highest_match_score]):
                                print(" -", highest_match_score, pub_id, pubid_to_pub_record[pub_id], sep="\t")
                                reason_for_no_match[citation_id] += "\t"+str(pubid_to_pub_record[pub_id])
                    else:
                        ''' Ambiguous strong: >= 4 matching fields '''
                        print("AMBIGUOUS STRONG (", len((pubs_per_match_score[highest_match_score])), "options with equal match score",highest_match_score,")")
                        count_ambiguous += 1
                        reason_for_no_match[citation_id] = "Ambiguous citation\t" + str(
                            len((pubs_per_match_score[highest_match_score]))) + " options with equal match score (" + str(
                            highest_match_score) + " fields matched)"
                        if len((pubs_per_match_score[highest_match_score])) < 10:
                            for pub_id in (pubs_per_match_score[highest_match_score]):
                                print (" +",highest_match_score,pub_id,pubid_to_pub_record[pub_id],sep="\t")
                                reason_for_no_match[citation_id] += "\t" + str(pubid_to_pub_record[pub_id])
            else:
                # only one with highest match score
                for pub_id in (pubs_per_match_score[highest_match_score]):
                    print("MATCH2",highest_match_score,pub_id,pubid_to_pub_record[pub_id],sep="\t")
                    final_matches[citation_id] = pub_id
                    count_total_matched += 1
                    if highest_match_score >= 2:
                        count_strong_match += 1
                    else:
                        count_weak_match += 1



''' PRINT ALL '''


out_pos = open(matches_filepath,'w',encoding='utf-8')
out_neg = open(nonmatches_filepath,'w',encoding='utf-8')

statsfile.write("\nNumber of parsed citations that have no potential matches:\t"+str(sum_parsing_result-number_of_citations_with_at_least_one_match)+"\n")
statsfile.write("Number of citations with at least one potential match:\t"+str(number_of_citations_with_at_least_one_match)+"\n")
statsfile.write("\nNumber of citations with definite match:\t"+str(count_total_matched)+"\n")
statsfile.write("\t\t- strong match:\t"+str(count_strong_match)+"\n")
statsfile.write("\t\t- weak match:\t"+str(count_weak_match)+"\n")
statsfile.write("Ambiguous matching:\t"+str(count_ambiguous)+"\n")

print("\nNumber of parsed citations that have no potential matches:",sum_parsing_result-number_of_citations_with_at_least_one_match,sep="\t")
print("Number of citations with at least one potential match:",number_of_citations_with_at_least_one_match,sep="\t")
print("\nNumber of citations with definite match:",count_total_matched, sep="\t")
print("\t\t- strong match:",count_strong_match,sep="\t")
print("\t\t- weak match:",count_weak_match,sep="\t")
print("Ambiguous matching:",count_ambiguous, sep="\t")


statsfile.write("\nTotal number of unmatched citations:\t"+str(len(citations_in_focus_years)-count_total_matched)+"\n")
statsfile.write("\t\t- cannot be parsed:\t"+str(count_cannot_be_parsed)+"\n")
statsfile.write("\t\t- not found in database:\t"+str(count_no_potential_matches)+"\n")
statsfile.write("\t\t- ambiguous:\t"+str(count_ambiguous)+"\n")

print("\nTotal number of unmatched citations:",len(citations_in_focus_years)-count_total_matched, sep="\t")
print("\t\t- cannot be parsed:",count_cannot_be_parsed,sep="\t")
print("\t\t- not found in database:",count_no_potential_matches,sep="\t")
#print("\t\t- journal id not found:",count_journal_id_not_extracted,sep="\t")
#print("\t\t- journal id found but no other matching fields:",count_no_potential_matches,sep="\t")
print("\t\t- ambiguous:",count_ambiguous,sep="\t")

print("\nFind duplicates with front-page citations and print all")

duplicatesfile = open(duplicatesfilepath,'w',encoding='utf-8')
duplicatesfile.write("citation_id\tpub_id\tpatent_id\tcitation_text\tfp_citation\n")
count_duplicates_with_fp = 0
for citation_id in citations_in_focus_years:

    # print("* citation for journal",jnl_no,"for",year,":",extracted_citation_fields)

    if citation_id in final_matches:

        extracted_citation_fields = all_fields_for_extracted_citation[citation_id]
        (author_extracted, second_author_extracted, citation_has_et_al, year, journal_id, issue_extracted, pages_extracted) = extracted_citation_fields

        ''' De-duplicate with front-page citations for the same patent '''
        patent_id = citation_id_to_patent[citation_id]
        pub_id = final_matches[citation_id]

        for fp_citation_id in fp_citations_per_patent[patent_id]:

                #print(patent_id,author_extracted,fp_citation_id_to_citation_words[fp_citation_id])
            if author_extracted in fp_citation_id_to_citation_words[fp_citation_id] and year in fp_citation_id_to_citation_words[fp_citation_id]:
                print("DUPLICATE WITH FP CITATATION:",citation_id,citation_id_to_patent[citation_id],citation_id_to_citation[citation_id].encode('utf-8')," ".join(fp_citation_id_to_citation_words[fp_citation_id]).encode('utf-8'),sep="\t")
                duplicatesfile.write(citation_id+"\t"+pub_id+"\t"+citation_id_to_patent[citation_id]+"\t"+citation_id_to_citation[citation_id]+"\t"+" ".join(fp_citation_id_to_citation_words[fp_citation_id])+"\n")
                count_duplicates_with_fp += 1


        #print(citation_id,pub_id)
        #print(pubid_to_pub_record[pub_id])
        out_pos.write(
            citation_id+"\t"+citation_id_to_patent[citation_id] + "\t" + citation_id_to_citation[citation_id]+"\t"+year + "\t" + "\t".join(pubid_to_pub_record[pub_id]) + "\n")
    elif citation_id in reason_for_no_match:
        out_neg.write(citation_id+"\t"+citation_id_to_patent[citation_id] + "\t" + citation_id_to_citation[citation_id]+"\t"+ "\t" + reason_for_no_match[citation_id]+"\n")


statsfile.write("Number of duplicates with front-page citations:\t"+str(count_duplicates_with_fp)+"\n")
statsfile.write("Matched publications that are cited in-text only:\t"+str(count_total_matched-count_duplicates_with_fp)+"\n")

print("Number of duplicates with front-page citations:",count_duplicates_with_fp,sep="\t")
print("Matched publications that are cited in-text only:",count_total_matched-count_duplicates_with_fp,sep="\t")

out_pos.close()
out_neg.close()
statsfile.close()
duplicatesfile.close()





