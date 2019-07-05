#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 26 18:39:16 2019

@author: osx024
"""

import os

groundtruth_bio_dir = 'data/ground_truth_bio/'
all_filenames = os.listdir(groundtruth_bio_dir+"bio-origin/")


large_sent = []
print ("Read BIO files...")
for filename in all_filenames:


    if '.bio' in filename:
        print(filename)
        items_for_this_file = []
        i = 0
        with open(groundtruth_bio_dir+"bio-origin/"+filename,'r',encoding='utf-8') as bio_file:
            f= open(groundtruth_bio_dir+"final_bio/"+filename,"w+",encoding='utf-8')
            citation = False
            previous_pos = " "
            for line in bio_file:
                i += 1

                columns = line.rstrip().split()

                if len(columns) == 3:
                    word = columns[0]
                    pos = columns[1]
                    biotag = columns[2]


                    if biotag=="O":

                        if word[0].isupper() and previous_pos=='.' and i>=20 and word!="No.":
                            f.write("\n")
                            f.write(line)
                            i =0
                        elif i>=40:
                            f.write("\n")
                            f.write(line)
                            i =0
                        else:
                            f.write(line)
                    else:
                        f.write(line)

                    previous_pos = pos

            f.close()
