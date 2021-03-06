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
from imgHash import ImageHash
from crawlerMongo import PyConnect
import BaseCrawler

pre_url_queue = Queue()  #等待分析的URL链接
post_url_queue = Queue()  #分析的URL链接
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



class URLScanner(BaseCrawler.BaseCrawler):
    """ 
    爬虫扫描程序，用于获取和处理页面中的可用链接，链接存入全局队列中等待下一步处理
    @threadID 下载文件数限制
    @timeout 超时设置
    @web_url 下载的目标网址，防止越界爬取
    """
    def __init__(self, threadID, timeout,web_url):
        super(URLScanner,self).__init__(threadID, timeout)
        self.web_url = web_url
        self.table = 'pass_url'
        self.type = 'url'
        
        self.connect = PyConnect('localhost', 27017)
        self.connect.use('test_for_new')
        self.connect.setCollection('collection1')
    
    def run(self):
        global IS_CONTINUE
        while IS_CONTINUE:
            pre_url = self.get_form_queue()
            self.process(pre_url, self.type, self.table )
    
    def process(self,pre_url, type, table):
        try:
            html_doc = self.get_html_doc(pre_url)

            url_list = self.choice_href(pre_url, html_doc)
            for url in url_list:
                if not self.is_exit(table, url):
                    print 'get '+type+' : '+ url
                    post_url_queue.put(url)
                    self.put_to_queue(url)
        except:
            print 'process url'+pre_url
        
    def choice_href(self, pre_url,html_doc):
        """ 寻找当前页面所有可用链接，返回可用且在目标网站的链接数组 """
        page_urls = []
        soup = BeautifulSoup(html_doc)
        for href in soup.findAll('a'):
            href_str = href.get('href')
            if href_str: 
                if href_str.startswith('http'):     #判断是否为一个完整链接
                    if  href_str.startswith(self.web_url): #判断是否为目标网站的链接
                        if not self.connect.find({'pass_url':href_str}).count():#判断该链接是否已经爬取                          
                            page_urls.append(href_str) 
                    
                else: #对缩写链接进行补全
                    if not self.connect.find({'pass_url':self.web_url + href_str}).count():
                        url_str = urlparse.urljoin(pre_url, href_str)
                        page_urls.append(url_str)
             
        return page_urls     
    
    def process_url(self, pre_url, html_doc):
        return self.choice_href(self, pre_url,html_doc)
    
    def get_form_queue(self):
        return pre_url_queue.get()
    
    def put_to_queue(self,data):
        return pre_url_queue.put(data)


