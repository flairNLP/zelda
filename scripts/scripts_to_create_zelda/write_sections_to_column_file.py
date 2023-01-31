# file to create a column corpus, given a list of wikipedia sections
import spacy
import json
import os


def create_zelda_conll(PATH_TO_REPOSITORY):
    print('Create conll file...')

    conll_file_path = os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_train.conll')
    write = open(conll_file_path, mode='w', encoding='utf-8')

    path_to_sections_jsonl = os.path.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_train.jsonl')
    with open(path_to_sections_jsonl, 'r', encoding='utf-8') as input_jsonl:
        total_lines = sum(1 for line in input_jsonl)

    lines_counter = 0

    nlp = spacy.load("en_core_web_sm")

    input_jsonl = open(path_to_sections_jsonl, 'r', encoding='utf-8')
    # given the filtered set of wikipedia pages, create a column file with which one can train
    for line in input_jsonl:

        # we write DOCSTART before each section
        write.write('-DOCSTART-\n')

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

        # tokenize and sentence split the text
        doc = nlp(text)

        # get all token start indices
        offsets = set()
        sentence_starts = set()
        for token in doc:
            offsets.add(token.idx)
            sentence_starts.add(token.sent[0].idx)
        offsets.add(len(text))

        # add all entity start indices and remember entities as list
        links = []
        for (mention_start, mention_end), wikiname, wikiid in zip(link_indices, wikinames, target_page_ids):
            if mention_start == mention_end: continue # some anchor texts get removed due to formatting weirdness
            offsets.add(mention_start)
            links.append((mention_start, mention_end, wikiname.replace(' ', '_'), str(wikiid)))

        # order all offsets
        offsets_ordered = list(offsets)
        offsets_ordered.sort()

        # get the first link
        next_link = links.pop(0)
        entity_started = False

        # go through all start positions
        for start, end in zip(offsets_ordered, offsets_ordered[1:]):

            # a newline before each sentence
            if start in sentence_starts:
                write.write('\n')

            span_token = text[start:end].rstrip()

            # if start position greater than current link, get next link
            if next_link and start > next_link[1] - 1:

                if not entity_started:
                    print("ERROR! Next entity started before previous was written")

                next_link = links.pop(0) if len(links) > 0 else None
                entity_started = False

            tag = 'O\tO'

            # if we are inside an entity
            if next_link and entity_started and start > next_link[0]:
                tag = 'I-' + next_link[3] + '\t' + 'I-' + next_link[2]

            # if start position is that of link, add annotation
            if next_link and start == next_link[0]:
                tag = 'B-' + next_link[3] + '\t' + 'B-' + next_link[2]
                entity_started = True

            if span_token.strip() != '':
                write.write(span_token + '\t' + tag + '\n')

        if len(links) > 0:
            print("ERROR! Unmatched entities left!")

        # empty line after each section/document
        write.write('\n')

        lines_counter += 1
        if lines_counter % 1000 == 0:
            print('processed {:10.4f} %'.format((lines_counter / total_lines) * 100))

    write.close()
    input_jsonl.close()
