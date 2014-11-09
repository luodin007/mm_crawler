# -*- coding:utf-8 -*-  
#author: luoding
#blog:www.nwber.com
#E-mail: luoding@nwber.com

from PIL import Image

class ImageHash:
    """ 
    计算图片的感知哈希，得到8位(默认)十六进制字符串
    感知哈希值可作为判断图片相似性的依据
    相同则哈希值相同，也可通过计算两个哈希值之间的汉明距离来得到图片相似程度
    @hash_size 哈希值的长度，默认为8位
    """
    def __init__(self,hash_size = 8):
        self.hash_size = hash_size
        
    def image_hash(self, path):
        """ 计算感知哈希值，path为图片地址 """
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
        """ 两个字符串之间的汉明距离 """
        if len(s1) != len(s2):
            raise ValueError("Undefined for sequences of unequal length")
        return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))
