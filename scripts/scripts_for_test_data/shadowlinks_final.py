# script to process the shadow links entity linking dataset
# data comes from this work: https://arxiv.org/abs/2108.10949 and can be downloaded from huggingface: https://huggingface.co/datasets/vera-pro/ShadowLink

# the dataset originally comes in json format, each example is a text with exactly one mention (offset, length)
import json
import os
import pickle
import time
from pathlib import Path

import requests
import wikipediaapi

wiki_wiki = wikipediaapi.Wikipedia(language="en")

from flair.data import Sentence  # TODO: Do not use flair, but some tokenizer directly
from flair.tokenization import SpacyTokenizer

tokenizer = SpacyTokenizer('en_core_web_sm')

write_to_column_file = True

possibly_not_good = 0

wiki_ids_to_titles = {}  # save upt-to-date wikipedia ids and corresponding page titles
bad_to_good_ids = {}  # to correct erroneous ids, i.e. if the id is broken use title to get id

# path to shadowlinks folder that contains the Tail.json, Shadow.json, Top.json
input_data_folder = '../../local_data'
output_data_folder = '../../zelda_data'

input_data_folder = Path(input_data_folder)
input_data_folder.mkdir(exist_ok=True, parents=True)
output_data_folder = Path(output_data_folder)
output_data_folder.mkdir(exist_ok=True, parents=True)

# first get the wikipedia ids and titles
# each example links to one unique entity
for filename in ['Shadow', 'Tail', 'Top']:
    with open(os.path.join(input_data_folder, filename + '.json'), mode='r', encoding='utf-8') as f_in:
        snippets = json.load(f_in)

        for snippet in snippets:

            # first we try to get a title with the provided id
            entity_id = snippet['wiki_id']

            resp = requests.get(
                f"https://en.wikipedia.org/w/api.php?action=query&prop=info|redirects&pageids={entity_id}&format=json&redirects").json()

            # either the id exists, then get the title
            # otherwise we try to get a valid answer using the provided title
            for wikiid in resp["query"]["pages"]:
                try:
                    wikiname_using_id = resp["query"]["pages"][wikiid]["title"]
                    # check if the original id from the data redirects to the found id
                    if 'redirects' in resp["query"]["pages"][wikiid]:
                        redirected_ids = [x['pageid'] for x in resp["query"]["pages"][wikiid]['redirects']]
                        if entity_id in redirected_ids:
                            print(f'Id {entity_id} redirects to {wikiid}')
                            bad_to_good_ids[entity_id] = int(wikiid)
                    wiki_ids_to_titles[int(wikiid)] = wikiname_using_id
                except KeyError:  # bad wikiid
                    print(
                        f'Bad wikipedia id: {entity_id}. Try to get the id using the wikipedia title in the data.')
                    page = wiki_wiki.page(snippet['entity_name'])
                    if page.exists():
                        print('Wikipedia title exists.')
                        bad_to_good_ids[entity_id] = page.pageid
                        wiki_ids_to_titles[page.pageid] = snippet['entity_name']
                    else:
                        print(f"Wikipedia title {snippet['entity_name']} also not good. Ignore annotation.")

# save the wikipedia-ids-to-titles-dictionary
with open(
        os.path.join(output_data_folder, 'wikiids_to_titles_shadowlinks.pickle'),
        'wb') as handle:
    pickle.dump(wiki_ids_to_titles, handle, protocol=pickle.HIGHEST_PROTOCOL)

