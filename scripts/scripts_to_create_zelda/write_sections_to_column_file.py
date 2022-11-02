# file to create a column corpus, given a list of wikipedia sections

from flair.tokenization import SpacyTokenizer
from flair.data import Sentence
import pickle
import json
import os
#from ..zelda import PATH_TO_REPOSITORY

def create_zelda_conll(PATH_TO_REPOSITORY):
    print('Create conll file...')
    tokenizer = SpacyTokenizer('en_core_web_sm')

    conll_file_path = os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_train.conll')
    write = open(conll_file_path, mode='w', encoding='utf-8')

    path_to_sections_jsonl = os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_train.jsonl')
    with open(path_to_sections_jsonl, 'r', encoding='utf-8') as input_jsonl:
        total_lines = sum(1 for line in input_jsonl)

    lines_counter = 0

    input_jsonl=open(path_to_sections_jsonl, 'r', encoding='utf-8')
    # given the filtered set of wikipedia pages, create a column file with which one can train
    for line in input_jsonl:

        # we write DOCSTART before each section
        write.write('-DOCSTART-\n\n')

        line_dict = json.loads(line)
        text = line_dict['text']

        # There is still some html syntax in the files.
        # we remove some of it to increase the annotation quality after toknization
        text = text.replace('&nbsp;',
                            '      ')  # we replace it with as many blanks as letters so that the offset poitions of the annotations remain correct
        text = text.replace('&thinsp;', '        ')
        text = text.replace('<small>', '       ')
        text = text.replace('</small>', '        ')
        text = text.replace('&ndash;', '   -   ')
        text = text.replace('</center>', '         ')
        text = text.replace('<center>', '        ')
        text = text.replace('&mdash;', '   -   ')
        text = text.replace('</big>', '      ')
        text = text.replace('<big>', '     ')
        text = text.replace('<br>', '    ')
        # the next one has big consequences
        text = text.replace('||', '  ')

        link_indices = line_dict['index']
        target_page_ids = line_dict['wikipedia_ids']
        wikinames = line_dict['wikipedia_titles']

        sentence = Sentence(text, use_tokenizer=tokenizer)

        # iterate through all annotations and add to corresponding tokens
        for (mention_start, mention_end), wikiname, wikiid in zip(link_indices, wikinames, target_page_ids):

            # set annotation for tokens of entity mention
            first = True
            annotated_tokens_string = ''

            for token in sentence.tokens:
                if ((token.start_pos >= mention_start and token.end_pos <= mention_end)
                        or (
                                token.start_pos >= mention_start and token.start_pos < mention_end)):
                    if first:
                        token.set_label(typename='nel', value='B-' + str(wikiid) + '\t' + 'B-' + str(wikiname))
                        first = False
                    else:
                        token.set_label(typename='nel', value='I-' + str(wikiid) + '\t' + 'I-' + str(wikiname))

        # WRITE EACH SECTION TO FILE
        for token in sentence:
            label = token.get_label('nel').value
            if label == 'O':  # no entity
                write.write(token.text + '\tO\tO\n')
            else:
                write.write(token.text + '\t' + label + '\n')

        # empty line after each section/document
        write.write('\n')

        lines_counter += 1
        if lines_counter % 1000 == 0:
            print('processed {:10.4f} %'.format((lines_counter / total_lines) * 100))

    write.close()
    input_jsonl.close()