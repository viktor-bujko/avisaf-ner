#!/usr/bin/env python3

import json
import os

from .data_extractor import get_training_data


def sort_annotations(file_path):
    """
    Function that sorts the (start_index, end_index, label) tuples based by
    their position in the given text. Sorting is done for every line of a JSON
    training data file.

    :type file_path:  file
    :param file_path: Path of the JSON file containing the list of
                      (text, entities) tuples, which will have entities sorted.
    """

    training_data = get_training_data(file_path)
    sorted_training_data = []

    for text, annotation in training_data:
        annot_list = annotation["entities"]  # get entities list from "entities" key in the annotation dictionary
        sorted_list = sorted(annot_list, key=lambda tple: tple[0])  # sort entities by the start_index
        sorted_training_data.append((text, {"entities": sorted_list}))  # recreate new, sorted dictionary

    with open(file_path, mode='w') as file:     # write the result to the same file
        json.dump(sorted_training_data, file)

    pretty_print_training_data(file_path)       # pretty print the file


def remove_overlaps_from_dict(annotations_dict):
    """
    Removes overlapping annotations from the annotations_dict['entities'] list
    of (start_index, end_index, label) tuples.
    :param annotations_dict: The dictionary containing the annotations list under
                             'entities' key.
    :return:                 The list of new annotations without overlaps.
    """

    entities_list = annotations_dict['entities']  # get entities list from "entities" key in the annotation dictionary
    remove_list = []
    for entity_triplet in entities_list:
        index = list(entities_list).index(entity_triplet)

        # if the entity_triplet is NOT the last item of the list
        if index < len(entities_list) - 1:
            next_triplet = entities_list[index + 1]  # find next tuple
            triplet_to_remove = overlap_between(entity_triplet, next_triplet)
            if triplet_to_remove is not None:  # an overlap detected and resolved
                remove_list.append(triplet_to_remove)

    new_annotations = [entity for entity in entities_list if entity not in remove_list]

    return new_annotations


def remove_overlaps_from_file(file_path):
    """
    The function removes overlapping annotations from all the (text, annotations)
    tuples in JSON file specified in the file_path argument.

    :type file_path:    file
    :param file_path:   The path to the JSON file which will have all overlapping annotations removed.
    :return:            Returns the content of the JSON file in the file_path arg without overlapping annotations.
    """

    sort_annotations(file_path)  # sorting annotations list for simpler overlap detection
    training_data = get_training_data(file_path)
    result = []

    for text, annotations in training_data:
        new_annotations = remove_overlaps_from_dict(annotations)
        result.append((text, {"entities": new_annotations}))  # recreate new (text, annotations) tuple

    with open(file_path, mode='w') as file:  # update the file
        json.dump(result, file)

    pretty_print_training_data(file_path)

    return result


def overlap_between(entity_triplet, next_triplet):
    """
    Detects whether there is an overlap between two triplets in the given text.
    In such a case, shorter triplet is removed.

    :type entity_triplet:  tuple
    :param entity_triplet: First  (start_index, end_index, label) entity descriptor.
    :type next_triplet:    tuple
    :param next_triplet:   Second (start_index, end_index, label) entity descriptor.
    :return:               Returns the triplet to be removed - the one which
                           represents a shorter part of the text.
    """
    entity_start = entity_triplet[0]  # entity start_index
    entity_end = entity_triplet[1]    # entity end_index

    next_start = next_triplet[0]      # next entity start_index
    next_end = next_triplet[1]        # next entity end_index
    x = set(range(entity_start, entity_end))
    y = range(next_start, next_end)

    # if an overlap is detected between two tuples.
    if x.intersection(y):
        # return shorter of the triplets - usually the one which is less correct
        if (entity_end - entity_start) >= (next_end - next_start):
            return next_triplet
        else:
            return entity_triplet
    else:
        return None


def pretty_print_training_data(path):
    """
    Prints each tuple object of the document in a new line instead of a single
    very long line.

    :type path:  file
    :param path: The path of the file to be rewritten.
    """

    with open(os.path.expanduser(path), mode='r') as file:
        content = json.loads(file.read())

    with open(os.path.expanduser(path), mode='w') as file:
        file.write('[')
        for i, entry in enumerate(content):
            json.dump(entry, file)
            if i != len(content) - 1:
                file.write(',\n')
            else:
                file.write('\n')
        file.write(']')


def write_sentences():
    """
    A loop which prompts a user to input a sentence which will be annotated
    later. The function end when string 'None' is detected
    :return: The list of user-written sentences.
    """
    result = []
    sentence = input('Write a sentence: ')

    while sentence != 'None':
        result.append(sentence)
        sentence = input('Write a sentence: ')

    return result