# first create the jsonl files
for filename in ['Shadow', 'Tail', 'Top']:
    with open(os.path.join(input_data_folder, filename + '.json'), mode='r', encoding='utf-8') as f_in, open(
            os.path.join(output_data_folder, 'test_shadowlinks-' + filename.lower() + '.jsonl'), mode='w',
            encoding='utf-8') as f_out:
        snippets = json.load(f_in)
        for snippet in snippets:
            # check if the annotation is correct
            entity_id = snippet['wiki_id']
            if entity_id in bad_to_good_ids:
                entity_id = bad_to_good_ids[entity_id]
            if not entity_id in wiki_ids_to_titles:
                print(f'Bad id {entity_id}. Do not write example to jsonl.')
                continue
            # write the example to the jsonl
            snippet_id = filename
            if 'entity_space_name' in snippet:
                snippet_id += ': ' + snippet['entity_space_name']
            else:
                snippet_id += ': ' + snippet['entity_name']
            start_of_mention = snippet['span'][0]
            if start_of_mention == -1:  # sometimes the mention start is indicated as -1 -> makes no sense, also detroys some annotations because we compute the mention end by adding the length
                start_of_mention = 0
            end_of_mention = snippet['span'][0] + snippet['span'][1]

            text = snippet['example']
            # manually change the text for a few cases to improve the annotation quality
            if 'S.H.Garrard' in text:
                text = text.replace('S.H.Garrard', 'S.H. Garrard')
                start_of_mention += 1
                end_of_mention += 1
            if 'BY Ferrin (W/A)' in text:
                start_of_mention -= 1
            if 'FOR Fitzwarren PARISH COUNCIL' in text:
                start_of_mention -= 1
            if 'bit of relaxation at Ree in County Meath' in text:  # example of where automatic search for mention fails, they search for 'ree' and locate the mention in the word 'three'
                start_of_mention = 63
                end_of_mention = 66
            if 'Hindustan Hindustan,( Persian: “Land of the Hindus”) ' in text:
                start_of_mention = 101
                end_of_mention = 103
            if 'While ​Overwatch​ doesn’t have a campaign or story mode, ' in text:
                start_of_mention -= 1
            if 'Village of Fredonia municipal water is SAFE to drink and use' in text:
                start_of_mention -= 3
                end_of_mention -= 3
            if 'We have just been informed about the loss of our good friend Goo' in text:
                start_of_mention = 61
                end_of_mention = 64

            snippet_dict = {'id': snippet_id,
                            'text': text,
                            'index': [[start_of_mention, end_of_mention]],
                            'wikipedia_ids': [entity_id],
                            'wikipedia_titles': [wiki_ids_to_titles[entity_id]]}
            json.dump(snippet_dict, f_out)
            f_out.write('\n')

