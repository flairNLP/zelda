# ZELDA benchmark

ZELDA is a comprehensive benchmark for entity disambiguation (ED). You can use it to train and evaluate ED models.

Download ZELDA as one big zip file [here](https://nlp.informatik.hu-berlin.de/resources/datasets/zelda/zelda_full.zip). Inside, you'll find this structure:

```console
ZELDA
├── train_data
│   ├── zelda_train.conll
│   └── zelda_train.jsonl
├── test_data
│   ├── conll
│   │   ├── test_aida-b.conll
│   │   ├── test_cweb.conll
│   │   ├── test_reddit-comments.conll
│   │   ...
│   └── jsonl
│       ├── test_aida-b.jsonl
│       ├── test_cweb.jsonl
│       ├── test_reddit-comments.jsonl
│       ...
└── other
    ├── zelda_mention_entities_counter.pickle
    └── entity_descriptions.jsonl
```

The `train_data` folder contains the training split (use either conll or jsonl version). The `test_data` folder contains all 9 evaluation splits in both formats. The `other` folder contains entity descriptions and candidate lists.


# How to Load

You should train your model using ZELDA train and evaluate with all 9 test splits. The macro-averaged accuracy over all splits is your final evaluation number. 

This section shows different ways to load the data for training and testing.

## Load with Flair

The easiest way to load and explore the corpus is through [**`flair`**](https://github.com/flairNLP/flair). Simply use this snippet to load the corpus and iterate through some sentences and their anntation: 


```python
from flair.datasets import ZELDA

# get Zelda corpus and print statistics
corpus = ZELDA()
print(corpus)

# get a sentence of the test split 
sentence = corpus.test[1]

# print this sentence with all annotations 
print(sentence)

# iterate over linked entities in this sentence and print each
for entity in sentence.get_labels('nel'):
    print(entity)
```


## Load in CoNLL-Format

You can load the CoNLL format directly. In this format, each line is a token followed by the ID and URL annotations of this token, in BIO format:

```
-DOCSTART-

# 1163testb SOCCER
SOCCER	O	O
-	O	O
JAPAN	B-993546	B-Japan_national_football_team
GET	O	O
LUCKY	O	O
WIN	O	O
,	O	O
CHINA	B-887850	B-China_national_football_team
IN	O	O
```
## Load in JSONL-Format

In the **jsonl** files each document is in the form of a dictionary with keys 'id', 'text', 'index', 'wikipedia_titles' and 'wikipedia_ids'. For instance, run this snippet to load:

```python
import json

input_jsonl = open('test_data/jsonl/aida-b_final.jsonl', mode='r', encoding='utf-8')

# each line represents one document
first_line = next(input_jsonl)
document_dictionary = json.loads(first_line)

document_text = document_dictionary['text']
mention_indices = document_dictionary['index']
mention_gold_titles = document_dictionary['wikipedia_titles']
mention_gold_ids = document_dictionary['wikipedia_ids']

for index, title, idx in zip(mention_indices, mention_gold_titles, mention_gold_ids):
    mention_start = index[0]
    mention_end=index[1]
    print(f'Mention: {document_text[mention_start:mention_end]} --- Wikipedia title: {title} --- Wikipedia id: {idx}')
```

# How to Cite

Please refer to our paper for information on how the benchmark was constructed:

```
@inproceedings{milich2023zelda,
  title={{ZELDA}: A Comprehensive Benchmark for Supervised Entity Disambiguation},
  author={Milich, Marcel and Akbik, Alan},
  booktitle={{EACL} 2023,  The 17th Conference of the European Chapter of the Association for Computational Linguistics},
  year={2023}
}
```

# More Info

Next to our paper, more information on the scripts used to create this dataset is found [here](SCRIPTS.md).
