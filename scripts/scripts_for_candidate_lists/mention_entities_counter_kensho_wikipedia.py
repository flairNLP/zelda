# script to create the candidate lists
# from three sources (kensho wikimedia, wikilinks and wikidata "also known as") we count, for each apperaing mention, how often it refers to specific entities in wikipedia

import json
from collections import defaultdict
import pickle
import os

mention_and_entities_counter = defaultdict(dict)

PATH_TO_REPOSITORY = ''
folder_of_kensho_link_annotated_jsonl = ''

lines_counter = 0
total_lines_kensho = 5354091

# get entity vocabulary from ZELDA
with open(os.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_ids_to_titles.pickle'), 'rb') as handle:
    ids_to_titles_zelda = pickle.load(handle)

with open(os.path.join(folder_of_kensho_link_annotated_jsonl, 'link_annotated_text.jsonl'), mode = 'r', encoding='utf-8') as kensho_lines:

    for line in kensho_lines:
        jline = json.loads(line)

        for section in jline['sections']:

            text = section['text']

            link_offsets = section['link_offsets']
            link_lengths = section['link_lengths']
            target_page_ids = section['target_page_ids']

            for offset, length, idx in zip(link_offsets, link_lengths, target_page_ids):

                # only consider entities that are contained in ZELDA
                try:
                    title = ids_to_titles_zelda[idx]
                except KeyError:
                    continue

                mention = text[offset:offset+length]

                if title in mention_and_entities_counter[mention]:
                    mention_and_entities_counter[mention][title] +=1
                else:
                    mention_and_entities_counter[mention][title] = 1

        lines_counter += 1
        if lines_counter % 1000 == 0:
            print('processed {:10.4f} %\n'.format((lines_counter / total_lines_kensho) * 100))

with open(
        os.path.join(folder_of_kensho_link_annotated_jsonl, 'mention_entities_counter_kensho.pickle'),
        'wb') as handle:
    pickle.dump(mention_and_entities_counter, handle, protocol=pickle.HIGHEST_PROTOCOL)
