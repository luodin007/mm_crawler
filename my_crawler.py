# -*- coding:utf-8 -*-  
#author: luoding
#blog:www.nwber.com
#E-mail: luoding@nwber.com

from threading import Thread
import urllib 
import urllib2 
from Queue import Queue  
from BeautifulSoup import * 
import cookielib
import StringIO
import gzip
import hashlib
import os
from PIL import Image
import time
import random

pass_url = set()
pass_img = set()
pass_hash = set()

url_queue = Queue()
img_queue = Queue()

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

class URLScanner(Thread):
    def __init__(self, threadID, timeout,web_url):
        Thread.__init__(self)
        self.threadID = threadID
        self.timeout = timeout
        self.web_url = web_url
    
    
    def run(self):
        while True:
            pre_url = url_queue.get()
            self.process(pre_url)
            
    def is_exit(self, pre_url):
        if pre_url in pass_url:
            return True
        else:
            pass_url.add(pre_url)
            return False
    
    def process(self, pre_url):
        try:
            request = urllib2.Request(pre_url)
            request.add_header('User-Agent', '"Mozilla/4.0 (compatible; MSIE 5.0; Windows NT; DigExt)')
            request.add_header('Accept-encoding', 'gzip')
            opener = urllib2.build_opener()
            html = opener.open(request, timeout=self.timeout)
            isGzip = html.headers.get('Content-Encoding')
            if isGzip :
                compresseddata = html.read()
                compressedstream = StringIO.StringIO(compresseddata)
                gzipper = gzip.GzipFile(fileobj=compressedstream)
                html_doc = gzipper.read()
            else:
                html_doc = html.read()
            #html_doc = urllib2.urlopen(request, timeout=self.timeout).read() 
            url_list = self.choice_href(html_doc)
            for url in url_list:
                if not self.is_exit( url):
                    print 'get url   :  '+url
                    pass_url.add(url)
                    url_queue.put(url)
        except:
            pass
            
        
    def choice_href(self, html_doc):
        """ 寻找当前页面所有可用链接，返回可用且在目标网站的链接数组 """
        page_urls = []
        soup = BeautifulSoup(html_doc)
        for href in soup.findAll('a'):
            href_str = href.get('href')
            if href_str: 
                if href_str.startswith('http'):     #判断是否为一个完整链接
                    if  href_str.startswith(self.web_url):  #判断是否为目标网站的链接
                        if href_str not in page_urls:   #判断该链接是否已经爬取
                            page_urls.append(href_str) 
                    else:
                        continue
                    
                else: #对缩写链接进行补全
                    if self.web_url + href_str not in page_urls:
                        page_urls.append(self.web_url +'/'+ href_str)
             
        return page_urls     


class IMGScanner(Thread):
    def __init__(self, threadID, timeout, web_url):
        Thread.__init__(self)
        self.threadID = threadID
        self.timeout = timeout
        self.web_url = web_url
    
    def run(self):
        while True:
            pre_url = url_queue.get()
            self.process(pre_url)
            
    def is_exit(self, pre_url):
        if pre_url in pass_img:
            return True
        else:
            pass_img.add(pre_url)
            return False
    
    def process(self, pre_url):
        try:
            request = urllib2.Request(pre_url)
            request.add_header('User-Agent', '"Mozilla/4.0 (compatible; MSIE 5.0; Windows NT; DigExt)')
            request.add_header('Accept-encoding', 'gzip')
            opener = urllib2.build_opener()
            html = opener.open(request, timeout=self.timeout)
            isGzip = html.headers.get('Content-Encoding')
            if isGzip :
                compresseddata = html.read()
                compressedstream = StringIO.StringIO(compresseddata)
                gzipper = gzip.GzipFile(fileobj=compressedstream)
                html_doc = gzipper.read()
            else:
                html_doc = html.read()
            #html_doc = urllib2.urlopen(request, timeout=self.timeout).read() 
            
            img_list = self.choice_img(html_doc)
            for img in img_list:
                if not self.is_exit(img):
                    print 'get img   :  '+img
                    pass_img.add(img)
                    img_queue.put(img)
        except:
            pass
            
        
    def choice_img(self, html_doc):
        """ 寻找当前页面所有图片，返回为图片的完整地址 """
        page_imgs = []
        soup = BeautifulSoup(html_doc)
        for img in soup.findAll('img'):
            img_str = img.get('src')
            if img_str:
                if img_str.startswith('http'):
                    if img_str.find( self.web_url):
                        if img_str not in page_imgs:
                            page_imgs.append(img_str)
                            
                    else:
                        continue
                else:
                    if self.web_url+img_str not in page_imgs:
                        page_imgs.append(self.web_url+img_str)
                        
        return page_imgs

class IMGDownloader(Thread):
    """
    下载爬虫，支持多线程下载
    @threadID 当前线程编号
    @save_path 文件保存目录
    """
    def __init__(self, threadID, save_path):
        Thread.__init__(self)
        self.threadID = threadID
        self.save_path = save_path
        self.ext_list = ['']
        self.ImageHash = ImageHash()

    def run(self): 
        while True:  
            img_url = img_queue.get()
            print 'downloading: '+img_url 
            if self.get_ext(img_url):
                img_ext = self.get_ext(img_url)
                filename = hashlib.md5(str(random.random() + time.time())).hexdigest() #生成随机文件名
                self.download(img_ext, filename,img_url)

    def download(self, img_ext, filename, img_url):
        urlopen = urllib.URLopener()  
        try:  
            fp = urlopen.open(img_url)  
            data = fp.read()  
            fp.close()  
            f = open(self.save_path + "/" + filename + '.' + img_ext, 'w+b') 
            f.write(data) 
            f.close() 
            
            if os.path.getsize(self.save_path + "/" + filename+ '.' + img_ext) <10: #小于10k的图片会被删除
                os.remove( self.save_path + "/" + filename + '.' + img_ext )
                print "delete img " + filename+ '.' + img_ext
            
            img_hash = self.ImageHash.image_hash(self.save_path + "/" + filename+ '.' + img_ext)
            
            if self.is_exit(img_hash) :
                os.remove( self.save_path + "/" + filename + '.' + img_ext)
                print "delete img "+ filename + '.' +  img_ext
            os.rename(self.save_path + "/" + filename+ '.' + img_ext, self.save_path + "/" + img_hash + '.' + img_ext)
                
        except IOError:  
            pass
            
        
    def is_exit(self, img_hash):
        if img_hash in pass_hash:
            return True
        else:
            pass_hash.add(img_hash)
            return False
        
    def get_ext(self, url):
        if url[-3:] in ('jpg','png','gif','BMP'):
            return url[-3:]
        else:
            return False

url_queue.put('http://www.amazon.cn/')

threads = []
    
for i in range(100):  
        thread = URLScanner(i,2,'http://www.amazon.cn/')
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
    
for i in range(100):  
        thread = IMGScanner(i,2,'http://www.amazon.cn/')
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
    
for i in range(100):  
        thread = IMGDownloader(i,'download/')
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
        
for thread in threads:
    thread.join()
        
    