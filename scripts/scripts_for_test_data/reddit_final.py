# this script is to process the reddit dataset
# data introduced in paper https://arxiv.org/abs/2101.01228 and can be downloaded here: https://zenodo.org/record/3970806#.Y9pZFhzMI5k

# we have a posts and a comments file, the text is not tokenized, annotations are (in a separate file) in the form (start, end) and wikipedia titles
import json
from pathlib import Path

from flair.tokenization import SpacyTokenizer
from flair.data import Sentence

tokenizer = SpacyTokenizer('en_core_web_sm')
import pickle
import os

import wikipediaapi

wiki_wiki = wikipediaapi.Wikipedia(language="en")

# path to the folder that contains posts.tsv, comments.tsv, gold_post_annotations.tsv, ...
input_data_folder = '../../local_data'
output_data_folder = '../../zelda_data'

input_data_folder = Path(input_data_folder)
input_data_folder.mkdir(exist_ok=True, parents=True)
output_data_folder = Path(output_data_folder)
output_data_folder.mkdir(exist_ok=True, parents=True)

# first, as always, get the up-to-date wikipedia titles and ids
original_names_to_ids = {}
wikiids_to_up_to_date_names = {}

already_processed_names = set()
for filename in ['gold_comment_annotations.tsv', 'gold_post_annotations.tsv']:
    with open(os.path.join(input_data_folder, filename), mode='r', encoding='utf-8') as f_in:
        for line in f_in:
            wikipedia_name_from_dataset = line.split('\t')[3]

            if not wikipedia_name_from_dataset in already_processed_names:
                # print(f'Number of titles processed: {len(already_processed_names)}')
                if wikipedia_name_from_dataset == '9':
                    page = wiki_wiki.page('Fahrenheit 11/9')
                else:
                    page = wiki_wiki.page(wikipedia_name_from_dataset)
                if page.exists():  # page exists
                    original_names_to_ids[wikipedia_name_from_dataset] = page.pageid
                    wikiids_to_up_to_date_names[page.pageid] = page.title
                else:
                    print(f'Bad wikipedia title: {wikipedia_name_from_dataset}. Ignore.')
                already_processed_names.add(wikipedia_name_from_dataset)

# save the dictionaries
with open(
        os.path.join(output_data_folder, 'wikiids_to_titles_reddit.pickle'),
        'wb') as handle:
    pickle.dump(wikiids_to_up_to_date_names, handle, protocol=pickle.HIGHEST_PROTOCOL)

# get the annotations
posts_annotations = []
comments_annotations = []
for filename in ['gold_comment_annotations.tsv', 'gold_post_annotations.tsv']:
    with open(os.path.join(input_data_folder, filename), mode='r', encoding='utf-8') as f_in:
        for line in f_in:
            if filename == 'gold_comment_annotations.tsv':
                comments_annotations.append(line.split('\t'))
            else:
                posts_annotations.append(line.split('\t'))

# posts
# in this file each line is one post
with open(os.path.join(input_data_folder, 'posts.tsv'), mode='r', encoding='utf-8') as posts_input, \
        open(os.path.join(output_data_folder, 'test_reddit_posts.jsonl'), mode='w', encoding='utf-8') as posts_jsonl:
    for line in posts_input:
        reddit_id, subreddit, text = line.strip().split('\t')
        post_dict = {'id': reddit_id + ' ' + subreddit, 'text': text}
        # find the annotations
        index = []
        wikipedia_titles = []
        wikipedia_ids = []
        for annotation_list in posts_annotations:
            if annotation_list[0] == reddit_id and annotation_list[1] == subreddit:
                # annotation belongs to this post
                index.append([int(annotation_list[4]), int(annotation_list[5])])
                wikipedia_id = original_names_to_ids[annotation_list[3]]
                wikipedia_ids.append(wikipedia_id)
                wikipedia_titles.append(wikiids_to_up_to_date_names[wikipedia_id])
        # add example if there are annotations
        if index:
            post_dict['index'] = index
            post_dict['wikipedia_titles'] = wikipedia_titles
            post_dict['wikipedia_ids'] = wikipedia_ids

            json.dump(post_dict, posts_jsonl)
            posts_jsonl.write('\n')

