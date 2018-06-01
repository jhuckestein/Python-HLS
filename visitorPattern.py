##Visitor pattern as used in class at Penn State "We Are!"
##
##This pattern allows different operations to be performed
##on the elements in a heirarchical object structure.  Crucially
##though, it allows you to define a new set of operations 
##without changing the classes of the elements on which it
##operates and thus provides a nice way of separating your
##data and algorithms.
##
##The Visitor pattern allows you to extend the interface of the 
##primary type by creating a separate class heirarchy of type
##Visitor to virtualize the operations performed upon the 
##primary type.  The objects of the primary type simply 
##"accept" the visitor, then call the visitor's dynamically
##bound member functions.
##
################################################################

from __future__ import generators
import random


#The Flower object is where all the magic of polymorphism happens.
#This has the basic method algorithms that can be performed.
################################################################
# The Flower hierarchy cannot be changed:
class Flower(object):
    def accept(self, visitor):
        visitor.visit(self)
    def pollinate(self, pollinator):
        print(self, "pollinated by", pollinator)
    def eat(self, eater):
        print(self, "eaten by", eater)
    def __str__(self):
        return self.__class__.__name__

#The flower subclasses specify what kind of flower is visited
class Gladiolus(Flower): pass
class Runuculus(Flower): pass
class Chrysanthemum(Flower): pass

class Visitor:
    def __str__(self):
        return self.__class__.__name__

#The bug is the visitor, and then has two categories
class Bug(Visitor): pass
class Pollinator(Bug): pass
class Predator(Bug): pass

#The two categories are broken down into three instance
#types, and these visitors specify what methods they will
#invoke on the flower they visit via polymorphism.
#########################################################
# Add the ability to do "Bee" activities:
class Bee(Pollinator):
    def visit(self, flower):
        flower.pollinate(self)

# Add the ability to do "Fly" activities:
class Fly(Pollinator):
    def visit(self, flower):
        flower.pollinate(self)

# Add the ability to do "Worm" activities:
class Worm(Predator):
    def visit(self, flower):
        flower.eat(self)

def flowerGen(n):                    ##This generates random flowers from the
    flwrs = Flower.__subclasses__()  ##three subclasses of flowers.  The sub
    for i in range(n):               ##classes are what are really visited.
        yield random.choice(flwrs)()

# It's almost as if I had a method to Perform
# various "Bug" operations on all Flowers:
bee = Bee()
fly = Fly()
worm = Worm()
for flower in flowerGen(10):
    flower.accept(bee)
    flower.accept(fly)
    flower.accept(worm)
