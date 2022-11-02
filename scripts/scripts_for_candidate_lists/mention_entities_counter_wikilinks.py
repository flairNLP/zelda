# script to generate the candidate lists from the wikilinks corpus
# the dataset can be downloaded here https://code.google.com/archive/p/wiki-links/downloads
# you can also use the following command in linux:
# for (( i=0; i<10; i++ )) do echo "Downloading file $i of 10"; wget https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/wiki-links/data-0000$i-of-00010.gz ; done
# after downloading unpack the ten files: for (( i=0; i<10; i++ )) do gzip -d data-0000$i-of-00010.gz ; done
import os
import multiprocessing
import wikipediaapi
import pickle
import urllib.parse
import requests
import time

folder_of_wikilinks_files = '/glusterfs/dfs-gfs-dist/milichma/wikilinks/new'

# as a first step we collect all wikipedia titles in the dataset
# since the dataset is rather old we need to check the titles for existence and update them if necessary
set_of_all_wikipedia_titles_in_wikilinks = set()
for filename in os.listdir(folder_of_wikilinks_files):

    if not filename.startswith('data-'):
        continue

    with open(os.path.join(folder_of_wikilinks_files, filename), mode='r') as wikilinks_input:

        for line in wikilinks_input:

            if line.startswith('MENTION'):

                original_wikipedia_title = line.strip().split('/')[-1]

                # ignore certain titles
                if ('#' in original_wikipedia_title  # link to section of wikipedia page
                                     or original_wikipedia_title.startswith('File:')  # link to files
                                     or original_wikipedia_title.startswith('Wikibooks:')  # wikibooks??
                                     or original_wikipedia_title.startswith('Template:')  # Template Documentation of Wikipedia
                                     or original_wikipedia_title.startswith('User:')  # user page
                                     or original_wikipedia_title.startswith('Image:')
                                     or original_wikipedia_title.startswith('Category:')
                                     or original_wikipedia_title.startswith('Wikipedia:')
                                     or original_wikipedia_title.startswith('Help:')
                                     or original_wikipedia_title.startswith('De:')
                                     or original_wikipedia_title.startswith('de:')
                                     or original_wikipedia_title.startswith('it:')
                                     or original_wikipedia_title.startswith('ru:')
                                     or original_wikipedia_title.startswith('Ru:')
                                     or original_wikipedia_title.startswith('ja:')
                                     or original_wikipedia_title.startswith('fr:')
                                     or original_wikipedia_title.startswith('cs:')
                                     or original_wikipedia_title.startswith('nl:')
                                     or original_wikipedia_title.startswith('pl:')
                                     or original_wikipedia_title.startswith('Visionaries:')
                                     or original_wikipedia_title.startswith('Wikisource:')
                                     or original_wikipedia_title.startswith('Wikt:')
                                     or original_wikipedia_title.startswith('Scores:')
                                     or original_wikipedia_title.startswith('S:')
                                     or original_wikipedia_title.startswith('Project:')
                                     or original_wikipedia_title.startswith('Wiktionary:')
                                     or original_wikipedia_title.endswith('_(disambiguation)')
                                     or '%23' in original_wikipedia_title # this is the url encoding for '#' which means that there is a link to a specific section of an article, we don't do that
                             ):
                    continue

                set_of_all_wikipedia_titles_in_wikilinks.add(original_wikipedia_title)

# save the dictionaries
# with open(
#         os.path.join('/glusterfs/dfs-gfs-dist/milichma/wikilinks/new', 'set_of_titles.pickle'),
#         'wb') as handle:
#     pickle.dump(set_of_all_wikipedia_titles_in_wikilinks, handle, protocol=pickle.HIGHEST_PROTOCOL)

# with open(os.path.join('/glusterfs/dfs-gfs-dist/milichma/wikilinks/new', 'set_of_titles.pickle'),
#         'rb') as handle:
#     set_of_all_wikipedia_titles_in_wikilinks= pickle.load(handle)

# once we have the original wikipedia titles we will check each one of them for existence


# this function mainly removes the url encoding that is present int the urls of the data
def clean_wikipedia_page_name(wikiname):
    # remove url/percentage encoding
    processed = urllib.parse.unquote(wikiname)
    processed = urllib.parse.unquote(processed)
    processed = urllib.parse.unquote(processed)

    processed = processed.strip()

    # through un-url-encoding the wikipagename some extra blanks occur
    if '_ _' in processed:
        if processed in ['Fort_Lauderdale_ _Hollywood_International_Airport', 'Clayton_County_Airport_ _Tara_Field',
                         'Canada_ _United_States_border', 'Howard_Beach_ _JFK_Airport_(IND_Rockaway_Line)',
                         'Rennes_ _Saint-Jacques_Airport']:
            processed.replace('_ _', '_-_')
        else:
            processed.replace('_ _', '_+_')

    # some links start with 'en:' e.g. en:Nauvoo,_Illinois
    if processed.startswith('en:'):
        processed = processed[3:]

    # For some reason some of the names either start or begin with an '_'
    if processed.startswith('_'):
        processed = processed[1:]
    if processed.endswith('_'):
        processed = processed[:-1]

    if '|' in processed:
        processed = processed.replace('|', '')

    return processed