# now the conll files
for filename in ['Shadow', 'Tail', 'Top']:
    with open(os.path.join(input_data_folder, filename + '.json'), mode='r',
              encoding='utf-8') as f_in, open(
            os.path.join(output_data_folder, 'test_shadowlinks-' + filename.lower() + '.conll'), mode='w',
            encoding='utf-8') as f_out:
        snippets = json.load(f_in)
        for snippet in snippets:
            # check if the annotation is correct
            entity_id = snippet['wiki_id']
            if entity_id in bad_to_good_ids:
                entity_id = bad_to_good_ids[entity_id]
            if not entity_id in wiki_ids_to_titles:
                print(f'Bad id {entity_id}. Do not write example to conll.')
                continue

            wikiname = wiki_ids_to_titles[entity_id]
            text = snippet['example']

            snippet_id = filename
            if 'entity_space_name' in snippet:
                snippet_id += ': ' + snippet['entity_space_name']
            else:
                snippet_id += ': ' + snippet['entity_name']

            start_of_mention = snippet['span'][0]
            if start_of_mention == -1:  # sometimes the mention start is indicated as -1 -> makes no sense, also detroys some annotations because we compute the mention end by adding the length
                start_of_mention = 0

            end_of_mention = start_of_mention + snippet['span'][1]

            # manually change the text for a few cases to improve the annotation quality
            if 'Dan Hicks(I)(1951–2020)' in text:
                text = text.replace('Dan Hicks(I)(1951–2020)', 'Dan Hicks (I)(1951–2020)')
            if 'S.H.Garrard' in text:
                text = text.replace('S.H.Garrard', 'S.H. Garrard')
                start_of_mention += 1
                end_of_mention += 1
            if 'Edward Foxcroft`s' in text:
                text = text.replace('Foxcroft`s', 'Foxcroft `s')
            if 'Frakes*Price' in text:
                text = text.replace('Frakes*Price', 'Frakes *Price')
            if '"Ferrier",1' in text:
                text = text.replace('"Ferrier",1', '"Ferrier" ,1')
            if 'BY Ferrin (W/A)' in text:
                start_of_mention -= 1
            if 'FOR Fitzwarren PARISH COUNCIL' in text:
                start_of_mention -= 1
            if 'bit of relaxation at Ree in County Meath' in text:  # example of where automatic search for mention fails, they search for 'ree' and locate the mention in the word 'three'
                start_of_mention = 63
                end_of_mention = 66
            if 'Hindustan Hindustan,( Persian: “Land of the Hindus”) ' in text:
                start_of_mention = 101
                end_of_mention = 103
            if '";exploitation";cinema' in text:
                text = text.replace('";exploitation";cinema', '";exploitation" ;cinema')
            if 'October 27, 2019(Putnam (CDP)' in text:
                text = text.replace('October 27, 2019(Putnam (CDP)', 'October 27, 2019 (Putnam (CDP)')
                start_of_mention += 1
                end_of_mention += 1
            if '107M as the HRB-1' in text:
                text = text.replace('107M as the HRB-1', '107M as the HRB -1')
            if 'Jerry back in. Fraidy Cat8.' in text:
                text = text.replace('Jerry back in. Fraidy Cat8.', 'Jerry back in. Fraidy Cat 8.')
            if 'While ​Overwatch​ doesn’t have a campaign or story mode, ' in text:
                start_of_mention -= 1
            if 'Village of Fredonia municipal water is SAFE to drink and use' in text:
                start_of_mention -= 3
                end_of_mention -= 3
            if 'G for ‘Goner’Whedon remains tight-lipped' in text:
                text = text.replace('G for ‘Goner’Whedon remains tight-lipped',
                                    'G for ‘Goner’ Whedon remains tight-lipped')
            if 'Frings(1909–1981) Pulitzer Prize-winning' in text:
                text = text.replace('Frings(1909–1981) Pulitzer Prize-winning',
                                    'Frings (1909–1981) Pulitzer Prize-winning')
            if 'Gaskill(I) Brian Gaskill' in text:
                text = text.replace('Gaskill(I) Brian Gaskill', 'Gaskill (I) Brian Gaskill')
            if 'Emeritus ProfessorStephenGlaister Contact' in text:
                text = text.replace('Emeritus ProfessorStephenGlaister Contact',
                                    'Emeritus Professor Stephen Glaister Contact')
                start_of_mention += 2
                end_of_mention += 2
            if 'We have just been informed about the loss of our good friend Goo' in text:
                start_of_mention = 61
                end_of_mention = 64
            if 'Approx remuneration Mumtaz-5 lakhs Hema-3 lakhs' in text:
                text = text.replace('Approx remuneration Mumtaz-5 lakhs Hema-3 lakhs',
                                    'Approx remuneration Mumtaz-5 lakhs Hema -3 lakhs')
            if 'Giorgio"Right Here, Right Now" (ft.' in text:
                text = text.replace('Giorgio"Right Here, Right Now" (ft.', 'Giorgio "Right Here, Right Now" (ft.')
            if 'Gordon McDougall(I)(1916–1991)  Gordon McDougall' in text:
                text = text.replace('Gordon McDougall(I)(1916–1991)  Gordon McDougall',
                                    'Gordon McDougall (I)(1916–1991)  Gordon McDougall')
            if 'Burna Boy‘Dumebi’ - Rema‘Wetin We Gain’ - Victor AD‘Fake Love’' in text:
                text = text.replace('Burna Boy‘Dumebi’ - Rema‘Wetin We Gain’ - Victor AD‘Fake Love’',
                                    'Burna Boy‘Dumebi’ - Rema‘Wetin We Gain’ - Victor AD ‘Fake Love’')
            if 'Sarah Ansari&amp;amp;amp;amp;#x27;s recent study is a continuation of her early work which fo' in text:
                text = text.replace(
                    'Sarah Ansari&amp;amp;amp;amp;#x27;s recent study is a continuation of her early work which fo',
                    'Sarah Ansari &amp;amp;amp;amp;#x27;s recent study is a continuation of her early work which fo')
            if 'Driven to Kill(aka Ruslan) is the latest Steven Seagal film' in text:
                text = text.replace('Driven to Kill(aka Ruslan) is the latest Steven Seagal film',
                                    'Driven to Kill (aka Ruslan) is the latest Steven Seagal film')
            if 'George Bellows/Both Members of This Club/1909,' in text:
                text = text.replace('George Bellows/Both Members of This Club/1909,',
                                    'George Bellows/Both Members of This Club /1909,')
            if 'The 1984 Cartagena Declaration on Refugees[i] is a landmark,' in text:
                text = text.replace('The 1984 Cartagena Declaration on Refugees[i] is a landmark',
                                    'The 1984 Cartagena Declaration on Refugees [i] is a landmark')
            if 'TOUR OF UKRAINE’2017  In 2016 with the help of the efforts of the first professional,' in text:
                text = text.replace(
                    'TOUR OF UKRAINE’2017  In 2016 with the help of the efforts of the first professional',
                    'TOUR OF UKRAINE ’2017  In 2016 with the help of the efforts of the first professional')
            if 'Marina Kuznetsova(I)(1925–1996)  Marina Kuznetsova' in text:
                text = text.replace('Marina Kuznetsova(I)(1925–1996)  Marina Kuznetsova',
                                    'Marina Kuznetsova (I)(1925–1996)  Marina Kuznetsova')
            if ' Tale"/"Sheesh!' in text:
                text = text.replace(' Tale" /"Sheesh!', ' Tale"/"Sheesh!')
            if 'Resources  9041Fear of Mirrors3Historical' in text:
                text = text.replace('Resources  9041Fear of Mirrors3Historical',
                                    'Resources  9041 Fear of Mirrors 3Historical')
                start_of_mention += 1
                end_of_mention += 1
            if 'Now the school is known as Nada High School(灘高等学校)' in text:
                text = text.replace('Now the school is known as Nada High School(灘高等学校)',
                                    'Now the school is known as Nada High School (灘高等学校)')
            if 'NEW YORK--(BUSINESS WIRE)--Nanotronics Imaging' in text:
                text = text.replace('NEW YORK--(BUSINESS WIRE)--Nanotronics Imaging',
                                    'NEW YORK--(BUSINESS WIRE)-- Nanotronics Imaging')
                start_of_mention += 1
                end_of_mention += 1

            mention = text[start_of_mention:end_of_mention]
            sentence = Sentence(text, use_tokenizer=tokenizer)

            first = True
            annotated_tokens_string = ''

            for token in sentence:

                if ((token.start_pos >= start_of_mention and token.end_pos <= end_of_mention)
                        or (
                                token.start_pos >= start_of_mention and token.start_pos < end_of_mention and token.text.isalpha())
                        or (
                                token.start_pos >= start_of_mention and token.start_pos < end_of_mention and token.text[
                                                                                                             :-1].isalpha())
                ):
                    if first:
                        token.set_label(typename='nel', value='B-' + str(entity_id) + '\t' + 'B-' + wikiname.replace(' ', '_'))
                        first = False
                    else:
                        token.set_label(typename='nel', value='I-' + str(entity_id) + '\t' + 'I-' + wikiname.replace(' ', '_'))

            # WRITE EACH EXAMPLE TO FILE
            f_out.write('-DOCSTART-\n\n')  # each example is a document in this case
            f_out.write('# ' + snippet_id + '\n')

            for token in sentence.tokens:

                label = token.get_label('nel').value

                if label == 'O':  # no entity
                    f_out.write(token.text + '\tO\tO\n')

                else:
                    f_out.write(token.text + '\t' + label + '\n')

            f_out.write('\n')  # empty line after each sentence
