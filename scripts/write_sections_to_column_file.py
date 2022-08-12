# file to create a column corpus, given a list of wikipedia sections

from flair.tokenization import SpacyTokenizer
from flair.data import Sentence
import pickle

tokenizer = SpacyTokenizer('en_core_web_sm')

# replace with where you want to save the conll file
conll_file_path = ''
write = open(conll_file_path, mode='w', encoding='utf-8')

# load list of sections, replace the path with the path to the list of sections on your system (which has been created using filter_sections_from_kensho.py)
path_to_list_of_sections = ''
with open(path_to_list_of_sections, 'rb') as handle:
    list_of_sections = pickle.load(handle)

correct_formatted_mentions = 0
not_correct_formatted_mentions = 0

lines_counter = 0
total_lines = len(list_of_sections)

# given the filtered set of wikipedia pages, create a column file with which one can train
for section in list_of_sections:

    # we write DOCSTART before each section
    write.write('-DOCSTART-\n\n')

    text = section['text']

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

    link_offsets = section['link_offsets']
    link_lengths = section['link_lengths']
    target_page_ids = section['target_page_ids']
    wikinames = section['target_page_titles']

    sentence = Sentence(text, use_tokenizer=tokenizer)

    # iterate through all annotations and add to corresponding tokens
    for mention_offset, mention_length, wikiname, wikiid in zip(link_offsets, link_lengths, wikinames, target_page_ids):

        mention_end = mention_offset + mention_length

        # set annotation for tokens of entity mention
        first = True
        annotated_tokens_string = ''

        for token in sentence.tokens:
            if ((token.start_pos >= mention_offset and token.end_pos <= mention_end)
                    or (
                            token.start_pos >= mention_offset and token.start_pos < mention_end)):
                if first:
                    token.set_label(typename='nel', value='B-' + str(wikiid) + '\t' + 'B-' + str(wikiname))
                    first = False
                else:
                    token.set_label(typename='nel', value='I-' + str(wikiid) + '\t' + 'I-' + str(wikiname))

    # WRITE EACH SECTION TO FILE
    for token in sentence:
        label = token.get_label('nel').value
        if label == '':  # no entity
            write.write(token.text + '\tO\n')
        else:
            write.write(token.text + '\t' + label + '\n')

    # empty line after each section/document
    write.write('\n')

    lines_counter += 1
    if lines_counter % 1000 == 0:
        print('processed {:10.4f} %\n'.format((lines_counter / total_lines) * 100))

write.close()
