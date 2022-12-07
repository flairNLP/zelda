# this script is there to get an 'entity description' for each of the entities we have in ZELDA

# we derive almost all of the entity descriptions from the kensho dataset, for some pages kensho does not have an 'Introduction' section, then we use the wikipedia api
# the entity description consists of the first sentence of the corresponding Wikipedia article
# to obtain the first sentence we use a sentence splitter

import wikipediaapi
import pickle
import json
import os
from flair.tokenization import SpacySentenceSplitter, SpacyTokenizer

# get all relevant entity titles
def generate_entity_descriptions(PATH_TO_REPOSITORY, PATH_TO_KENSHO_JSONL):
    print('Generate entity descriptions...')

    tokenizer = SpacyTokenizer('en_core_web_sm')
    sentence_splitter = SpacySentenceSplitter('en_core_web_sm', tokenizer=tokenizer)

    wiki_wiki = wikipediaapi.Wikipedia(language="en")

    # get the entities from zelda
    with open(os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_ids_to_titles.pickle'), 'rb') as handle:
        zelda_ids_to_titles = pickle.load(handle)

    # get the id-title dict for kensho
    with open(os.path.join(PATH_TO_REPOSITORY, 'other', 'kensho_ids_to_titles_redirects_solved.pickle'), 'rb') as handle:
        kensho_dict_id_to_title = pickle.load(handle)

    with open(PATH_TO_KENSHO_JSONL, mode='r', encoding='utf-8') as kensho_jsonl, open(os.path.join(PATH_TO_REPOSITORY, 'train_data', 'entity_descriptions.jsonl'), mode='w', encoding='utf-8') as output_jsonl:
        set_of_entity_ids_in_zelda = set(zelda_ids_to_titles.keys())
        counter = 0
        no_introduction = 0
        number_of_entities = len(set_of_entity_ids_in_zelda)
        for page_line in kensho_jsonl:
            page_dict = json.loads(page_line)
            page_id = page_dict['page_id']
            if not page_id in kensho_dict_id_to_title:
                continue
            if type(kensho_dict_id_to_title[page_id]) == int:
                page_id = kensho_dict_id_to_title[page_id]

            if page_id in set_of_entity_ids_in_zelda:
                set_of_entity_ids_in_zelda.remove(page_id)
                title = zelda_ids_to_titles[page_id]
                # add description
                section_names = [sec['name'] for sec in page_dict['sections']]
                if 'Introduction' in section_names:
                    text = page_dict['sections'][0]['text']
                else:
                    no_introduction+=1
                    page = wiki_wiki.page(title)
                    try:
                        text = page.summary
                    except:
                        print(f'Bad wikipedia call for title: {title}. Save empty entity description.')
                        text = ''

                text = text[:1200]
                sentences = sentence_splitter.split(text)
                if len(sentences) > 0:
                    entity_description = sentences[0].to_original_text()
                else:
                    print(f'Empty entity descripction to title: {title}')
                    entity_description = ''

                outpt_dict = {'wikipedia_id': page_id, 'wikipedia_title': title, 'description': entity_description}
                json.dump(outpt_dict, output_jsonl)
                output_jsonl.write('\n')
                counter += 1
                if counter % 1000 == 0:
                    print(
                        f'{counter / number_of_entities * 100:.2f}% entities processed.')

                    print(f'Introduction={counter - no_introduction}, NO Introduction = {no_introduction}')
