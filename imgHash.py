'''
Created on Nov 2, 2014

@author: luoding
'''

from PIL import Image

class ImageHash:
    def __init__(self,hash_size = 8):
        self.hash_size = hash_size
        
    def image_hash(self, path):
        im = Image.open(path)
        im= im.resize((self.hash_size, self.hash_size), Image.ANTIALIAS).convert('L')
        avg = reduce(lambda x, y: x + y, im.getdata()) / (self.hash_size*self.hash_size)
        difference = map(lambda i: 0 if i < avg else 1, im.getdata())
    #     for col in range(self.hash_size-1):
    #         print h[col:col+self.hash_size]
        decimal_value = 0
        hex_string = []
        for index, value in enumerate(difference):
            if value:
                decimal_value += 2**(index % 8)
            if (index % 8) == 7:
                hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
                decimal_value = 0
     
        return ''.join(hex_string)
    
    def hamming_distance(self, s1, s2):
        #Return the Hamming distance between equal-length sequences
        if len(s1) != len(s2):
            raise ValueError("Undefined for sequences of unequal length")
        return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))

lists =[]
for i in range(0,8):
    s1 = ImageHash.image_hash('/home/luoding/workspace/crawler/crawler/'+str(i)+'.jpg')
    s2 = ImageHash.image_hash('/home/luoding/workspace/crawler/crawler/'+str(i+1)+'.jpg')
    lists.append(ImageHash.hamming_distance(s1, s2))
lists.sort()   
print lists