# each consumer checks titles for existance using the wikipedia-api
class Consumer(multiprocessing.Process):

    def __init__(self, task_queue, return_dict):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.wikipedia = wikipediaapi.Wikipedia(language="en")
        self.original_titles_to_id ={}
        self.return_dict = return_dict

    def run(self):
        proc_name = self.name
        while True:
            titles_list = self.task_queue.get()
            if titles_list is None:
                # Poison pill means shutdown
                print('%s: Exiting' % proc_name)
                self.task_queue.task_done()
                self.return_dict[proc_name] = self.original_titles_to_id
                break


            for original_title in titles_list:

                cleaned_title = clean_wikipedia_page_name(original_title)

                if not cleaned_title:
                    continue

                # this title caused an endless loop
                if cleaned_title == 'Visionaries:_Knights_of_the_Magical_Light&origin=':
                    continue

                try:
                    resp = requests.get(
                             f"https://en.wikipedia.org/w/api.php?action=query&format=json&titles={cleaned_title}&indexpageids&redirects").json()
                except:
                    # this happens when there are too many api calls
                    titles_list.append(original_title) # append the title again and do it again in a later iteration
                    print(f'Bad call ----------------------------------> {cleaned_title}')
                    continue

                try:
                    for wikiid in resp['query']['pages']:
                        if not wikiid.startswith('-'):
                            self.original_titles_to_id[original_title] = int(wikiid)
                        else:
                            print(f'Page does not exist: {original_title}')
                except KeyError:
                    print(resp)


            self.task_queue.task_done()


tasks = multiprocessing.JoinableQueue()
manager = multiprocessing.Manager()
return_dict = manager.dict()

# Start consumers
num_consumers = 15
print('Creating %d consumers' % num_consumers)
consumers = [Consumer(tasks, return_dict)
             for i in range(num_consumers)]


for w in consumers:
    w.start()

number_titles = len(set_of_all_wikipedia_titles_in_wikilinks)
list_of_titles = list(set_of_all_wikipedia_titles_in_wikilinks)

print(number_titles)

# Enqueue jobs
for i in range(number_titles//1000):
#for i in range(num_consumers):
    tasks.put(list_of_titles[i*1000:(i+1)*1000])

# Add a poison pill for each consumer
for i in range(num_consumers):
    tasks.put(None)

# Wait for all of the tasks to finish
tasks.join()

print(return_dict.keys())

key = list(return_dict.keys())[0]

print(return_dict[key])

# to filter entities we do not need, first get the entity vocabulary from ZELDA
with open('/glusterfs/dfs-gfs-dist/milichma/new_m/train_data/zelda_ids_to_titles.pickle',
        'rb') as handle:
    ids_to_titles_zelda= pickle.load(handle)

original_titles_to_ids_dict = {}

for key in return_dict:

    for orig_title, idx in return_dict[key].items():
        if idx in ids_to_titles_zelda:
            original_titles_to_ids_dict[orig_title] = idx

# now that we have the mapping from original titles to updated wikipedia ids, we create the lists
mention_entities_counter = {}


for filename in os.listdir(folder_of_wikilinks_files):

    if not filename.startswith('data-'):
        continue

    print(filename)

    with open(os.path.join(folder_of_wikilinks_files, filename), mode='r') as wikilinks_input:

        for line in wikilinks_input:

            if line.startswith('MENTION'):

                line_list = line.strip().split('\t')

                original_wikipedia_title = line_list[-1].split('/')[-1]
                mention = line_list[1]

                if original_wikipedia_title in original_titles_to_ids_dict:
                    idx = original_titles_to_ids_dict[original_wikipedia_title]
                    updated_title = ids_to_titles_zelda[idx]

                    if mention in mention_entities_counter:
                        if updated_title in mention_entities_counter[mention]:
                            mention_entities_counter[mention][updated_title] +=1
                        else:
                            mention_entities_counter[mention][updated_title] = 1
                    else:
                        mention_entities_counter[mention] = {updated_title : 1}

# save the dictionaries
with open(
        os.path.join('/glusterfs/dfs-gfs-dist/milichma/new_m/cg/', 'mention_entities_counter_wikilinks.pickle'),
        'wb') as handle:
    pickle.dump(mention_entities_counter, handle, protocol=pickle.HIGHEST_PROTOCOL)
