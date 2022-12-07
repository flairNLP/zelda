# script to utilize wikidata aliases as candidatate lists
# the idea is as follows: given a wikipedia title, we check whether a corresponding wikidata entry exists
# if so, we go to the "also known as" field, we take every entry as a mention referring to the title that we started with


import json
import shutil
import pickle
import pywikibot
from collections import defaultdict
import os
import multiprocessing

PATH_TO_REPOSITORY = ''

# first we need to get all titles of our vocabulary

# get all titles from train and test
# load the set of titles from ZELDA, we will only consider these titles
with open(os.join(PATH_TO_REPOSITORY, 'train_data', 'zelda_ids_to_titles.pickle'), 'rb') as handle:
    ids_to_titles_zelda = pickle.load(handle)

set_of_titles_in_train_and_test = set(ids_to_titles_zelda.values())
number_titles = len(set_of_titles_in_train_and_test)
list_of_titles = list(set_of_titles_in_train_and_test)
print(number_titles)

# create temporary folder for the results of the processes
folder_to_save_output_dict = ''
tmp_folder_path = os.path.join(folder_to_save_output_dict, 'tmp')
if not os.path.exists(tmp_folder_path):
    os.mkdir(tmp_folder_path)

class Consumer(multiprocessing.Process):

    def __init__(self, task_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.site =  pywikibot.Site("en", "wikipedia")

    def run(self):
        proc_name = self.name
        f = open(os.path.join(tmp_folder_path, proc_name), mode ='w', encoding='utf-8')
        while True:
            titles_list = self.task_queue.get()
            if titles_list is None:
                # Poison pill means shutdown
                print('%s: Exiting' % proc_name)
                self.task_queue.task_done()
                f.close()
                break

            for title in titles_list:
                # add title itself as a mention
                f.write(title + '\t' + title + '\n')
                # then Wikidata
                page = pywikibot.Page(self.site, title)
                try:
                    item = pywikibot.ItemPage.fromPage(page)
                    try:
                        aliases = item.aliases['en']
                        for alias in aliases:
                            f.write(alias + '\t' + title +'\n')
                    except KeyError:
                        print(f'No english aliases for: {title}')
                except:
                    print(f'Page does not exist in wikidata: {title}')
            self.task_queue.task_done()
        return



if __name__ == '__main__':
    # Establish communication queues
    tasks = multiprocessing.JoinableQueue()

    # Start consumers
    num_consumers = min(multiprocessing.cpu_count(), 15) # should not be too much, since there are some problems with the api otherwise
    print('Creating %d consumers' % num_consumers)
    consumers = [Consumer(tasks)
                 for i in range(num_consumers)]
    for w in consumers:
        w.start()

    # Enqueue jobs
    for i in range(number_titles//100):
        tasks.put(list_of_titles[i*100:(i+1)*100])

    # Add a poison pill for each consumer
    for i in range(num_consumers):
        tasks.put(None)

    # Wait for all of the tasks to finish
    tasks.join()

    # unify the results
    mention_entities_counter = {}

    for file_name in os.listdir(tmp_folder_path):
        with open(os.path.join(tmp_folder_path, file_name), mode='r', encoding='utf-8') as input_file:
            print(file_name)
            for line in input_file:
                line_list = line.strip().split('\t')
                mention = line_list[0]
                entity = line_list[1]

                if mention in mention_entities_counter:
                    if entity in mention_entities_counter[mention]:
                        mention_entities_counter[mention][entity] += 1
                    else:
                        mention_entities_counter[mention][entity] = 1
                else:
                    mention_entities_counter[mention] = {entity: 1}

    # save mention entities counter
    with open(
            os.path.join(folder_to_save_output_dict,  'mention_entities_counter_wikidata.pickle'),
            'wb') as handle:
        pickle.dump(mention_entities_counter, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # remove the temporary folder
    shutil.rmtree(tmp_folder_path)
    # remove additional created files
    # current_dir = os.getcwd()
    # os.remove(os.path.join(current_dir, ))