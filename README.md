# ED_Data
Repo for unified train and test corpus for ED

The training corpus is derived from the [Kensho Derived Wikimedia Dataset](https://www.kaggle.com/datasets/kenshoresearch/kensho-derived-wikimedia-data) 
(licence [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)). We used the "link_annotated_text.jsonl" that provides wikipedia pages
divided into sections. Each section consists of a name, a text and wikipedia hyperlinks specified by offset, length and wikipedia id of the 
referenced page. 

The test corpora are the test split of the [AIDA CoNLL-YAGO](https://www.mpi-inf.mpg.de/departments/databases-and-information-systems/research/ambiverse-nlu/aida/downloads) dataset (AIDA-b), 
the [Reddit EL corpus](https://doi.org/10.5281/zenodo.3970806), the [Tweeki EL corpus](https://ucinlp.github.io/tweeki/), the [ShadowLink dataset](https://huggingface.co/datasets/vera-pro/ShadowLink) and 
the [WNED-WIKI/WNED-CWEB](https://github.com/lephong/mulrel-nel) corpora processed by [Le and Titov, 2018](https://aclanthology.org/P18-1148/).
