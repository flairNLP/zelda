# first you need to download the kensho file. Go to https://www.kaggle.com/datasets/kenshoresearch/kensho-derived-wikimedia-data and get the 'link_annotated_text.jsonl'
# replace the path with the path to the file 'link_annotated_text.jsonl' on your system
PATH_TO_KENSHO_JSONL = 'C:\\Users\\Marcel\\Desktop\\tmp_arbeit\\ddddd\\link_annotated_text.jsonl'

# replace with the path where you saved the repository on your system
PATH_TO_REPOSITORY = 'C:\\Users\\Marcel\\Desktop\\Arbeit\\Task\\Entitiy_Linking\\my_dataset_repo\\ED_Dataset'

# If you want a conll version of ZELDA-train, set this to true
create_conll_version_of_zelda_train = True
# If you want to generate the entity descriptions, set this to true
create_entity_descriptions = True

# all files will be stored in repo/train_data

from scripts.scripts_to_create_zelda.filter_sections_from_kensho import create_train_jsonl
from scripts.scripts_to_create_zelda.merge_candidate_lists import merge_candidate_lists
from scripts.scripts_to_create_zelda.write_sections_to_column_file import create_zelda_conll
from scripts.scripts_to_create_zelda.generate_entity_descriptions import generate_entity_descriptions

create_train_jsonl(PATH_TO_REPOSITORY=PATH_TO_REPOSITORY, PATH_TO_KENSHO_JSONL=PATH_TO_KENSHO_JSONL)
merge_candidate_lists(PATH_TO_REPOSITORY=PATH_TO_REPOSITORY)

if create_conll_version_of_zelda_train:
    create_zelda_conll(PATH_TO_REPOSITORY=PATH_TO_REPOSITORY)

if create_entity_descriptions:
    generate_entity_descriptions(PATH_TO_REPOSITORY=PATH_TO_REPOSITORY, PATH_TO_KENSHO_JSONL=PATH_TO_KENSHO_JSONL)