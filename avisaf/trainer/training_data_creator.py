#!/usr/bin/env python3

import sys
from spacy.matcher import PhraseMatcher, Matcher
from util.data_extractor import get_narratives, get_entities
from util.indexing import get_spans_indexes
import util.training_data_build as train
import spacy
import json
import os

sys.path.append('/home/viktor/Documents/avisaf_ner/avisaf')
MAN_TRAINING_DATA_FILE_PATH = os.path.expanduser('~/Documents/avisaf_ner/data_files/man_annotated_data.json')


def annotate_auto(keywords_file_path,
                  label_text,
                  model='en_core_web_md',
                  tr_src_file=None,
                  extract_texts=False,
                  use_phrasematcher=True,
                  save=False,
                  verbose=False):
    """
    Semi-automatic annotation tool. The function takes a file which should 
    contain a list of keywords to be matched.
    
    :type keywords_file_path:   str
    :param keywords_file_path:  String representing a path to the file with words to be matched (glossary etc).
    :type label_text:           str
    :param label_text:          The text of the label of an entity.
    :type model:                str
    :param model:               Model to be loaded to spaCy.
    :type tr_src_file:          str
    :param tr_src_file:         Training data source file path.
    :type extract_texts:        bool
    :param extract_texts:       Flag indicating whether new texts should be searched for.
    :type use_phrasematcher:    bool
    :param use_phrasematcher:   Flag indicating whether Matcher or PhraseMatcher spaCy object is used.
    :type save:                 bool
    :param save:                Flag indicating whether the data should be saved.
    :type verbose:              bool
    :param verbose:             Flag indicating verbose printing.
    :return:
    """
    # result list
    tr_data_overlaps = []

    if extract_texts or tr_src_file is None:
        # get testing texts
        texts = list(get_narratives())  # file_path is None
        entities = None
    else:
        with open(tr_src_file, mode='r') as tr_data_file:
            # load the file containing the list of training ('text string', entity dict) tuples
            tr_data = json.load(tr_data_file)
            texts = [text for text, _ in tr_data]
            entities = [ents for _, ents in tr_data]

    # create NLP analyzer object of the model
    nlp = spacy.load(model)
    with open(keywords_file_path, mode='r') as keys_file:
        patterns = json.load(keys_file)  # phrase/patterns to be matched

    if use_phrasematcher:
        # create PhraseMatcher object
        matcher = PhraseMatcher(nlp.vocab, validate=True)
        # process the keys and store their values in the patterns list
        keywords = list(nlp.pipe(patterns))
        # add all patterns to the matcher
        matcher.add(label_text, keywords)
    else:
        # create Matcher object
        matcher = Matcher(nlp.vocab, validate=True)
        matcher.add(label_text, patterns)

    print(f'Using {matcher}', flush=verbose)
    print(*patterns, sep='\n', flush=verbose)
    matcher1 = Matcher(nlp.vocab)
    # matcher1.add("LETISKO",
    #    [[{"LOWER": {"IN": ["runway", "rwy"]}, "OP": "?"}, {"TEXT": {"REGEX": "(0[1-9]|[1-2][0-9]|3[0-6])(L|C|R)?"}}]])

    for doc in nlp.pipe(texts, batch_size=50):
        matches = matcher(doc) + matcher1(doc)
        matched_spans = [doc[start:end] for match_id, start, end in matches]
        print(f'Doc index: {texts.index(doc.text)}', f'Matched spans: {matched_spans}', flush=verbose)
        new_entities = [(span.start_char, span.end_char, label_text) for span in matched_spans]
        tr_example = (doc.text, {"entities": new_entities})
        if entities is not None:
            doc_index = texts.index(doc.text)
            old_entities = list(entities[doc_index]["entities"])
            new_entities = new_entities + old_entities
            tr_example = (doc.text, {"entities": new_entities})

        tr_data_overlaps.append(tr_example)

    TRAINING_DATA = []  # list will contain training data without overlaps

    for text, annotations in tr_data_overlaps:
        new_annotations = train.remove_overlaps_from_dict(annotations)
        TRAINING_DATA.append((text, {"entities": new_annotations}))

    if save and tr_src_file is not None:
        with open(tr_src_file, mode='w') as file:
            json.dump(TRAINING_DATA, file)

    else:
        print(*TRAINING_DATA, sep='\n')

    return TRAINING_DATA


def annotate_man(labels,
                 file_path,
                 lines,
                 start_index=0,
                 save=False):
    """
    Manual text annotation tool. A set of 'lines' texts starting with start_index
    is progressively printed in order to be annotated by labels.

    :type labels:       list
    :param labels:      List of available entity labels.
    :type file_path:    str
    :param file_path:   The path to the file containing texts to be annotated.
                        If None, then a user can write own sentences and annotate them.
    :type lines:        int
    :param lines:       The number of texts to be annotated (1 text = 1 line).
    :type start_index:  int
    :param start_index: The index of the first text to be annotated.
    :type save:         bool
    :param save:        Flag indicating whether the result of the annotation
                        should be saved.

    :return:            List of texts and its annotations.
    """

    if file_path is not None:
        texts = list(get_narratives(lines=lines, file_path=file_path, start_index=start_index))
    else:
        texts = train.write_sentences()

    result = []

    for text in texts:
        ent_labels = []
        print(text)
        print()  # print an empty line
        words = input('Write all words you want to annotate (separated by a comma): ')
        spans = set([word.strip() for word in words.split(',') if word.strip()])

        if not spans:
            new_entry = (text, {"entities": []})
            result.append(new_entry)
        else:
            found_occurs = get_spans_indexes(text, spans)  # find positions of "spans" string list items in the text
            for occur_dict in found_occurs:
                key = list(occur_dict.keys())[0]  # only the first key is desired
                matches = occur_dict[key]
                label = input(f'Label \'{key}\' with an item from: {list(enumerate(labels))}: ').upper()
                if label == 'NONE':  # when there is no suitable label in the list
                    continue
                if label.isdigit():
                    ent_labels += [(start, end, labels[int(label)]) for start, end in matches]  # create the tuple
                else:
                    # same as above, but entity label text is directly taken
                    ent_labels += [(start, end, label) for start, end in matches]

            new_entry = (text, {"entities": ent_labels})
            result.append(new_entry)
        print()  # print an empty line

        if save:
            # rewrite the content of the file
            with open(os.path.expanduser(MAN_TRAINING_DATA_FILE_PATH), mode='r') as file:
                old_content = json.load(file)

            with open(os.path.expanduser(MAN_TRAINING_DATA_FILE_PATH), mode='w') as file:
                old_content.append(new_entry)
                json.dump(old_content, file)

            train.pretty_print_training_data(MAN_TRAINING_DATA_FILE_PATH)

    return result


if __name__ == '__main__':
    path_arg = sys.argv[1]
    first_text_idx = int(sys.argv[2])
    ents = get_entities()
    print(annotate_man(labels=ents, file_path=path_arg, start_index=first_text_idx, lines=5))
    train.pretty_print_training_data(MAN_TRAINING_DATA_FILE_PATH)

    annotate_auto("/home/viktor/Documents/avisaf_ner/data_files/altitude_list.json",
                           "ALTITUDE",
                  tr_src_file="/home/viktor/Documents/avisaf_ner/data_files/auto_annotated_data.json",
                  use_phrasematcher=False)
