# script to combine the candidate lists created from Wikilinks, Kensho Wikipedia and Wikidata

import os
import zipfile
import pickle

def merge_candidate_lists(PATH_TO_REPOSITORY):

    final_lists = {}

    cg_folder = os.path.join(PATH_TO_REPOSITORY, 'other')

    for source in ['wikidata', 'kensho', 'wikilinks']:

        with zipfile.ZipFile(os.path.join(cg_folder, 'mention_entities_counter_' + source + '.zip'), 'r') as zip_ref:
            zip_ref.extractall(cg_folder)
        with open(os.path.join(cg_folder, 'mention_entities_counter_' + source + '.pickle'), 'rb') as handle:
            current_mention_entities_counter = pickle.load(handle)

        for mention in current_mention_entities_counter:
            if mention in final_lists:
                for entity in current_mention_entities_counter[mention]:
                    if entity in final_lists[mention]:
                        final_lists[mention][entity] += 1
                    else:
                        final_lists[mention][entity] = 1
            else:
                final_lists[mention] = current_mention_entities_counter[mention]

    # save the final lists
    with open(os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_mention_entities_counter.pickle'), 'wb') as handle:
        pickle.dump(final_lists, handle, protocol=pickle.HIGHEST_PROTOCOL)
