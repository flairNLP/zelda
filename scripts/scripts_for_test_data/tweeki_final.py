# this script is to process the tweeki gold dataset
# the dataset is from the paper 'Tweeki: Linking Named Entities on Twitter to a Knowledge Graph' (https://aclanthology.org/2020.wnut-1.29.pdf)
# and can be downloaded here: https://ucinlp.github.io/tweeki/

import wikipediaapi
from qwikidata.linked_data_interface import get_entity_dict_from_api
import pickle
import json
import os

wiki_wiki = wikipediaapi.Wikipedia(language="en")

wiki_ids_to_titles = {}  # save upt-to-date wikipedia ids and corresponding page titles
annotations_to_wikipedia_ids = {}  # keep track of the annotations we already saw

# Note: The text in the json file provided by the creators is just the tokens of the conll-file joined with blanks. So e.g. there is blanks between the last word of a sentence and the ending '.', etc.

# path to Tweeki_gold folder that contains the Tweeki_gold and Tweeki_gokd.jsonl
data_folder=''

zelda_folder = os.path.join(data_folder, 'zelda_data')
os.mkdir(zelda_folder)

# First thing we do is to process the annotations, annotations come in the form 'wikipedia_page_title|wikidata_q_id'
# What we want is wikipedia title and wikipedia id (both up-to-date)

# this fucntion takes an annotation in the form 'wikipedia_page_title|wikidata_q_id' and hands back wikipedia title and wikipedia id, if they exist
def get_up_to_date_wiki_title_and_id_from_tweeki_annotation(annotation: str):
    wikiname, q_id = annotation.split('|')
    # first, try with the given wikipedia name
    try:
        page = wiki_wiki.page(wikiname)

        if page.exists():  # page exists
            return page.pageid, page.title
        else:
            print(f"Wikipedia page name '{wikiname}' does not exist")
            print('Try with q-id')
            try:
                q_dict = get_entity_dict_from_api(q_id)

                print('q-id is okay!')

                try:
                    # try to acces the wikipedia page name saved in wikidata
                    wikiname = q_dict['sitelinks']['enwiki']['title']

                    page = wiki_wiki.page(wikiname)

                    if page.exists():
                        return page.pageid, page.title
                    else:
                        assert 0, 'wikiname saved in wikidata does not exist?????'

                except KeyError:
                    print(f"No english wikipedia link to q-id {q_id} in wikidata, do not use annotation '{annotation}'")
                    return None, None
            except:
                print(f"q-id also not okay!!! do not use '{annotation}' ")
                return None, None
    except:
        assert 0, 'Unexpected exception with wikipedia page name ???'


# open the tweeki conll file and get all the annotations
with open(os.path.join(data_folder, 'Tweeki_gold'), mode='r',
          encoding='utf-8') as tweeki_conll:
    set_of_annotations = set()
    for line in tweeki_conll:
        if not line.startswith('#') and not line == '\n':
            annotation = line.split('\t')[-1].strip()
            if line.endswith('\t\n'):
                annotation = line.split('\t')[-2]
            if annotation != '-':
                set_of_annotations.add(annotation)

    for annotation in set_of_annotations:
        wikipedia_id, wikipedia_title = get_up_to_date_wiki_title_and_id_from_tweeki_annotation(annotation)
        if wikipedia_id:
            wiki_ids_to_titles[wikipedia_id] = wikipedia_title
            annotations_to_wikipedia_ids[annotation] = wikipedia_id
        else:
            annotations_to_wikipedia_ids[annotation] = -1

# save the wikipedia-ids-to-titles-dictionary
with open(
        os.path.join(zelda_folder, 'wikiids_to_titles_tweeki.pickle'),
        'wb') as handle:
    pickle.dump(wiki_ids_to_titles, handle, protocol=pickle.HIGHEST_PROTOCOL)

# once we have the the annotations processed, we produce the output file
#first the conll version
with open(os.path.join(data_folder,'Tweeki_gold'), mode='r',
          encoding='utf-8') as conll_input, open(
        os.path.join(zelda_folder, 'tweeki_final.conll'), mode='w',
        encoding='utf-8') as conll_output:
    for line in conll_input:

        if line.startswith('# tweet_id'):
            conll_output.write('-DOCSTART-\n\n')
            id = line.split()[-1]
            conll_output.write('# tweet_id=' + id + '\n')  # add the tweet id
        elif line.startswith('#'):
            continue
        elif line == '\n':
            conll_output.write('\n')
        else:  # line with a token
            line_list = line.split('\t')

            line_annotation = line_list[-1].strip()
            if line.endswith('\t\n'):
                line_annotation = line_list[-2]
            if line_annotation == '-':
                conll_output.write(line_list[1] + '\tO\tO\n')
            else:
                if '4	and	O	-' in line:  # somehow there is a problem with this line somewhere in the file
                    conll_output.write('and\tO\tO\n')
                    continue
                token = line_list[1]
                bio_tag = line_list[2][0]
                # print(line)
                wikipedia_id = annotations_to_wikipedia_ids[line_annotation]
                if wikipedia_id != -1:
                    wikipedia_title = wiki_ids_to_titles[wikipedia_id]
                    conll_output.write(
                        token + '\t' + bio_tag + '-' + str(
                            wikipedia_id) + '\t' + bio_tag + '-' + wikipedia_title + '\n')
                else:
                    conll_output.write(token + '\tO\tO\n')

# next, also provide the wikipedia annotations for the json file
with open(os.path.join(data_folder, 'Tweeki_gold.jsonl'), mode='r',
          encoding='utf-8') as json_input, open(
        os.path.join(zelda_folder, 'tweeki_final.jsonl'), mode='w',
        encoding='utf-8') as json_output:
    for line in json_input:
        line_dict = json.loads(line)
        new_index = []
        wikipedia_ids = []
        wikipedia_titles = []
        for index, annotation in zip(line_dict['index'], line_dict['link']):
            annotation = annotation.strip()
            wikipedia_id = annotations_to_wikipedia_ids[annotation]
            if wikipedia_id != -1:
                wikipedia_title = wiki_ids_to_titles[wikipedia_id]
                new_index.append(index)
                wikipedia_ids.append(wikipedia_id)
                wikipedia_titles.append(wikipedia_title)
        del line_dict['link']
        # save text as 'text' instead of sentence
        text = line_dict['sentence']
        line_dict['text'] = text
        del line_dict['sentence']
        line_dict['index'] = new_index
        line_dict['wikipedia_ids'] = wikipedia_ids
        line_dict['wikipedia_titles'] = wikipedia_titles
        json.dump(line_dict, json_output)
        json_output.write('\n')
