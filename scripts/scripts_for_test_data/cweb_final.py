# script for processing the clueweb (cweb) dataset
# data taken from here: https://github.com/lephong/mulrel-nel
# they provide the data in conll format and raw text together with an xml file for the annotations

# the annotations in the cweb dataset are wikipedia page titles
# to make sure these annotations are up-to-date, we check whether the title yields a proper wikipedia page using the wikipedia-api
# then, given the page, we save the up-to-date title and the page id to our data
# if the title does not yield a proper wikipedia page, we discard it

import wikipediaapi
import pickle
import xml.etree.ElementTree as ET
import os
import json

# path to the folder that contains clueweb.xml, clueweb.conll, RawText,...
data_folder = ''

zelda_folder = os.path.join(data_folder, 'zelda_data')
os.mkdir(zelda_folder)

# to get up-to-date annotations we use the wikipedia-api
wiki_wiki = wikipediaapi.Wikipedia(language="en")

original_names_to_ids = {}
wikiids_to_up_to_date_names = {}

number_invalid_titles = 0
number_valid_titles_with_new_name_in_current_wiki = 0

# get all wikipedia titles from the dataset
set_of_all_wikipedia_titles_in_cweb = set()
tree = ET.parse(
    os.path.join(data_folder, 'clueweb.xml'))
root = tree.getroot()
for doc in root:
    for annotation in doc:
        for node in annotation:
            if node.tag == 'wikiName':
                set_of_all_wikipedia_titles_in_cweb.add(node.text)

# get the up-to-date names
for original_wikiname in set_of_all_wikipedia_titles_in_cweb:
    page = wiki_wiki.page(original_wikiname)

    if page.exists():  # page exists
        wikiid = page.pageid
        title = page.title

        if '(disambiguation)' in title or 'List of' in title:
            print(f'--->Wikipedia page name {original_wikiname} is now a disambiguation page. Ignore.')
            number_invalid_titles += 1
            continue

        if title != original_wikiname:
            print(f'Title changed: Old title {original_wikiname} New title: {title}')
            number_valid_titles_with_new_name_in_current_wiki+=1

        original_names_to_ids[original_wikiname] = wikiid
        wikiids_to_up_to_date_names[wikiid] = title
    else:
        print(f'--->Wikipedia page name {original_wikiname} Does not exist. Ignore.')
        number_invalid_titles+=1

print(f'Number of entities: {len(original_names_to_ids) + number_invalid_titles} from which {number_invalid_titles} are invalid')
print(f'Of the {len(original_names_to_ids)} this is the number of them that changed over time: {number_valid_titles_with_new_name_in_current_wiki}')

# save the dictionaries
with open(
        os.path.join(zelda_folder,'wikiids_to_titles_cweb.pickle'),
        'wb') as handle:
    pickle.dump(wikiids_to_up_to_date_names, handle, protocol=pickle.HIGHEST_PROTOCOL)


# get the brackets
document_names_to_brackets = {}
with open(os.path.join(data_folder, 'clueweb-name2bracket.tsv'), mode='r', encoding='utf-8') as nameToBrackets:
    lines = nameToBrackets.readlines()
    for line in lines:
        line_list = line.strip().split('\t')
        document_name = line_list[0]
        bracket = line_list[1]
        document_names_to_brackets[document_name] = bracket

# 1. go through the xml annotations file
docnames_and_annotations = {}
tree = ET.parse(
        os.path.join(data_folder, 'clueweb.xml'))
root = tree.getroot()
for doc in root:
    docnames_and_annotations[doc.attrib['docName']] = []
    for annotation in doc:
        annotation_dict = {}
        for node in annotation:

            if node.tag == 'wikiName':
                annotation_dict['wikiName'] = node.text
            elif node.tag == 'offset':
                annotation_dict['offset'] = int(node.text)
            elif node.tag == 'length':
                annotation_dict['length'] = int(node.text)

        # valid annotation?
        if annotation_dict['wikiName'] in original_names_to_ids:
            start = annotation_dict['offset']
            end = annotation_dict['offset'] + annotation_dict['length']
            wikiid = original_names_to_ids[annotation_dict['wikiName']]
            title = wikiids_to_up_to_date_names[wikiid]
            # save tuple (start, end, id, title)
            docnames_and_annotations[doc.attrib['docName']].append((start, end, wikiid, title))


# first the conll file
current_doc_name = 'clueweb12-0501wb-06-28661'
with open(os.path.join(data_folder,'clueweb.conll'), mode='r', encoding='utf-8') as cweb_original, open(os.path.join(zelda_folder, 'cweb_final.conll'), mode='w', encoding='utf-8') as out_file:

    lines = cweb_original.readlines()

    for line in lines:

        if line.startswith('-DOCSTART-'):

            out_file.write('-DOCSTART-\n\n')

            current_doc_name = line.strip().split()[1][1:]

            try:
                bracket = document_names_to_brackets[current_doc_name]
            except KeyError: # files with no annotation have no bracket
                bracket = 'No bracket provided'

            # write the title and bracket as comment at the beginning of each document

            out_file.write('# ' + current_doc_name + '\t' + bracket + '\n')

        elif line == '\n':
            out_file.write('\n')
        else:
            line_list = line.split('\t')

            if len(line_list) == 1:
                out_file.write(line.strip() + '\tO\tO\n' )

            else: # token with annotation
                token = line_list[0]
                bio_tag = line_list[1]

                original_wikiname = line_list[3].replace('_', ' ')

                if original_wikiname in original_names_to_ids:
                    wikiid = original_names_to_ids[original_wikiname]
                    title = wikiids_to_up_to_date_names[wikiid]
                    out_file.write(
                        token + '\t' + bio_tag + '-' + str(wikiid) + '\t' + bio_tag + '-' +
                        title + '\n')
                else:
                    print(f'Invalid Name in conll file: {original_wikiname}')
                    out_file.write(token + '\tO\tO\n')

# next we create the jsonl file

# write the jsonl file
with open(os.path.join(zelda_folder, 'cweb_final.jsonl'), mode='w', encoding='utf-8') as jsonl_out:

    raw_text_folder = os.path.join(data_folder, 'RawText')

    for filename in os.listdir(raw_text_folder):

        # some files do not seem to have an annotation
        if not filename in docnames_and_annotations:
            continue

        file_dict = {'id':filename, 'bracket': document_names_to_brackets[filename]}
        with open(os.path.join(raw_text_folder, filename), mode='r', encoding='utf-8') as doc_input:
            file_dict['text'] = doc_input.read()
        file_dict['index'] = []
        file_dict['wikipedia_ids'] = []
        file_dict['wikipedia_titles'] = []
        for start, end, wikiid, title in docnames_and_annotations[filename]:
            file_dict['index'].append([start,end])
            file_dict['wikipedia_ids'].append(wikiid)
            file_dict['wikipedia_titles'].append(title)
        json.dump(file_dict, jsonl_out)
        jsonl_out.write('\n')
