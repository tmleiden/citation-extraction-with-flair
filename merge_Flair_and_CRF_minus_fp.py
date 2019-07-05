from collections import defaultdict

flair_output_file = "data/all.matches.Flair.out"
crf_output_file = "data/all.matches.CRF.out"
flair_dups_file = "data/Flair_duplicates_with_fp.txt"
crf_dups_file = "data/CRF_duplicates_with_fp.txt"

def read_file(filepath):
    with open(filepath,'r',encoding='utf-8') as data:
        records = data.readlines()
    data.close()
    return records

def store_dups_records(dups_records):
    fp_pub_ids_per_patent = defaultdict(list)

    for record in dups_records:
        citation_id, pub_id, patent_id, citation_text, fp_citation = record.rstrip().split('\t')
        (fp_pub_ids_per_patent[patent_id]).append(pub_id)

    return fp_pub_ids_per_patent

print("read Flair output")
flair_records = read_file(flair_output_file)
print("read CRF output")
crf_records = read_file(crf_output_file)

print("read Flair duplicates with frontpage")
flair_dups_records = read_file(flair_dups_file)
print("read CRF duplicates with frontpage")
crf_dups_records = read_file(crf_dups_file)

print("store fp duplicates per patent for Flair")
fp_pub_ids_per_patent_flair = store_dups_records(flair_dups_records)
print("store fp duplicates per patent for CRF")
fp_pub_ids_per_patent_crf = store_dups_records(crf_dups_records)


print("store Flair records, not on fp")
flair_pubs = defaultdict(int)
flair_pubs_not_on_fp = defaultdict(int)

count_flair = 0
count_flair_on_fp = 0
count_flair_not_on_fp = 0
patents_without_duplicates_flair = defaultdict(int)
for record in flair_records:
    fields = record.rstrip().split('\t')
    patent_id = fields[1]
    pub_id = fields[4]
    count_flair += 1
    flair_pubs[pub_id] += 1
    if patent_id in fp_pub_ids_per_patent_flair:
        fp_pub_ids = fp_pub_ids_per_patent_flair[patent_id]
        if pub_id in fp_pub_ids:
            count_flair_on_fp += 1
        else:
            flair_pubs_not_on_fp[pub_id] += 1
            count_flair_not_on_fp += 1

    else:
        count_flair_not_on_fp += 1
        patents_without_duplicates_flair[patent_id] += 1



print("compare CRF records, not on fp")
count_crf = 0
count_crf_on_fp = 0
count_crf_not_on_fp = 0
count_both = 0
count_both_not_on_fp = 0
count_union = count_flair
count_union_not_on_fp = count_flair_not_on_fp
for record in crf_records:
    fields = record.rstrip().split('\t')
    patent_id = fields[1]
    pub_id = fields[4]
    count_crf += 1
    if pub_id in flair_pubs:
        count_both += 1
    else:
        count_union += 1
    if patent_id in fp_pub_ids_per_patent_crf:
        fp_pub_ids = fp_pub_ids_per_patent_crf[patent_id]
        if pub_id in fp_pub_ids:
            count_crf_on_fp += 1
        else:
            count_crf_not_on_fp += 1
            if pub_id in flair_pubs_not_on_fp:
                count_both_not_on_fp += 1
            else:
                count_union_not_on_fp += 1
    else:
        count_flair_not_on_fp += 1

print()
print("Flair references:",count_flair,sep="\t")
print("Flair references on fp:",count_flair_on_fp,sep="\t")
print("Flair references not on fp:",count_flair_not_on_fp,sep="\t")
print("Number of patents without duplicates between in-text and fp:",len(patents_without_duplicates_flair),sep="\t")

print()
print("CRF references:",count_crf,sep="\t")
print("CRF references on fp:",count_crf_on_fp,sep="\t")
print("CRF references not on fp:",count_crf_not_on_fp,sep="\t")
print()
print("Both:",count_both,sep="\t")
print("Union:",count_union,sep="\t")
print("Both not on fp:",count_both_not_on_fp,sep="\t")
print("Union not on fp:",count_union_not_on_fp,sep="\t")
