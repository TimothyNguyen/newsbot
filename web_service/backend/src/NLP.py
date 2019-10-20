import requests
from newsapi import NewsApiClient as c
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyser = SentimentIntensityAnalyzer()
import spacy


# coding: utf-8

import urllib
import nltk
import rake_nltk
import requests
from bs4 import BeautifulSoup

# rake_nltk is the library needed for keyword extraction
from rake_nltk import Metric, Rake

import operator
from nltk.corpus import stopwords
set(stopwords.words('english'))
from nltk.tokenize import word_tokenize, sent_tokenize

# Synonyms e.g., mother, mom, and mommy should be treated the same way
# For this, use a Stemmer - an algorithm to bring words to its root word.
from nltk.stem import PorterStemmer
nlp = spacy.load('en_core_web_sm')

class NLP:

    def __init__(self, html):
        self.html = html
        self.text = ''
        self.title = ''
        self.h1_tags = ''

        # Create dictionary that will hold frequency of words in text - not including stop words
        self.freqTable = dict()

        # Stemmer (puts pluralized, tensed words/verbs into their root form eg: agreed -> agree, flies -> fli)
        self.ps = PorterStemmer()

        self.summary = ''

        self.sentenceValue = dict()

        self.stopWords = set(stopwords.words('english'))
        self.createSummary()


    def removeSpecialCharacters(self):
        for char in self.text:
            if char in " ?.!/;:":
                self.text.replace(char,'')


    def tally(self, words):
        for word in words:
            word = word.lower()
            if word in self.stopWords:
                continue
            # Pass every word by the stemmer before adding it to our freqTable
            # It is important to stem every word when going through each sentence before adding the score of the words in it.
            word = self.ps.stem(word)
            if word in self.freqTable:
                self.freqTable[word] += 1
            else:
                self.freqTable[word] = 1

    def clean(self):
        self.beautifyText()

        # Remove all special characters
        self.removeSpecialCharacters()


    def scoreSentences(self, sentences):
        # Go through every sentence and give it a score depending on the words it has while also dividing the value by the
        # length of the sentence to avoid giving more emphasis to longer sentences
        for sentence in sentences:
            sentence_length = len(sentence.split(' '))
            for key,value in self.freqTable.items():
                if key in sentence.lower():
                    if sentence[:12] in self.sentenceValue:
                        self.sentenceValue[sentence[:12]] += value / sentence_length
                    else:
                        self.sentenceValue[sentence[:12]] = value / sentence_length

    def getAverageScore(self):
        sumValues = 0
        for sentence in self.sentenceValue:
            sumValues += self.sentenceValue[sentence]

        # Average value of a sentence from original text
        return int(sumValues / len(self.sentenceValue))


    def beautifyText(self):
        soup = BeautifulSoup(self.html, "html.parser")

        # Get all the text in <p> tags on the page
        self.title = soup.title.text
        self.h1_tags = soup.findAll("h1")
        text = ''
        h1_text = ''
        p_tags = soup.findAll("p")
        for r in p_tags:
            tag = BeautifulSoup(str(r), "html.parser")
            for a in tag.findAll('a'):
                a.replaceWithChildren()
            text = text + tag.text + '\n'

        for h1 in self.h1_tags:
            tag = BeautifulSoup(str(h1), "html.parser")
            for a in tag.findAll('a'):
                a.replaceWithChildren()
            h1_text = h1_text + tag.text + '\n'

        self.text = text

        self.h1_text = h1_text


    def createSummary(self):
        try:
            # Clean up the text
            self.clean()

            # Tokenize
            words = word_tokenize(self.text)

            # Tally occurrences into freqTable
            self.tally(words)

            # Sentence tokenize
            sentences = sent_tokenize(self.text)
            self.scoreSentences(sentences)

            # What to compare each sentence's values to? The average of all the sentences
            average = self.getAverageScore()

            # Apply sentences in order into the summary
            for sentence in sentences:
                if sentence[:12] in self.sentenceValue and self.sentenceValue[sentence[:12]] > (1.5 * average):
                    self.summary +=  " " + sentence

            theList = []
            for sentence in sentences:
                score = analyser.polarity_scores(sentence)['compound']
                theList.append([sentence, score])
                r = buildTree(sentence)
                printTree(r, "ROOT")
                print("end\n")

        except Exception as e:
            print(str(e))
            raise e

