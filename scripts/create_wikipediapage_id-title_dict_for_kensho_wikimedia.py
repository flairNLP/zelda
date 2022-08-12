# since there are only wikipedia ids in the kensho dataset, this script creates a dictionary of id-title pairs
# the titles are obtained by a call to the wikimedia api

import json
import requests
import pickle
from pathlib import Path

path_to_kensho_jsnol = ''
path_to_save_id_titles_dictionary = ''

# whether or not to add the id-title pairs of the test sets
# note that there are a few ids in the test set not covered with links in kensho
add_test_set_ids_and_titles = True

# first we get all ids from kensho
print('create set of all ids in the data')
all_ids = set()

with open(path_to_kensho_jsnol, mode='r', encoding='utf-8') as kensho:
    line = kensho.readline()
    while line:

        jline = json.loads(line)

        page_id = jline['page_id'] #integer
        all_ids.add(page_id)

        for section in jline['sections']:
            all_ids.update(section['target_page_ids'])

        line = kensho.readline()

print(f'Id set created, total of {len(all_ids)} wikipedia ids in the kensho dataset.')

# next we try to get a title for each id, we do this by making a call to the wikimedia api for the ids
wikiid_wikiname_dict = {}
wikiid_list = list(all_ids)
ids = ""
length = len(wikiid_list)
bad_ids = 0
lines_counter = 0
total_lines = 5354091 # total lines in kensho

for i in range(length):
    lines_counter += 1
    if (i + 1) % 50 == 0 or i == length - 1:  # there is a limit to the number of ids in one request in the wikimedia api

        ids += str(wikiid_list[i])
        # request
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "prop": "info",
                "pageids": ids,
                "format": "json",
            },
        ).json()

        for wikiid in resp["query"]["pages"]:
            try:
                wikiname = resp["query"]["pages"][wikiid]["title"]
            except KeyError:  # bad wikiid
                bad_ids+=1
                wikiname = "O"
            wikiid_wikiname_dict[int(wikiid)] = wikiname
        ids = ""

    else:
        ids += str(wikiid_list[i])
        ids += "|"

        if lines_counter % 1000 == 0:
            print('processed {:10.4f} %\n'.format((lines_counter / total_lines) * 100))

print(f'Done. Out of ids {len(all_ids)} we have {len(all_ids) - bad_ids} ids that gave a good api response, {bad_ids} not (probably the pages do not exist anymore).')

# if desired, the pairs from the test data are added, almost all of them should be already covered
if add_test_set_ids_and_titles:

    test_folder = Path.cwd().parent / 'test_data'

    for conll_file in test_folder.iterdir():
        with open(conll_file, mode='r', encoding='utf-8') as input_file:
            for line in input_file:
                line_list = line.split('\t')
                if line_list[1].startswith('B-'):
                    idx = int(line_list[1][2:])
                    title = int(line_list[2][2:])
                    wikiid_wikiname_dict[idx] = title

# pickle the resulting dictionary
with open(path_to_save_id_titles_dictionary, 'wb') as handle:
     pickle.dump(wikiid_wikiname_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
