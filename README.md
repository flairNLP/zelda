# ZELDA benchmark
ZELDA is an easy-to-use benchmark for entity disambiguation (ED) including train and test data. The idea of ZELDA is to create a fair environment to compare ED architectures and 
to remove the big hurdle that is in the beginning of supervised ED research: Generating training data, choosing an entity set, obtaining and updating test sets, creating candidate 
lists and so on. All these steps are no longer necessary using ZELDA, one can focus on investigating ED architectures. So far ZELDA provides a training corpus covering 8 diverse
test splits, a fixed entity set, candidate lists and entity descriptions. 

The training corpus is derived from the [Kensho Derived Wikimedia Dataset](https://www.kaggle.com/datasets/kenshoresearch/kensho-derived-wikimedia-data) 
(licence [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)). We used the "link_annotated_text.jsonl" that provides wikipedia pages
divided into sections. Each section consists of a name, a text and wikipedia hyperlinks specified by offset, length and wikipedia id of the 
referenced page. 

The test corpora are the test split of the [AIDA CoNLL-YAGO](https://www.mpi-inf.mpg.de/departments/databases-and-information-systems/research/ambiverse-nlu/aida/downloads) dataset (AIDA-b), 
the [Reddit EL corpus](https://doi.org/10.5281/zenodo.3970806), the [Tweeki EL corpus](https://ucinlp.github.io/tweeki/), the [ShadowLink dataset](https://huggingface.co/datasets/vera-pro/ShadowLink) and 
the [WNED-WIKI/WNED-CWEB](https://github.com/lephong/mulrel-nel) corpora processed by [Le and Titov, 2018](https://aclanthology.org/P18-1148/).

### How to use the repository
This repository is basically a collection of python scripts to obtain and process the data.  The intended use is as follows:

1. The test data is ready to use in the test_data folder. Each split comes in jsonl and conll format.

The **conll** files are tab separated. The first line is a text token, second line contains the wikipedia id and the third line the wikipedia title.
Annotations are equipped with BIO-tags, there is a 'O' for tokens with no annotations. Moreover single documents are separated with a '-DOCSTART-' and in the
beginning of each document there is a comment line (starting with '# ', i.e. hashtag followed by blank) that is a unique identifier for each document.
The form of this identifier depends on the respective dataset and usually does not contain any additional information  except for the two datasets cweb and wikipedia: Here 
the document identifier contains the difficulty bracket (separated by a tab). In the following example you see the first lines of the aida-b_final.conll file.
```
-DOCSTART-

# 1163testb SOCCER
SOCCER	O	O
-	O	O
JAPAN	B-993546	B-Japan national football team
GET	O	O
LUCKY	O	O
WIN	O	O
,	O	O
CHINA	B-887850	B-China national football team
IN	O	O
```
In the **jsonl** files each document is in the form of a dictionary with keys 'id', 'text', 'index', 'wikipedia_titles' and 'wikipedia_ids'.
```
import json

input_jsonl = open('test_data/jsonl/aida-b_final.jsonl', mode='r', encoding='utf-8')

# each line represents one document
first_line = next(input_jsonl)
document_dictionary = json.loads(first_line)

document_text = document_dictionary['text']
mention_indices = document_dictionary['index']
mention_gold_titles = document_dictionary['wikipedia_titles']
mention_gold_ids = document_dictionary['wikipedai_ids']

for index, title, idx in zip(mention_indices, mention_gold_titles, mention_gold_ids):
    mention_start = index[0]
    mention_end=index[1]
    print(f'Mention: {document_text[mention_start:mention_end]} --- Wikipedia title: {title} --- Wikipedia id: {idx}')
```

Additionally we provide the entity vocabulary of all test splits combined in test_data/wikiids_to_titles_test_splits.pickle.
```
import pickle

with open('test_data/ids_and_titles/wikiids_to_titles_test_splits.pickle', 'rb') as handle:
    ids_to_titles_test_sets = pickle.load(handle)
    
print(f'There are {len(ids_to_titles_test_sets)} entities in the test sets.')

wikipedia_id = list(ids_to_titles_test_sets.keys())[0]

print(f'Wikipedia id: {wikipedia_id} Wikipedia title: {ids_to_titles_test_sets[wikipedia_id]}')

```

2. To create the train split you need to download the [Kensho Derived Wikimedia Dataset](https://www.kaggle.com/datasets/kenshoresearch/kensho-derived-wikimedia-data), 
more specifically the "link_annotated_text.jsonl" file. Moreover, for tokenization we utilize the 'en_core_web_sm' model from spacy. Download it with the following command:
```
python -m spacy download en_core_web_sm
```
Then, to generate the data, you need to set two paths in the script 'repo/scripts/zelda.py' 
```
...
# replace the path with the path to the file 'link_annotated_text.jsonl' on your system
PATH_TO_KENSHO_JSONL = ''

# replace with the path where you saved the repository on your system
PATH_TO_REPOSITORY = ''
...
```
Also you can set two variables 
```
# If you want a conll version of ZELDA-train, set this to true
create_conll_version_of_zelda_train = True
# If you want to generate the entity descriptions, set this to true 
create_entity_descriptions = True
```
Then, all you need to do is to execute 'zelda.py':
```
# go to the scripts folder and call

python zelda.py
```
Note that it may take a few hours to generate all objects. The generated data will be stored in 'repo/train_data' and contains the zelda-train split (in jsonl and conll format), the entity descriptions (in jsonl format), the 
candidate lists (as a pickled dictionary) and a dictionary containing all id-title pairs (of all train and test sets). 
```
# the entity vocabulary can be handled just as the vocabulary of only the test sets

import pickle

with open('train_data/zelda_ids_to_titles.pickle', 'rb') as handle:
    zelda_ids_to_titles = pickle.load(handle)
    
print(f'There are {len(zelda_ids_to_titles)} entities in zelda.')

wikipedia_id = list(ids_to_titles_test_sets.keys())[0]

print(f'Wikipedia id: {wikipedia_id} Wikipedia title: {ids_to_titles_test_sets[wikipedia_id]}')

# once created, the mention_entities_counter contains, for each collected mention, a dictionary of entity:count pairs where 
we saved how often we saw the respective mention together with a certain entity. 

with open('train_data/zelda_mention_entities_counter.pickle', 'rb') as handle:
    zelda_mention_entities_counter = pickle.load(handle)
    
mention = 'Ronaldo'
print(zelda_mention_entities_counter[mention])
# {'Cristiano Ronaldo': 3, 'Ronaldo (Brazilian footballer)': 2}
```

### Candidate Lists

The script scripts/scripts_for_candidate_lists/demo_of_candidate_lists.py demonstrates how we used the candidate lists to achieve the numbers of our paper (add reference).

|               | AIDA-B        |TWEEKI         | REDDIT-P      |REDDIT-C       |CWEB           |WIKI           |S-TAIL         |S-SHADOW       |S-TOP          |
| ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- |
| MFS           |               |               ||||||||
| CL-Recall     |               |               ||||||||

### Other Scripts
All other scripts in this repository (e.g. scripts_for_test_data, scripts_for_candidate_lists) must not be used and are added for transparency reasons, to show how we created ZELDA. 
The data (id-title dictionaries, candidate lists, etc.) was created in October, 2022. Executing the scripts at another time might change the resulting objects 
because Wikipedia continuously evolves. 