class sTreeNode():
    def __init__(self, n, is_entity):
        self.is_entity = is_entity
        self.root = n
        self.p_children = list(n.children)
        self.msg = None
        self.text = n.text
        self.subj = None
        self.obj = None
        if not is_entity:
            self.add_subj()
            self.add_obj()

    def add_subj(self):
        for ent in self.root.children:
            if ent.dep_ == "nsubj" or ent.dep_ == "nsubjpass":
                self.subj = sTreeNode(ent, True)

    def add_obj(self):
        obj_exists = False
        if (return_of_type("acomp", self.p_children) != -1):
            self.text += " " + self.p_children[return_of_type("acomp", self.p_children)].text
        if (return_of_type("xcomp", self.p_children) != -1):
            self.text += " " + self.p_children[return_of_type("xcomp", self.p_children)].text
            self.p_children += list(self.p_children[return_of_type("xcomp", self.p_children)].children)
        if return_of_type("dobj", self.p_children) != -1:
            self.obj = sTreeNode(self.p_children[return_of_type("dobj", self.p_children)], True)
        if return_of_type("prep", self.p_children) != -1 and return_of_type("pobj", list(
                self.p_children[return_of_type("prep", self.p_children)].children)) != -1:
            for child in self.p_children[return_of_type("prep", self.p_children)].children:
                if child.dep_ == "pobj":
                    self.obj = sTreeNode(child, True)
        if (return_of_type("ccomp", self.p_children) != -1):
            if not obj_exists:
                self.obj = sTreeNode(self.p_children[return_of_type("ccomp", self.p_children)], False)
            else:
                self.msg = sTreeNode(self.p_children[return_of_type("ccomp", self.p_children)], False)


def chunkify(curr, doc):
    if curr != None:
        if curr.is_entity == True:
            for chunk in doc.noun_chunks:
                if curr.text == chunk.root.text:
                    curr.text = chunk.text
        chunkify(curr.subj, doc)
        chunkify(curr.obj, doc)
        chunkify(curr.msg, doc)


def return_of_type(dep, lis):
    for i, child in enumerate(lis):
        if child.dep_ == dep:
            return i
    return -1


def buildTree(s):
    doc = nlp(s)
    root = None
    for ent in doc:
        if ent.dep_ == "ROOT":
            root = sTreeNode(ent, False)
            chunkify(root, doc)
    return root


def printTree(n, s):
    if (n != None):
        printTree(n.subj, "SUBJ")
        score = analyser.polarity_scores(n.text)
        print(n.text, "(" + str(score['compound']) + ")", s, "->", end="")
        printTree(n.obj, "OBJ")
        printTree(n.msg, "MSG")



# Test url:
#url = 'https://www.huffingtonpost.ca/entry/melania-trump-child-detainees_us_5b2bea31e4b0040e2740f172'
url = 'https://ca.reuters.com/article/topNews/idCAKCN1QI5JY-OCATP'



# Now that the main webpage text is extracted from the html, pass it to Rake to extract keywords

#r = Rake() # Uses stopwords for english from NLTK, and all puntuation characters.
#r.extract_keywords_from_text(text)
#r.get_ranked_phrases() # To get keyword phrases ranked highest to lowest.



# Extract all relevant text from page's html (ie try to avoid ads and other noise)

html = requests.get(url).text

soup = BeautifulSoup(html, "html.parser")

# Get all the text in <p> tags on the page
title = soup.title.text
h1_tags = soup.findAll("h1")
text = ''
h1_text = ''
p_tags = soup.findAll("p")
for r in p_tags:
    tag = BeautifulSoup(str(r), "html.parser")
    for a in tag.findAll('a'):
        a.replaceWithChildren()
    text = text + tag.text + '\n'

for h1 in h1_tags:
    tag = BeautifulSoup(str(h1), "html.parser")
    for a in tag.findAll('a'):
        a.replaceWithChildren()
    h1_text = h1_text + tag.text + '\n'

nlp = NLP(text)





"""
#Test the stemmer on various pluralised words.

stemmer = PorterStemmer()
plurals = ['caresses', 'flies', 'dies', 'mules', 'denied','died', 'agreed', 'owned', 'humbled', 'sized','meeting',\
           'stating', 'siezing', 'itemization','sensational', 'traditional', 'reference', 'colonizer','plotted']
singles = [stemmer.stem(plural) for plural in plurals]
print(' '.join(singles))

"""





# TODO:
# change language to be dynamic (in constructor)
# Want to report the authors of the article (if available)
# Want to ignore advertisements on pages where there are many

