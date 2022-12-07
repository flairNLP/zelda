import pickle
import re
import os
import operator
import json

punc_remover = re.compile(r"[\W]+")

PATH_TO_REPOSITORY = ''

# get the mention entities counter
with open(os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_mention_entities_counter.pickle'), 'rb') as handle:
    mention_entities_counter = pickle.load(handle)

# to improve the recall of the candidate lists we add a lower cased and a further reduced version of each mention to the mention set
simpler_mentions_candidate_dict = {}
for mention in mention_entities_counter:
    # create mention without blanks and lower cased
    simplified_mention = mention.replace(' ', '').lower()
    # the simplified mention already occurred from another mention
    if simplified_mention in simpler_mentions_candidate_dict:
        for entity in mention_entities_counter[mention]:
            if entity in simpler_mentions_candidate_dict[simplified_mention]:
                simpler_mentions_candidate_dict[simplified_mention][entity] += mention_entities_counter[mention][entity]
            else:
                simpler_mentions_candidate_dict[simplified_mention][entity] = mention_entities_counter[mention][entity]
    # its the first occurrence of the simplified mention
    else:
        simpler_mentions_candidate_dict[simplified_mention] = mention_entities_counter[mention]

even_more_simpler_mentions_candidate_dict = {}
for mention in mention_entities_counter:
    # create simplified mention
    simplified_mention=punc_remover.sub("", mention.lower())
    # the simplified mention already occurred from another mention
    if simplified_mention in even_more_simpler_mentions_candidate_dict:
        for entity in mention_entities_counter[mention]:
            if entity in even_more_simpler_mentions_candidate_dict[simplified_mention]:
                even_more_simpler_mentions_candidate_dict[simplified_mention][entity] += mention_entities_counter[mention][entity]
            else:
                even_more_simpler_mentions_candidate_dict[simplified_mention][entity] = mention_entities_counter[mention][entity]
    # its the first occurrence of the simplified mention
    else:
        even_more_simpler_mentions_candidate_dict[simplified_mention] = mention_entities_counter[mention]

def get_candidates_and_mfs(mention):
    try:
        candidates = mention_entities_counter[mention]
    except KeyError:
        try:
            candidates = simpler_mentions_candidate_dict[mention.lower().replace(' ', '')]
        except KeyError:
            try:
                candidates = even_more_simpler_mentions_candidate_dict[punc_remover.sub("", mention.lower())]
            except KeyError:
                candidates = []
    if not candidates:
        return [], ''
    else:

        mfs = max(candidates.items(), key=operator.itemgetter(1))[0]

        return list(candidates.keys()), mfs

# get the test sets
test_folder = os.path.join(PATH_TO_REPOSITORY, 'test_data', 'jsonl')
for filename in os.listdir(test_folder):

    number_mentions = 0
    number_mentions_not_contained_in_lists = 0
    number_mfs_mentions = 0
    number_mentions_with_gold_in_candidates = 0

    with open(os.path.join(test_folder, filename), mode='r', encoding='utf-8') as jsnol_input:

        for jline in jsnol_input:
            input_dictionary = json.loads(jline)

            input_text = input_dictionary['text']
            for index, gold_title in zip(input_dictionary['index'], input_dictionary['wikipedia_titles']):
                number_mentions+=1

                mention = input_text[index[0]: index[1]]

                candidates, mfs = get_candidates_and_mfs(mention)

                if not candidates:
                    number_mentions_not_contained_in_lists+=1
                else:
                    if gold_title == mfs:
                        number_mfs_mentions+=1
                    if gold_title in candidates:
                        number_mentions_with_gold_in_candidates+=1

        print(f'================={filename}=================')
        print(f'Number mentions: {number_mentions}, Of which are contained in the candidate lists {number_mentions-number_mentions_not_contained_in_lists} ({number_mentions_not_contained_in_lists} missing).')
        print(f'Total accuracy of mfs: {number_mfs_mentions/number_mentions:.3} ({number_mfs_mentions/(number_mentions-number_mentions_not_contained_in_lists):.3} on the mentions contained in the lists.)')
        print(f'Total recall of candidates: {number_mentions_with_gold_in_candidates/number_mentions:.3} ({number_mentions_with_gold_in_candidates/(number_mentions-number_mentions_not_contained_in_lists):.3} on the mentions contained in the lists.)')