# comments
# note that some comments span over several lines
with open(os.path.join(input_data_folder, 'comments.tsv'), mode='r', encoding='utf-8') as comments_input, \
        open(os.path.join(output_data_folder, 'test_reddit_comments.jsonl'), mode='w',
             encoding='utf-8') as comments_jsonl:
    line = comments_input.readline()
    comments_list = []
    id = ''
    text = ''
    while line:
        line_list = line.split('\t')
        if len(line_list) > 1 and line_list[1].startswith('t') and line_list[1][2] == '_':  # this is a new comment
            if id:
                comments_list.append((id, text))
            # id of new comment
            id = line_list[0] + ' ' + line_list[1] + ' ' + line_list[2] + ' ' + line_list[3]
            text = line_list[4]
        else:  # line is not a new comment
            text += line
        line = comments_input.readline()
    comments_list.append((id, text))
    # now that we collected all comments we get the annotations and write them to the jsonl file
    for comment in comments_list:
        reddit_id, _, __, subreddit = comment[0].split(' ')
        text = comment[1].strip()
        comment_dict = {'id': comment[0], 'text': text}
        wikipedia_ids = []
        wikipedia_titles = []
        index = []
        for annotation_list in comments_annotations:
            if annotation_list[0] == reddit_id and annotation_list[1] == subreddit:
                # annotation belongs to this comment
                index.append([int(annotation_list[4]), int(annotation_list[5])])
                wikipedia_id = original_names_to_ids[annotation_list[3]]
                wikipedia_ids.append(wikipedia_id)
                wikipedia_titles.append(wikiids_to_up_to_date_names[wikipedia_id])
            # add example if there are annotations
        if index:
            comment_dict['index'] = index
            comment_dict['wikipedia_titles'] = wikipedia_titles
            comment_dict['wikipedia_ids'] = wikipedia_ids

            json.dump(comment_dict, comments_jsonl)
            comments_jsonl.write('\n')

# after creating the jsonl files we also create the colmun files
for filename in ['test_reddit_comments', 'test_reddit_posts']:
    with open(os.path.join(output_data_folder, filename + '.jsonl'), mode='r', encoding='utf-8') as input_jsonl, \
            open(os.path.join(output_data_folder, filename + '.conll'), mode='w', encoding='utf-8') as output_conll:
        sentences = []
        for line in input_jsonl:
            line_dict = json.loads(line)
            tokenized_text = Sentence(line_dict['text'], use_tokenizer=tokenizer)

            for index, wikipedia_title, wikipedia_id in zip(line_dict['index'], line_dict['wikipedia_titles'],
                                                            line_dict['wikipedia_ids']):
                mention_start = index[0]
                mention_end = index[1]

                original_mention = line_dict['text'][mention_start:mention_end]

                first = True
                for token in tokenized_text:
                    if (token.start_pos >= mention_start and token.end_pos <= mention_end) \
                            or (token.start_pos >= mention_start and token.start_pos < mention_end):

                        if first:
                            token.set_label(typename='nel',
                                            value='B-' + str(wikipedia_id) + '\t' + 'B-' + wikipedia_title.replace(' ',
                                                                                                                   '_'))
                            first = False
                        else:
                            token.set_label(typename='nel',
                                            value='I-' + str(wikipedia_id) + '\t' + 'I-' + wikipedia_title.replace(' ',
                                                                                                                   '_'))

                # the above annotation of tokenized sentences works pretty well!!! Actually, there is only one erronous case
                if original_mention == 'human' and wikipedia_title == 'Human':
                    for token in tokenized_text:
                        if token.text == 'humans':
                            token.set_label(typename='nel',
                                            value='B-' + str(wikipedia_id) + '\t' + 'B-' + wikipedia_title)
                            break

            sentences.append((line_dict['id'], tokenized_text))

        # after processing all posts, write to file
        for sentence in sentences:
            output_conll.write('-DOCSTART-\n\n')
            output_conll.write('# ' + sentence[0] + '\n')

            for token in sentence[1].tokens:

                label = token.get_label('nel').value

                if label == 'O':  # no entity
                    output_conll.write(token.text + '\tO\tO\n')
                else:
                    output_conll.write(token.text + '\t' + label + '\n')

            output_conll.write('\n')  # empty line after each sentence
