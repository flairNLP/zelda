# since there are only wikipedia ids in the kensho dataset, this script creates a dictionary of id-title pairs
# the titles are obtained by calls to the wikimedia api
# ids that do not have a wikipedia page are discarded (this happens e.g. when the wikipedia page does not exist anymore)

# the redirects are already resolved in the kensho dataset, thats why we do not handle redirects in the script
# Note that since the data is not from the newest wikipedia dump it might happen that some new redirects were introduced since
# but this should concern not too many ids, i.e. an acceptable amount of noise (there are more changes in titles with steady id)

# Note: When running the script it might happen that you get an error "too many calls" to the wikimedia api
# Just run the script again

import json
import requests
import pickle
from pathlib import Path

path_to_kensho_jsnol = '/glusterfs/dfs-gfs-dist/milichma/kensho_wikimedia/link_annotated_text.jsonl'
path_to_save_id_titles_dictionary = '/glusterfs/dfs-gfs-dist/milichma/m/other/kensho_ids_to_titles_redirects_solved.pickle'

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

# pickle the resulting dictionary
with open('/glusterfs/dfs-gfs-dist/milichma/m/other/all_ids_in_kensho', 'wb') as handle:
     pickle.dump(all_ids, handle, protocol=pickle.HIGHEST_PROTOCOL)



# next we try to get a title for each id, we do this by making a call to the wikimedia api for the ids
wikiid_wikiname_dict = {}
wikiid_list = list(all_ids)
ids = ""
length = len(wikiid_list)
bad_ids = 0
lines_counter = 0

for i in range(length):
    lines_counter += 1
    if (i + 1) % 50 == 0 or i == length - 1:  # there is a limit to the number of ids in one request in the wikimedia api

        ids += str(wikiid_list[i])
        # # request

        id_list= [int(x) for x in ids.split('|')]
        resp = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&prop=info|redirects&pageids={ids}&format=json&redirects").json()

        # either the id exists, then get the title
        for wikiid in resp["query"]["pages"]:
            try:
                wikiname_using_id = resp["query"]["pages"][wikiid]["title"]
                wikiid_wikiname_dict[int(wikiid)] = wikiname_using_id
                # next, check for redirects
                # if a given id redirects to another, we save the redirect in the dictionary,
                # i.e. the id does not save a title but the id it redirects to
                if 'redirects' in resp["query"]["pages"][wikiid]:
                    redirected_ids = [x['pageid'] for x in resp["query"]["pages"][wikiid]['redirects']]
                    for idx in id_list:
                        if idx in redirected_ids:
                            print(f'Id {idx} redirects to {wikiid}')
                            wikiid_wikiname_dict[idx] = int(wikiid)

            except KeyError:  # bad wikiid
                print(f'Bad wikipedia id: {wikiid}')
                bad_ids+=1

        ids = ""

    else:
        ids += str(wikiid_list[i])
        ids += "|"

        if lines_counter % 1001 == 0:
            print('processed {:10.4f} %\n'.format((lines_counter / length) * 100))

print(f'Done. Out of ids {len(all_ids)} we have {len(all_ids) - bad_ids} ids that gave a good api response, {bad_ids} not (probably the pages do not exist anymore).')

# add (id,title) pairs from test data as well, a small percentage of them is not covered by kensho
#ids_and_titles = Path.cwd().parent / 'test_data' / 'ids_and_titles' / 'wikiids_to_titles_across_all_test_sets.pickle'
ids_and_titles = '/glusterfs/dfs-gfs-dist/milichma/m/test_data/ids_and_titles/wikiids_to_titles_test_splits.pickle'

with open(ids_and_titles, 'rb') as handle:
    dict_ids_to_titles_in_test = pickle.load(handle)
    for idx in dict_ids_to_titles_in_test:
        wikiid_wikiname_dict[idx] = dict_ids_to_titles_in_test[idx]

# pickle the resulting dictionary
with open(path_to_save_id_titles_dictionary, 'wb') as handle:
     pickle.dump(wikiid_wikiname_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
