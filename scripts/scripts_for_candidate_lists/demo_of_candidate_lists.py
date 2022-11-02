import pickle
from collections import defaultdict
import re
import os
import operator
import json

punc_remover = re.compile(r"[\W]+")

PATH_TO_REPOSITORY = 'C:\\Users\\Marcel\\Desktop\\Arbeit\\Task\\Entitiy_Linking\\my_dataset_repo\\ED_Dataset'


# to improve the recall of the candidate lists we add a lower cased and a further reduced version of each mention to the mention set
mention_to_mentions = defaultdict(set)

# get the mention entities counter
with open(os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_mention_entity_counter.pickle'), 'rb') as handle:
    mention_entities_counter = pickle.load(handle)

# normal mentions
for mention in mention_entities_counter:
    mention_to_mentions[mention].add(mention)

print(len(mention_to_mentions))

# lower case and remove blanks
for mention in mention_entities_counter:
    simplified_mention = mention.lower().replace(' ', '')
    mention_to_mentions[simplified_mention].add(mention)

    even_more_simplified_mention = punc_remover.sub("", mention.lower())
    mention_to_mentions[even_more_simplified_mention].add(mention)

print(len(mention_to_mentions))

def find_mention(mention):

    try:
        corresponding_mentions = mention_to_mentions[mention]
        return list(corresponding_mentions)
    except KeyError:
        try:
            corresponding_mentions = mention_to_mentions[mention.lower().replace(' ','')]
            return list(corresponding_mentions)
        except KeyError:
            try:
                corresponding_mentions = mention_to_mentions[punc_remover.sub("", mention.lower())]
                return list(corresponding_mentions)
            except KeyError:
                return []


def get_candidates_and_mfs(mentions):
    if not mentions:
        return [], ''
    else:
        candidates = mention_entities_counter[mentions[0]].copy()
        for current_mention in mentions[1:]:
            for cand, occurence in mention_entities_counter[current_mention].items():
                if cand in candidates:
                    candidates[cand] += occurence
                else:
                    candidates[cand] = occurence

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

                mentions = find_mention(mention)
                candidates, mfs = get_candidates_and_mfs(mentions)

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