class IMGScanner(BaseCrawler.BaseCrawler):
    """ 
    爬虫扫描程序，用于获取和处理页面中的可下载图片，图片存入全局队列中等待下一步处理
    @threadID 下载文件数限制
    @timeout 超时设置
    @web_url 下载的目标网址，防止越界爬取
    """
    def __init__(self, threadID, timeout, web_url):
        super(IMGScanner,self).__init__(threadID, timeout)
        self.web_url = web_url
        self.table = 'pass_img'
        self.type = 'img'
        
        self.connect = PyConnect('localhost', 27017)
        self.connect.use('test_for_new')
        self.connect.setCollection('collection1')
    
    
    def run(self):
        global IS_CONTINUE
        while IS_CONTINUE:
            pre_url = self.get_form_queue()
            self.process(pre_url, self.type, self.table )
            
    def process(self,pre_url, type, table):
        try:
            html_doc = self.get_html_doc(pre_url)

            url_list = self.choice_img(pre_url, html_doc)

            for url in url_list:
                if not self.is_exit(table, url):
                    print 'get '+type+' : '+ url
                    self.put_to_queue(url)
        except:
            print 'process img'+pre_url
    
    def choice_img(self, pre_url, html_doc):
        """ 寻找当前页面所有图片，返回为图片的完整地址 """
        page_imgs = []
        soup = BeautifulSoup(html_doc)
        for img in soup.findAll('img'):
            img_str = img.get('src')
            if img_str:
                if  img_str.startswith('http'):
                    
                    if not self.connect.find({'pass_img':img_str}).count():#判断该链接是否已经爬取                          
                        page_imgs.append(img_str)

                else:
                    if not self.connect.find({'pass_img':self.web_url + img_str}).count():
                        url_str = urlparse.urljoin(pre_url, img_str)
                        page_imgs.append(url_str)
                        
        return page_imgs
    
    def get_form_queue(self):
        return post_url_queue.get()
    
    def put_to_queue(self,data):
        return img_queue.put(data)

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
        self.connect = PyConnect('localhost', 27017)
        self.connect.use('test_for_new')
        self.connect.setCollection('collection1')

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
                return 0
            
            img_hash = self.ImageHash.image_hash(self.save_path + "/" + filename+ '.' + img_ext)
            
            if self.is_exit('pass_hash',img_hash) :
                if os.path.getsize(self.save_path + "/" + img_hash+ '.' + img_ext) < os.path.getsize(self.save_path + "/" + filename+ '.' + img_ext):
                    os.rename(self.save_path + "/" + filename+ '.' + img_ext, self.save_path + "/" + img_hash + '.' + img_ext)
                    print "update img "+ img_hash + '.' +  img_ext
                else:
                    os.remove(os.path.getsize(self.save_path + "/" + filename+ '.' + img_ext))
                    print "delete img " + filename+ '.' + img_ext
                            
            else:
                os.rename(self.save_path + "/" + filename+ '.' + img_ext, self.save_path + "/" + img_hash + '.' + img_ext)
                print "delete img " + filename+ '.' + img_ext
                
        except IOError:  
            print 'IOError'+img_url
            
        
    def get_ext(self, url):
        """ 判断扩展名是否为图片 """
        if url[-3:] in self.ext_list:
            return url[-3:]
        else:
            return False
        
    def is_exit(self, table, pre_url):
        if self.connect.find({ table :pre_url }).count():
            return True
        else:
            self.connect.insert({ table :pre_url })
            return False

class URLScannerManager(Thread):
    def __init__(self, thread_num, timeout, web_url):
        Thread.__init__(self)
        self.thread_num = thread_num
        self.timeout = timeout
        self.url = web_url
        self.threads = []
        
    def run(self):
        for i in range(self.thread_num):  
            thread = URLScanner(i, self.timeout, self.url)
            thread.setDaemon(True) 
            thread.start() 
            self.threads.append(thread)
        for thread in self.threads:
            thread.join()
    
class IMGScannerManager(Thread):
    def __init__(self, thread_num, timeout, web_url):
        Thread.__init__(self)
        self.thread_num = thread_num
        self.timeout = timeout
        self.url = web_url
        self.threads = []
        
    def run(self):
        for i in range(self.thread_num):  
            thread = IMGScanner(i, self.timeout, self.url)
            thread.setDaemon(True) 
            thread.start() 
            self.threads.append(thread)
        for thread in self.threads:
            thread.join()

class IMGDownloaderManager(Thread):
    def __init__(self, thread_num, save_path, file_size):
        Thread.__init__(self)
        self.thread_num = thread_num
        self.save_path = save_path
        self.file_size = file_size
        self.threads = []
        
    def run(self):
        for i in range(self.thread_num):  
            thread = IMGDownloader(i, self.save_path,self.file_size)
            thread.setDaemon(True) 
            thread.start() 
            self.threads.append(thread)
        for thread in self.threads:
            thread.join()       


def my_crawler(url = "http://www.meizitu.com/", save_path = './download/', url_thread = 2, img_thread = 4, download_thread = 8, file_num_limit= 0, frequency=0.1, timeout = 5, file_size =10000):
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

    pre_url_queue.put(url)

    threads = []
        
    
        
    if url_thread != 0 : 
        thread = URLScannerManager(url_thread, timeout, url)
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
    
    if img_thread != 0 : 
        thread = IMGScannerManager(img_thread, timeout, url)
        thread.setDaemon(True) 
        thread.start() 
        threads.append(thread)
        
    if download_thread != 0 : 
        thread = IMGDownloaderManager(download_thread, save_path, file_size)
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
    
    pre_url_queue.join() 
    post_url_queue.join() 
    img_queue.join() 

if __name__=="__main__":
    my_crawler()
    print "end"
    
