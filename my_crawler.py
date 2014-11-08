# -*- coding:utf-8 -*-  
#author: luoding
#blog:www.nwber.com
#E-mail: luoding@nwber.com

import urllib 
import urllib2 
import cookielib
import urlparse
import StringIO
import gzip
import hashlib
import os
import time
import random
import argparse
from Queue import Queue  
from BeautifulSoup import * 
from threading import Thread
from PIL import Image


pass_url = set() #已处理过的URL链接
pass_img = set() #已处理过的图片链接
pass_hash = set() #已下载过的图片的感知哈希值

url_queue = Queue()  #等待分析的URL链接
img_queue = Queue()  #等待下载的图片链接

IS_CONTINUE = True   #控制所有线程，用于下载图片数限制
VERSION = 0.3   #当前版本号

class FileNumLimit(Thread):
    """ 
    限制下载图片数目线程，限定时间间隔查看文件夹中文件，如果超出则终止所有线程运行
    因为扫描有时间间隔，所以最终结果可能有一定超出，超出数目与下载速度有关
    @file_num_limit 下载文件数限制
    @frequency 检查目标文件夹中文件数目频率
    @save_path 下载保存文件夹
    """
    def __init__(self, file_num_limit, frequency, save_path):
        Thread.__init__(self)
        self.file_num_limit = file_num_limit
        self.frequency = frequency
        self.save_path = save_path
        
    def run(self):
        global IS_CONTINUE #全局变量来控制所有线程的运行
        while IS_CONTINUE:  
            if self.file_num_limit <= sum([len(files) for root,dirs,files in os.walk(self.save_path)]): 
                #对比目标文件夹中的文件数与限制文件数
                IS_CONTINUE = False
            time.sleep(self.frequency)

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

class URLScanner(Thread):
    """ 
    爬虫扫描程序，用于获取和处理页面中的可用链接，链接存入全局队列中等待下一步处理
    @threadID 下载文件数限制
    @timeout 超时设置
    @web_url 下载的目标网址，防止越界爬取
    """
    def __init__(self, threadID, timeout,web_url):
        Thread.__init__(self)
        self.threadID = threadID
        self.timeout = timeout
        self.web_url = web_url
    
    
    def run(self):
        global IS_CONTINUE
        while IS_CONTINUE:
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
            request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux i686)\
                              AppleWebKit/537.36 (KHTML, like Gecko)\
                              Chrome/35.0.1916.153 Safari/537.36')
            request.add_header('Accept', 'text/html,application/xhtml+xml,\
                              application/xml;q=0.9,image/webp,*/*;q=0.8')
            request.add_header('Accept-encoding', 'gzip')
            request.add_header('Accept-Language', 'zh-CN,zh;q=0.8,en;q=0.6')

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
            url_list = self.choice_href(pre_url, html_doc)
            for url in url_list:
                if not self.is_exit( url):
                    print 'get url   :  '+url
                    pass_url.add(url)
                    url_queue.put(url)
        except:
            pass
            
        
    def choice_href(self, pre_url,html_doc):
        """ 寻找当前页面所有可用链接，返回可用且在目标网站的链接数组 """
        page_urls = []
        soup = BeautifulSoup(html_doc)
        for href in soup.findAll('a'):
            href_str = href.get('href')
            if href_str: 
                if href_str.startswith('http'):     #判断是否为一个完整链接
                    if  href_str.startswith(self.web_url): #判断是否为目标网站的链接
                        if href_str not in pass_url:   #判断该链接是否已经爬取
                            page_urls.append(href_str) 
                    
                else: #对缩写链接进行补全
                    if self.web_url + href_str not in pass_url:
                        url_str = urlparse.urljoin(pre_url, href_str)
                        page_urls.append(url_str)
             
        return page_urls     


class IMGScanner(Thread):
    """ 
    爬虫扫描程序，用于获取和处理页面中的可下载图片，图片存入全局队列中等待下一步处理
    @threadID 下载文件数限制
    @timeout 超时设置
    @web_url 下载的目标网址，防止越界爬取
    """
    def __init__(self, threadID, timeout, web_url):
        Thread.__init__(self)
        self.threadID = threadID
        self.timeout = timeout
        self.web_url = web_url
    
    def run(self):
        global IS_CONTINUE
        while IS_CONTINUE:
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
            request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux i686)\
                              AppleWebKit/537.36 (KHTML, like Gecko)\
                              Chrome/35.0.1916.153 Safari/537.36')
            request.add_header('Accept', 'text/html,application/xhtml+xml,\
                              application/xml;q=0.9,image/webp,*/*;q=0.8')
            request.add_header('Accept-encoding', 'gzip')
            request.add_header('Accept-Language', 'zh-CN,zh;q=0.8,en;q=0.6')
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
            
            img_list = self.choice_img(pre_url, html_doc)
            for img in img_list:
                if not self.is_exit(img):
                    print 'get img   :  '+img
                    pass_img.add(img)
                    img_queue.put(img)
        except:
            pass
            
        
    def choice_img(self, pre_url, html_doc):
        """ 寻找当前页面所有图片，返回为图片的完整地址 """
        page_imgs = []
        soup = BeautifulSoup(html_doc)
        for img in soup.findAll('img'):
            img_str = img.get('src')
            print img
            if img_str:
                if  img_str.startswith('http'):
                    
                    if img_str not in pass_img:
                        page_imgs.append(img_str)

                else:
                    if self.web_url+img_str not in pass_img:
                        url_str = urlparse.urljoin(pre_url, img_str)
                        page_imgs.append(url_str)
                        
        return page_imgs

