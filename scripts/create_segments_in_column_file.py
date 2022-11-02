# this script takes a column file and adds/removes empty lines to it such that segments have lengths around min_segment_length (if possible, always respecting document boundaries)
# note that segments might be slighty longer than min_
# recall that segments are consecutive lines without an empty line within a document (i.e. not surpassing a '-DOCSTART-')


from math import inf
import os
min_segment_length = 400

# replace with the file you want to segment
input_file = '/glusterfs/dfs-gfs-dist/milichma/el_test_data/train_data/train_fevry_flair_model/sections.conll'
output_file = '/glusterfs/dfs-gfs-dist/milichma/el_test_data/train_data/train_fevry_flair_model/sections_400_tokens.conll'

# statistics for input file
avg = 0
max = 0
min = inf
number_mentions = 0
number_docs = 0
p = '/glusterfs/dfs-gfs-dist/milichma/el_test_data/train_data/train_fevry_flair_model/conll_test_files/'
for filename in os.listdir(p):
    if filename.endswith('py'):
        continue
    print(filename)
    input_file = p + filename
    output_file = p + filename[:-6] + '_400.conll'
    with open(input_file, mode = 'r', encoding='utf-8') as column_file:

        lines = column_file.readlines()

        section_length = 0
        mentions_in_section = 0
        first = True

        for line in lines:
            if line == '-DOCSTART-\n':
                number_docs+=1
                avg += section_length
                if section_length > max:
                    max = section_length
                if section_length < min and not first:
                    min = section_length
                section_length=0
                first = False

            elif line == '\n' or line.startswith('# '):
                continue

            else:
                section_length+=1
                line_list = line.split('\t')
                #print(line + '################################')
                if line_list[1].startswith('B-'):
                    number_mentions+=1
                    mentions_in_section+=1

        avg /= number_docs

        print(f'Number sections: {number_docs}')
        print(f'Average length: {avg}')
        print(f'Longest section: {max}')
        print(f'Shortest section: {min}')
        print(f'Total number of mentions: {number_mentions}')

    # create the output file
    f_in = open(input_file, mode='r', encoding='utf-8')
    if output_file:
        f_out = open(output_file, mode='w', encoding='utf-8')
    else:
        output_file = input_file + f'_min-seg-length={min_segment_length}'
        f_out = open(output_file, mode='w', encoding='utf-8')

    line = f_in.readline()
    current_length = 0

    while line:
        if '-DOCSTART-' in line:
            f_out.write(line)
            f_out.write('\n')
            current_length=0
        else:
            if line.startswith('# '):
                line = f_in.readline()
                continue
            if line == '\n':
                # check if this is end of document or end of a sentence within a document
                line = f_in.readline()
                if '-DOCSTART-' in line: # end of document
                    f_out.write('\n')
                    current_length=0
                    continue
                else: # this is just an end of a sentence within a document, ignore it
                    continue
            # only write empty line (end of sentence) if segment has at least as many words as min_segment_length
            # but we need to be careful to not break mentions!
            elif current_length >= min_segment_length:
                f_out.write(line)
                line = f_in.readline()
                line_list = line.split('\t')
                while len(line_list) > 1 and line_list[1].startswith('I-'):
                    f_out.write(line)
                    line = f_in.readline()
                    line_list = line.split('\t')
                f_out.write('\n')
                current_length=0

                if not line == '\n':
                    continue

            else: # normal token
                f_out.write(line)
                current_length+=1
        line = f_in.readline()

    f_in.close()
    f_out.close()

    # statistics for output file
    print('\nAfter segmenting:')
    number_segments = 0
    min=inf
    max=0

    with open(output_file , mode = 'r', encoding='utf-8') as column_file:

        line = column_file.readline()
        sentence_list = []
        section_length = 0
        first = True

        while line:

            if line == '-DOCSTART-\n':
                line=column_file.readline() # skip next empty line

            elif line == '\n':
                number_segments += 1
                avg += section_length
                if section_length > max:
                    max = section_length
                if section_length < min:
                    min = section_length
                section_length=0

            else:
                section_length+=1

            line = column_file.readline()

        avg /= number_segments

        print(f'Number of segments: {number_segments}')
        print(f'Average length of segments: {avg}')
        print(f'Longest segment: {max}')
        print(f'Shortest segment: {min}')
