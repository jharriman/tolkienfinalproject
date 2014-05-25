#! /usr/bin/env python
import sys
import nltk
import copy
from nltk.corpus import wordnet as wn
from nltk.tag.simplify import simplify_wsj_tag
from nltk.stem.wordnet import WordNetLemmatizer

def util_group_tup(seq, sep):
    tripped = False
    g = []
    for elm in seq:
        if not tripped:
            if elm[1] == sep:
                yield g
                yield [elm]
                g = []
                tripped = True
            else:
                g.append(elm)
        else:
            g.append(elm)
    yield g

class tParse:
    def __init__(self):
        self.lmtz = WordNetLemmatizer()
        self.names = dict()
        give = wn.synsets("give")
        self.transfer1 = self.makeSynList(give, [1,3,4,5,6,8,12,14,15,19,21,22,20,24,25,29,40]) # Note, remember that feed is in here

        app = wn.synsets("apply")
        being = wn.synsets("be")
        self.apply1 = self.makeSynList(app).union(self.makeSynList(being))

    def printSyns(self, word):
        synsets = wn.synsets(word)
        i = 0
        for s in synsets:
            print i, " Def: ", s.definition
            for l in s.lemmas:
                print "\t ", i, " ", l.name
            i += 1

    def makeSynList(self, synsets, defs=None):
        syns = set()
        if defs == None:
            for s in synsets:
                for l in s.lemmas:
                    syns.add(l.name)
        else:
            for d in defs:
                s = synsets[d]
                for l in s.lemmas:
                    syns.add(l.name)
        return syns
    
    def tag(self, sentence):
        tokens = nltk.word_tokenize(sentence)
        tagged = nltk.pos_tag(tokens)
        simpl_tagged = [(word, simplify_wsj_tag(tag)) for word, tag in tagged]
        return simpl_tagged

    def sepIntClauses(self, tagged):
        topList = []
        curList = []
        for tag in tagged:
            if tag[1] in (".", ":"):
                if curList != []:
                    topList.append(curList)
                    curList = []
            else:
                curList.append(tag)
        topList.append(curList)
        return topList

    def addToNames(self, name, nameDict, player):
        if not name:
            if not nameDict:
                return player
            else:
                print "ERROR, player already in database"
        else:
            res = nameDict.get(name[0], None)
            if res is None:
                nameDict[name[0]] = self.addToNames(name[1:], dict(), player)
            elif type(res) is str:
                nameDict[name[0]] = self.addToNames(name[1:], {"^" : res}, player)
            else:
                nameDict[name[0]] = self.addToNames(name[1:], res, player)
            return nameDict

    def addPlayer(self, name):
        p = player(name)
        nameList = name.split(" ")
        self.names = self.addToNames(nameList, self.names, p)

    def getPlayerByName(self, name):
        split = name.split(" ")
        tmp = self.names
        try: 
            while tmp:
                if type(tmp) is dict:
                    tmp = tmp[split[0]]
                    split = split[1:]
                else:
                    return tmp
        except:
            return None
    
    def findKnownNames(self, taggedList, names, isSubj):
        for i in range(0, len(taggedList)):
            taggedWord = taggedList[i]
            # Check if tagged word is a pronoun
            if taggedWord[1] in ["PRO"]:
                if taggedWord[0] in ["him", "her", "their"]:
                    if self.objectEnv:
                        return self.objectEnv
                elif taggedWord[0] in ["he", "she", "they"]:
                    if self.subjEnv:
                        return self.subjEnv

            # If not a pronoun, look for the rest of the name
            res = names.get(taggedList[i][0], None)
            t = type(res)
            if t is dict:
                return self.findKnownNames(taggedList[1:], res, isSubj)
            elif res is None: # Done looking here, will check the next tagged word
                continue
            else:
                if isSubj:
                    self.subjEnv = res
                else:
                    self.objectEnv = res
                return res
        return "ERROR!"

    def removePFromTagged(self, p, taggedList):
        print "p: ", p
        print "taggedList", taggedList
        newList = list()
        plist = copy.deepcopy(p.name)
        for x,y in taggedList:
            if x not in plist:
                newList.append((x,y))
            else:
                plist.remove(x)
        return newList

    def findObject(self, taggedList):
        print taggedList
        for i in range(0, len(taggedList)):
            if taggedList[i][1] == "DET":
                adjectives = list()
                newTL = taggedList[i+1:]
                for j in range(0, len(newTL)):
                    if newTL[j][1] == "ADJ":
                        print newTL[j][1]
                        adjectives.append(newTL[j][0])
                    elif newTL[j][1] == "N" or newTL[j][1] == "NP": 
                        # We need to hande multiple subjects, so we will need to use an AND construct
                        objectName = newTL[j][0]
                        for k in range (0, len(newTL) - 1):
                            if newTL[k][1] is "NP" or newTL[k][1] is "DET":
                                objectName += " " + newTL[k][0]
                            elif newTL[k][1] is "VN":
                                continue #TODO! Subclass of objects (named objects)
                            else:
                                break
                        o = obj(objectName)
                        o.setAttributes(adjectives)
                        return o

    def findAttrs(self, taggedList, obj):
        adjs = list()
        for w in taggedList:
             if w[1] in ["ADJ", "ADV", "V"]: # Is the V being used here right?
                 adjs.append(w[0])
        return adjs

                
    def tokenize(self, taggedList):
        threeSplit = list(util_group_tup(taggedList, 'V')) 
        # We're expecting the clause to come in three parts (subject/verb/objects). This is a style choice for us.
        print threeSplit
        action = self.lmtz.lemmatize(threeSplit[1][0][0], 'v') 
        print action
        # Lemmatize breaks the word down into its stem, this lets us collapse the tenses
        if action in self.transfer1: #For now using the temporary transference 'library'
            print "Transferrence!"
            print "Finding giver"
            p1 = self.findKnownNames(threeSplit[0], self.names, True)
            print "Finding receiver"
            p2 = self.findKnownNames(threeSplit[2], self.names, False)
            print p2.name
            rest2 = self.removePFromTagged(p2, threeSplit[2])
            print rest2
            o = self.findObject(rest2)
            # Here there be logic for if the giver is "able" to give the object to another player.
            self.transfer(p1, p2, o)
        if action in self.apply1:
            print "Application"
            p1 = self.findKnownNames(threeSplit[0], self.names, True)
            print p1.name
            p1.setAttributes(self.findAttrs(threeSplit[2], p1))
            

    def transfer(self, sender, receiver, gift):
        if sender.extractItem(gift):
            receiver.addItem(gift)
            print receiver.inventory

    def interpret(self, sentence):
        # TODO! The tagger only works when we give it a single sentence, so we need to break our input down
        # if it is longer than a sentence.
        tagged = self.tag(sentence)
        print tagged
        clauses = self.sepIntClauses(tagged)
        self.tokenize(clauses[0])

class player:
    def __init__(self, name):
        self.raw_name = name
        self.name = name.split(" ")
        self.inventory = list()

    def extractItem(self, toRemove): 
        for item in self.inventory: 
            if item.name is toRemove.name:
                self.inventory.remove(item)
                return True
        print "Item is not in inventory"
        return False

    def setAttributes(self, adjs):
        self.attributes = adjs

    def printAttributes(self):
        print self.attributes

    def addItem(self, item):
        self.inventory.append(item)
        
class obj:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        printable = "Obj: " + self.name + "; "
        for adj in self.attributes:
            printable += adj + ", "
        return printable
    
    def setAttributes(self, adjectives):
        self.attributes = adjectives

if __name__ == "__main__":
    go = tParse()
    while(True):
        line = raw_input("> ")
        go.interpret(line)
