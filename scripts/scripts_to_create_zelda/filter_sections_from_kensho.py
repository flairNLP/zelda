# this script transforms the kensho wikimedia dataset into a small list of wikipedia 'sections' using the test-datasets

#from ..zelda import PATH_TO_REPOSITORY, PATH_TO_KENSHO_JSONL
import os
import random
import json
import pickle
from collections import defaultdict
import zipfile

def create_train_jsonl(PATH_TO_REPOSITORY, PATH_TO_KENSHO_JSONL):
    random.seed(11) # this has to be set to 11 to obtain the same dataset

    path_to_save_sections_jsonl = os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_train.jsonl')

    # first we get all the wikipedia ids in the test datasets
    print('Get ids from test data')
    ids_to_titles_test = os.path.join(PATH_TO_REPOSITORY, 'test_data', 'ids_and_titles', 'wikiids_to_titles_test_splits.pickle')

    with open(ids_to_titles_test, 'rb') as handle:
        dict_ids_to_titles_in_test = pickle.load(handle)

    set_of_all_ids_in_test = set(dict_ids_to_titles_in_test.keys())

    print(f'Test sets contain {len(set_of_all_ids_in_test)} ids in total.')

    # get for each test entity a count, how often it is referred to by links in Kensho Wikipedia
    # this is necessary since some entitis are being referred to less than threshold times, some even zero times
    # Moreover we create a list of triples (page-name, section-name, entity ids) for each appropriate section
    # from this list we will later
    print('Load lists and count entities...')
    list_of_section_triples = []
    test_entities_and_count = {idx: 0 for idx in set_of_all_ids_in_test}
    with open(PATH_TO_KENSHO_JSONL, mode='r', encoding='utf-8') as read:
        line = read.readline()

        while line:

            jline = json.loads(line)

            page_id = jline['page_id']

            for section in jline['sections']:
                # ignore useless/list-like sections
                if section['name'] not in ['Bibliography', 'Discography', 'External Links', 'Filmography', 'Footnotes',
                                           'Further Reading', 'Notes', 'References', 'See Also']:

                    add_section = False

                    # add section only if it links to one of the test ids
                    for entity_id in section['target_page_ids']:
                        if entity_id in test_entities_and_count:
                            test_entities_and_count[entity_id] += 1
                            add_section=True

                    if add_section:
                        list_of_section_triples.append((page_id, section['name'], section['target_page_ids']))

            line = read.readline()

    print(f'Loaded {len(list_of_section_triples)} sections.')


    print('Select sections...')

    # now, depending on the threshold, we sample sections from the list until each test entity is covered at least threshold times (if possible)
    threshold = 10

    entities_and_how_often_already_covered = {idx: 0 for idx in
                                              set_of_all_ids_in_test}  # save, for each entity, how often we have seen it so far
    entities_not_covered_enough_times_yet = set_of_all_ids_in_test.copy()  # start with all entities, and remove them as soon as we have seen them enough times

    selected_sections = defaultdict(list)

    # randomly shuffle the sections, so that sections are not processed article by article, but in a total random fashion
    random_order = random.sample(range(len(list_of_section_triples)), len(list_of_section_triples)) # randomly shuffle the sections

    for index in random_order:

        # stop, if all entities have been seen enough times
        if not entities_not_covered_enough_times_yet:
            print('Done')
            break

        section_triple = list_of_section_triples[index]

        target_page_ids = section_triple[2]  # all links in that section

        for idx in entities_not_covered_enough_times_yet:
            # if there is an id that we did not see enough times yet, add page to final list
            if idx in target_page_ids:

                # we save the section with a dictionary
                selected_sections[section_triple[0]].append(section_triple[1]) # key=page_id;value=section_name

                # update count
                for wiki_id in target_page_ids:
                    if wiki_id in entities_and_how_often_already_covered:
                        entities_and_how_often_already_covered[wiki_id] += 1

                # update covered set if necessary
                for wiki_id in entities_and_how_often_already_covered:
                    if wiki_id in entities_not_covered_enough_times_yet:

                        count = entities_and_how_often_already_covered[wiki_id]
                        if count >= threshold or count >= test_entities_and_count[wiki_id]:
                                entities_not_covered_enough_times_yet.remove(wiki_id)
                                print(
                                    f'{(1 - (len(entities_not_covered_enough_times_yet) / len(set_of_all_ids_in_test))) * 100:.2f}% of test ids covered')

                # we added the section and updated the counts and sets
                # thus we can continue with the next section
                break


    # finally create the jsonl file

    print('Load id-titles dictionary')
    # we also need the id to titles dictionary
    zip_folder = os.path.join(PATH_TO_REPOSITORY, 'other')
    with zipfile.ZipFile(os.path.join(zip_folder, 'kensho_ids_to_titles_redirects_solved.zip'), 'r') as zip_ref:
        zip_ref.extractall(zip_folder)
    with open(os.path.join(zip_folder, 'kensho_ids_to_titles_redirects_solved.pickle'), 'rb') as handle:
        kensho_dict_id_to_title = pickle.load(handle)

    print('Done.')

    # final vocabulary
    zelda_ids_to_titles = {}

    print('Write sections to file...')
    with open(path_to_save_sections_jsonl, mode='w', encoding='utf-8') as jsnol_output, open(PATH_TO_KENSHO_JSONL, mode='r', encoding='utf-8') as kensho_lines:

        for line in kensho_lines:

            jline = json.loads(line)
            page_id = jline['page_id']
            if page_id in selected_sections:

                sections_to_add = selected_sections[page_id]
                for section in jline['sections']:

                    if section['name'] in sections_to_add:

                        # write section to our dataset
                        link_offsets = section['link_offsets']
                        link_lengths = section['link_lengths']
                        # we also want to have the titles of the links, not only the ids
                        link_titles = []
                        for idx in section['target_page_ids']:
                            try:
                                title = kensho_dict_id_to_title[idx]
                                if type(title) == int: # redirect
                                    title = kensho_dict_id_to_title[title]
                                link_titles.append(title)
                            except KeyError:
                                link_titles.append('O')

                        new_link_lengths = []
                        new_link_offsets = []
                        new_target_page_ids = []
                        new_target_page_titles = []

                        for i in range(len(link_titles)):

                            # some wikipedia ids do not return a response when doing a call to the wikimedia api (probably outdated ids)
                            # this concerns only a tiny subset of all the ids
                            if link_titles[i] != 'O':
                                new_link_lengths.append(link_lengths[i])
                                new_link_offsets.append(link_offsets[i])
                                new_target_page_ids.append(section['target_page_ids'][i])
                                new_target_page_titles.append(link_titles[i])
                                zelda_ids_to_titles[section['target_page_ids'][i]] = link_titles[i]

                        # update
                        new_section = {'page_id': page_id}
                        new_section['section_name'] = section['name']
                        new_section['text'] = section['text']
                        indices = []
                        for offset, length in zip(new_link_offsets, new_link_lengths):
                            indices.append((offset, offset + length))
                        new_section['index'] = indices
                        new_section['wikipedia_ids'] = new_target_page_ids
                        new_section['wikipedia_titles'] = new_target_page_titles

                        # dump the section
                        json.dump(new_section,jsnol_output)
                        jsnol_output.write('\n')

    # add id-title pairs of the test set to the final vocabulary
    # a small fraction might not be covered by the links in the data for various reasons
    for idx in dict_ids_to_titles_in_test:
        zelda_ids_to_titles[idx] = dict_ids_to_titles_in_test[idx]

    # pickle the final vocabulary
    with open(
            os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_ids_to_titles.pickle'),
            'wb') as handle:
        pickle.dump(zelda_ids_to_titles, handle, protocol=pickle.HIGHEST_PROTOCOL)

    print('Done!')