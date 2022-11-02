# this script is for processing the test split of the aida yago nel dataset
# link to the data: https://www.mpi-inf.mpg.de/departments/databases-and-information-systems/research/ambiverse-nlu/aida/downloads
# follow instructions to create the conll file: AIDA_CoNLL-YAGO2-annotations.tsv

import wikipediaapi
import requests
import pickle
import os
import json

# data folder containing AIDA_CoNLL-YAGO-annotations.tsv
data_folder = ''

zelda_folder = os.path.join(data_folder, 'zelda_data')
os.mkdir(zelda_folder)


wiki_ids_to_titles = {} # save upt-to-date wikipedia ids and corresponding page titles

# there are 14 ids (and 36 mentions) in the aida dataset (Oct, 2022) that do not exist anymore, we manually replaced them
# bad id is key, good id is value
bad_ids_in_aida_and_good_counterpart = {3313915:35608495, # FC_Barcelona_Bàsquet
                                        2417447:30864466, # Owen_Finegan
                                        26722293:30519527, # St._Louis_Blues_(ice_hockey) -> St._Louis_Blues
                                        353781:47334241, # Luís_Figo
                                        18642444:41188263, # Madrid
                                        6583316: 30875941, # RCD_Espanyol
                                        2413021:30861637, # Hércules_CF
                                        66513:47332321, # Genoa
                                        10052:53199712, # HP_Enterprise_Services -> DXC_Technology
                                        319038:30857003, # Hindu_nationalism
                                        842061:47827636, # Umberto_Bossi
                                        58185:32149462, # Antwerp
                                        54537:32187890, # Cabinet_(government)
                                        183525:47836950, # Guangxi
                                        }

wiki_wiki = wikipediaapi.Wikipedia(language="en")


# step 1: ids and titles
# go through all lines of the column dataset
# skip to the test part
# for all non-Nil annotations, take the id and get the up-to-date-title
counter = 0

with open(os.path.join(data_folder, 'AIDA-YAGO2-dataset.tsv'), mode='r', encoding='utf-8') as aida:

    line = aida.readline()

    # skip lines of train and testa
    while line:
        if '1163testb SOCCER' in line:
            break
        line = aida.readline()

    while line:

        line_list = line.split("\t")

        if len(line_list) > 4:

            wikiname_in_original_data= line_list[4].split("/")[-1]

            idx = int(line_list[5])

            # assume we have one of the bad ids
            if idx in bad_ids_in_aida_and_good_counterpart:
                # replace by good id
                idx = bad_ids_in_aida_and_good_counterpart[idx]

            if not idx in wiki_ids_to_titles:
                    # make a call to the wikipedia api with the given index
                    resp = requests.get(
                        f"https://en.wikipedia.org/w/api.php?action=query&prop=info|redirects&pageids={idx}&format=json&redirects").json()

                    # either the id exists, then get the title
                    # otherwise set the title to 'O'
                    for wikiid in resp["query"]["pages"]:
                        try:
                            wikiname_using_id = resp["query"]["pages"][wikiid]["title"]
                            if 'redirects' in resp["query"]["pages"][wikiid]:
                                redirected_ids = [x['pageid'] for x in resp["query"]["pages"][wikiid]['redirects']]
                                if idx in redirected_ids:
                                    print(f'Id {idx} redirects to {wikiid}')
                                    bad_ids_in_aida_and_good_counterpart[idx] = int(wikiid)
                                    idx = int(wikiid)
                        except KeyError:  # bad wikiid
                            print(idx)
                            print(wikiname_in_original_data)
                            wikiname_using_id = "O"
                            assert 0

                    # save id and name
                    wiki_ids_to_titles[idx] = wikiname_using_id

        line = aida.readline()


# save ids and titles
with open(
        os.path.join(zelda_folder, 'wikiids_to_titles_aida-b.pickle'),
        'wb') as handle:
    pickle.dump(wiki_ids_to_titles, handle, protocol=pickle.HIGHEST_PROTOCOL)


# now: create up-to-date version of aida test

f_out = open(os.path.join(zelda_folder, 'aida-b_final.conll'), mode= 'w', encoding='utf-8')

# create column file:
with open(os.path.join(data_folder, 'AIDA-YAGO2-dataset.tsv'), mode='r', encoding='utf-8') as aida:

    line = aida.readline()

    # skip lines of train and testa
    while line:
        if '1163testb SOCCER' in line:
            break
        line = aida.readline()

    while line:

        if '-DOCSTART-' in line:
            f_out.write('-DOCSTART-\n\n')
            # write the title of the document as a comment
            doc_title = line[12:-2]
            f_out.write('# ' + doc_title + '\n')
        elif line == '\n':
            f_out.write(line)
        else: # token
            line_list = line.split("\t")
            if len(line_list) == 1:
                f_out.write(line_list[0][:-1] + "\tO\tO\n")
            elif '--NME--' in line:
                f_out.write(line_list[0] + "\tO\tO\n")
            else:

                token = line_list[0]

                idx = int(line_list[5])

                # assume we have one of the bad ids
                if idx in bad_ids_in_aida_and_good_counterpart:
                    # replace by good id
                    idx = bad_ids_in_aida_and_good_counterpart[idx]

                title_to_id = wiki_ids_to_titles[idx]

                f_out.write(token + '\t' + line_list[1] + '-' + str(idx) + '\t' + line_list[1] + '-' + title_to_id + '\n')


        line = aida.readline()

f_out.close()

# the aida-b dataset does come exclusively in conll format
# in the following we want to create a jsonl file from the conll file
# since there is no "whitespace after?" information for the tokens in the conll file, we just concatenate the tokens with blanks
with open(os.path.join(zelda_folder, 'aida-b_final.conll'), mode='r', encoding='utf-8') as input_conll, open(os.path.join(zelda_folder, 'aida-b_final.jsonl'),mode='w',encoding='utf-8') as output_jsonl:

    text = ''
    id = ''
    link_indices = []
    link_ids = []
    link_titles = []

    line=input_conll.readline()
    while line:
        # comment line
        if line.startswith('# '):
            # set id
            id = line[2:-1]
        # beginning of new document
        elif line.startswith('-DOCSTART-'):
            if text:
                doc = {'id':id, 'text': text, 'index': link_indices, 'wikipedia_ids': link_ids, 'wikipedia_titles':link_titles}
                json.dump(doc,output_jsonl)
                output_jsonl.write('\n')
            text = ''
            id = ''
            link_indices = []
            link_ids = []
            link_titles = []
            # skip next (empty) line
            line = input_conll.readline()

        # line with token
        else:
            # ignore empty lines
            if line == '\n':
                pass
            else:
                token, wiki_id, wiki_title = line.split('\t')
                # no annotation
                if wiki_id == 'O':
                    text += token + ' '
                # beginning of annotation
                elif wiki_id.startswith('B-'):
                    start_index = len(text)
                    text += token + ' '
                    # go through the whole annotation
                    line = input_conll.readline()
                    line_list = line.split('\t')
                    while len(line_list) == 3 and line_list[1].startswith('I-'):
                        text+=line_list[0] + ' '
                        line = input_conll.readline()
                        line_list = line.split('\t')
                    end_index = len(text) - 1
                    link_indices.append((start_index,end_index))
                    link_ids.append(int(wiki_id[2:]))
                    link_titles.append(wiki_title[2:-1])
                    continue
        line=input_conll.readline()

    # add the last document
    if text:
        doc = {'id': id, 'text': text, 'index': link_indices, 'wikipedia_ids': link_ids,
               'wikipedia_titles': link_titles}
        json.dump(doc, output_jsonl)
        output_jsonl.write('\n')
