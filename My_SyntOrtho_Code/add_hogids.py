import lxml.etree as etree
import os
import argparse
import collections


NS = {'ns': "http://orthoXML.org/2011/"}


def get_toplevel_groups(root):
    xquery = ".//ns:groups/ns:orthologGroup"
    return root.findall(xquery, namespaces=NS)


def is_ortholog_group(node):
    return node.tag == '{{{ns}}}orthologGroup'.format(**NS)


def is_paralog_group(node):
    return node.tag == '{{{ns}}}paralogGroup'.format(**NS)


def paralog_id_encoder(prefix, nr):
    """encode the paralogGroups at the same level, e.g. 1a, 1b, 1c
    for 3 paralogGroups next to each other. the nr argument
    identifies the individual indices of those 3 paralogGroups."""
    letters = []
    while nr // 26 > 0:
        letters.append(chr(97 + (nr % 26)))
        nr = nr // 26 - 1
    letters.append(chr(97 + (nr % 26)))
    return prefix + ''.join(letters[::-1])  # letters were in reverse order


class LevelDuplCounter(object):
    def __init__(self):
        self.duplCounts = collections.defaultdict(int)

    def reset(self):
        self.duplCounts.clear()

    def next_id(self, level):
        self.duplCounts[level] += 1
        return self.duplCounts[level]


class OrthoXmlIdAdder(object):
    def __init__(self, infile):
        self.doc = etree.parse(infile)
        self.level_counter = LevelDuplCounter()

    def add_hog_ids(self):
        for k, group in enumerate(get_toplevel_groups(self.doc.getroot())):
            self.level_counter.reset()
            self._annotateGroupR(group, group.get('id', str(k)))

    def _annotateGroupR(self, node, id, idx=0):
        """create the og attributes at the orthologGroup elements
        according to the naming schema of LOFT. ParalogGroup elements
        do not get own attributes (not possible in the xml schema),
        but propagate their sub-names for the subsequent orthologGroup
        elements."""
        if is_ortholog_group(node):
            node.set('id', id)
            for child in list(node):
                self._annotateGroupR(child, id, idx)
        elif is_paralog_group(node):
            idx += 1
            next_id = "{}.{}".format(id, self.level_counter.next_id(idx))
            for i, child in enumerate(list(node)):
                self._annotateGroupR(child, paralog_id_encoder(next_id, i), idx)

    def write(self, out):
        self.doc.write(out, pretty_print=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds LOFT ids to an orthoxml file")
    parser.add_argument('--out', help="output filename. defaults to stdout")
    parser.add_argument('input', help="input orthoxml filename")

    conf = parser.parse_args()
    adder = OrthoXmlIdAdder(conf.input)
    adder.add_hog_ids()
    adder.write(conf.out)