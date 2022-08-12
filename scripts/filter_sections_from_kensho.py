# this script transforms the kensho wikimedia dataset into a small list of wikipedia 'sections' using the test-datasets
from pathlib import Path
import json
import random
import pickle
import zipfile

random.seed(11) # must be set to 11

# replace with where you want to save the resulting sections list
folder_to_save_list_of_sections = ''

# first you need to download the kensho file. Go to https://www.kaggle.com/datasets/kenshoresearch/kensho-derived-wikimedia-data and get the 'link_annotated_text.jsonl'
# replace the path with the path to the file on your system
path_to_kensho_jsonl = ''

# first we get all the wikipedia ids in the test datasets
print('Get ids from test data')
test_folder = Path.cwd().parent / 'test_data'
set_of_all_ids_in_test = set()

for conll_file in test_folder.iterdir():
    with open(conll_file, mode='r', encoding='utf-8') as input_file:
        for line in input_file:
            line_list = line.split('\t')
            if line_list[1].startswith('B-'):
                set_of_all_ids_in_test.add(int(line_list[1][2:]))

# TODO: print how many ids

# second open the kensho wikimedia file and create a list of sections
print('Create list of sections')
list_of_sections = []
test_entities_and_count = {idx: 0 for idx in set_of_all_ids_in_test}
with open(path_to_kensho_jsonl, mode='r', encoding='utf-8') as read:
    line = read.readline()

    while line:

        jline = json.loads(line)

        for section in jline['sections']:
            # ignore useless/list-like sections
            if section['name'] not in ['Bibliography', 'Discography', 'External Links', 'Filmography', 'Footnotes',
                                       'Further Reading', 'Notes', 'References', 'See Also']:
                list_of_sections.append(section)
                for idx in section['target_page_ids']:
                    if idx in test_entities_and_count:
                        test_entities_and_count[idx] += 1

        line = read.readline()

# TODO: print how many sections loaded

print('Load id-titles dictionary')
# we also need the id to titles dictionary
zip_folder = Path.cwd().parent / 'other'
with zipfile.ZipFile(zip_folder / 'kensho_ids_to_titles.zip', 'r') as zip_ref:
    zip_ref.extractall(zip_folder)
with open(zip_folder / 'dictionary_of_all_wikiids_and_pagenames.pickle', 'rb') as handle:
    kensho_dict_id_to_title = pickle.load(handle)

# TODO: print to confirm that dictionary loaded

# now, depending on the threshold, we sample sections from the list until each test entity is covered at least threshold times (if possible)
threshold = 10

entities_and_how_often_already_covered = {idx: 0 for idx in
                                          set_of_all_ids_in_test}  # save, for each entity, how often we have seen it so far
entities_not_covered_enough_times_yet = set_of_all_ids_in_test.copy()  # start with all entities, and remove them as soon as we have seen them enough times

remaining_sections_list = []

# randomly shuffle the sections
random_order = random.sample(range(len(list_of_sections)), len(list_of_sections)) # randomly shuffle the sections

for index in random_order:

    # stop, if all entities have been seen enough times
    if not entities_not_covered_enough_times_yet:
        print('Done')
        break

    section = list_of_sections[index]

    link_offsets = section['link_offsets']
    link_lengths = section['link_lengths']

    target_page_ids = section['target_page_ids']  # all links in that section

    for idx in entities_not_covered_enough_times_yet:
        # if there is an id that we did not see enough times yet, add page to final list
        if idx in target_page_ids:

            # we also want to have the titles of the links, not only the ids
            link_titles = []
            for id in section['target_page_ids']:
                link_titles.append(kensho_dict_id_to_title[str(id)])

            new_link_lengths = []
            new_link_offsets = []
            new_target_page_ids = []
            new_target_page_titles = []

            for i in range(len(link_titles)):

                # TODO: comment to explain this
                if link_titles[i] != 'O':
                    new_link_lengths.append(section['link_lengths'][i])
                    new_link_offsets.append(section['link_offsets'][i])
                    new_target_page_ids.append(section['target_page_ids'][i])
                    new_target_page_titles.append(link_titles[i])

            # update
            new_section = {}
            new_section['name'] = section['name']
            new_section['text'] = section['text']
            new_section['link_lengths'] = new_link_lengths
            new_section['link_offsets'] = new_link_offsets
            new_section['target_page_ids'] = new_target_page_ids
            new_section['target_page_titles'] = new_target_page_titles

            remaining_sections_list.append(section)

            # update count
            for wiki_id in target_page_ids:
                if wiki_id in entities_and_how_often_already_covered:
                    entities_and_how_often_already_covered[wiki_id] += 1

            # update covered set if necessary
            for wiki_id in entities_and_how_often_already_covered:
                count = entities_and_how_often_already_covered[wiki_id]

                if count >= threshold or count >= test_entities_and_count[wiki_id]:
                    if wiki_id in entities_not_covered_enough_times_yet:
                        entities_not_covered_enough_times_yet.remove(wiki_id)
                        print(
                            f'{(1 - (len(entities_not_covered_enough_times_yet) / len(set_of_all_ids_in_test))) * 100:.2f}% of test ids covered')

            # TODO: comment to explain this :D
            break

with open(folder_to_save_list_of_sections + 'list_of_sections.pickle', 'wb') as handle:
    pickle.dump(remaining_sections_list, handle, protocol=pickle.HIGHEST_PROTOCOL)