class IMGDownloader(Thread):
    """
    下载爬虫，支持多线程下载
    @threadID 当前线程编号
    @save_path 文件保存目录
    """
    def __init__(self, threadID, save_path, file_size):
        Thread.__init__(self)
        self.threadID = threadID
        self.save_path = save_path
        self.ext_list = ('jpg','png','gif','bmp','JPG','PNG','GIF','BMP')
        self.ImageHash = ImageHash()
        self.file_size = file_size

    def run(self): 
        global IS_CONTINUE
        while IS_CONTINUE:  
            img_url = img_queue.get()
            print 'downloading: '+img_url 
            if self.get_ext(img_url):
                img_ext = self.get_ext(img_url)
                filename = hashlib.md5(str(random.random() + time.time())).hexdigest() #生成随机文件名
                self.download(img_ext, filename,img_url)

    def download(self, img_ext, filename, img_url):
        """
        通过打开链接图片保存内容到本地的方式下载
        下载之后对文件大小进行判断，小于一定数值（默认为10k）即视为无关图像予以删除
        之后对非无关图像进行感知哈希计算，将哈希值与之前下载的图片做对比
        相同即对比两张图片的大小，保留相对较大的图片
        如果不存在相同哈希即保存新的图片，并将其加入全局集合pass_hash
        """
        urlopen = urllib.URLopener()  
        try:  
            fp = urlopen.open(img_url)  
            data = fp.read()  
            fp.close()  
            f = open(self.save_path + "/" + filename + '.' + img_ext, 'w+b') 
            f.write(data) 
            f.close() 
            
            if os.path.getsize(self.save_path + "/" + filename+ '.' + img_ext) < self.file_size: #小于10k的图片会被删除
                os.remove( self.save_path + "/" + filename + '.' + img_ext )
                print "delete img " + filename+ '.' + img_ext
            
            img_hash = self.ImageHash.image_hash(self.save_path + "/" + filename+ '.' + img_ext)
            
            if self.is_exit(img_hash) :
                if os.path.getsize(self.save_path + "/" + img_hash+ '.' + img_ext) < os.path.getsize(self.save_path + "/" + filename+ '.' + img_ext):
                    os.rename(self.save_path + "/" + filename+ '.' + img_ext, self.save_path + "/" + img_hash + '.' + img_ext)
                    print "update img "+ img_hash + '.' +  img_ext
            else:
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
        """ 判断扩展名是否为图片 """
        if url[-3:] in self.ext_list:
            return url[-3:]
        else:
            return False


    
def my_crawler(url = "http://www.22mm.cc", save_path = './download/', url_thread = 1, img_thread = 1, download_thread = 4, file_num_limit= 0, frequency=0.1, timeout = 5, file_size =10000):
    parser = argparse.ArgumentParser(description='一个简易的多线程图片爬虫')
    parser.add_argument("-v", "--version", action="store_true", help="当前版本号")
    parser.add_argument("-ut","--url_thread",type=int, help="扫描链接线程数，默认为1")
    parser.add_argument("-it","--img_thread",type=int, help="扫描图片线程数，默认为1")
    parser.add_argument("-dt","--download_thread",type=int, help="图片下载线程数，默认为4")
    parser.add_argument("-s","--save_path",help="下载图片保存位置，默认为当前目录" )
    parser.add_argument("-u","--url",help="爬取的目标网址，格式http://www.baidu.com/")
    parser.add_argument("-l","--file_num_limit",help="下载文件数限制，默认为无限制")
    parser.add_argument("-fs","--file_size",help="文件大小小于规定数值即视为无关图像予以删除，默认为10000（即10k）")
    parser.add_argument("-f","--frequency",help=" 检查目标文件夹中文件数目频率（单位：秒），默认为0.1秒")
    parser.add_argument("-o","--timeout",help="网络连接超时设置，默认为5")
    args = parser.parse_args()
    if args.version:
        print "当前版本号: "+str(VERSION)
        exit()
    if args.save_path:
        save_path = args.outputPath
    if args.url_thread:
        url_thread =args.url_thread
    if args.img_thread:
        img_thread =args.img_thread
    if args.download_thread:
        download_thread =args.download_thread
    if args.url:
        url =args.url
    if args.file_num_limit:
        file_num_limit =args.file_num_limit
    if args.timeout:
        timeout =args.timeout
    if args.file_size:
        file_size =args.file_size

    if not os.path.exists(save_path):
        os.mkdir(save_path)

    url_queue.put(url)

    threads = []
        
    for i in range(url_thread):  
        thread = URLScanner(i, timeout, url)
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
        
    for i in range(img_thread):  
        thread = IMGScanner(i, timeout, url)
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
        
    for i in range(download_thread):  
        thread = IMGDownloader(i, save_path,file_size)
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
    
    if file_num_limit != 0 :
        thread = FileNumLimit( file_num_limit, frequency, save_path)
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
            
    for thread in threads:
        thread.join()
    
    url_queue.join() 
    img_queue.join() 

if __name__=="__main__":
    my_crawler()
    print "end"
    