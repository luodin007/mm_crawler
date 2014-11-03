# -*- coding:utf-8 -*-  
#author: luoding
#blog:www.nwber.com
#E-mail: luoding@nwber.com

import os  
import urllib  
import urllib2  
import urlparse 
import time
import random
import hashlib
import argparse
from BeautifulSoup import * 
from Queue import Queue  
from threading import Thread  

img_queue = Queue()  #储存图片地址的队列
version = 0.1

class URLLister:
    """
    爬虫扫描程序，用于获取和处理页面中的图片和链接，图片存入全局队列中等待下载
    @web_url 目标网址，格式 http://www.baidu.com/
    @timeout 超时设置，推荐为10
    @depth 搜索递归深度，太大将造成扫描时间过长
    """
    def __init__(self, web_url, timeout, depth):
        self.web_url = web_url  
        self.timeout = timeout
        self.depth = depth
        self.passUrls = set()  
    
    def start(self):
        """ 启动爬虫扫描程序 """
        self.get_page_html(self.web_url, self.depth)
           
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
                elif href_str.startswith('/'): #对缩写链接进行补全
                    if self.web_url + href_str not in page_urls:
                        page_urls.append(self.web_url + href_str)
             
        return page_urls
                    
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
                            print "get image: "+img_str
                    else:
                        continue
                elif img_str.startswith('/'):
                    if self.web_url+img_str not in page_imgs:
                        page_imgs.append(self.web_url+img_str)
                        
        return page_imgs
    
    def get_url_of_page(self, url, is_img=False):
        """ 
        获取一个页面上的所有链接。 
        is_img:如果为true，则获取的是页面上的所有图片的链接  
        """
        try:  
            html_doc = urllib2.urlopen(url, timeout=self.timeout).read()  
            if is_img:
                return self.choice_img(html_doc)

            else:
                return self.choice_href(html_doc)
            
        except urllib2.URLError, e:  
            print e
            return 
    
    def get_page_html(self, begin_url, depth):
        """ 递归处理页面，并将图片链接存入全局队列"""
        page_urls = []
        page_imgs = []
        if depth <= 0:  
            return 
        self.passUrls.add(begin_url) #忽略的链接
        
        page_urls = self.get_url_of_page(begin_url)  
        if page_urls:  
            for url in page_urls:  
                if not url in self.passUrls:
                    self.get_page_html(url, depth - 1)
    
        for img in self.get_url_of_page(begin_url,True):
            img_queue.put(img)  
        

class DownloadCrawler(Thread):
    """
    下载爬虫，支持多线程下载
    @threadID 当前线程编号
    @save_path 文件保存目录
    """
    def __init__(self, threadID, save_path):
        Thread.__init__(self)
        self.threadID = threadID
        self.save_path = save_path

    def run(self): 
        while True:  
            img_url = img_queue.get()
            print 'downloading: '+img_url  
            filename = hashlib.md5(str(random.random() + time.time())).hexdigest() #生成随机文件名
            self.download(filename, img_url)

    def download(self, filename, img_url):
        urlopen = urllib.URLopener()  
        try:  
            fp = urlopen.open(img_url)  
            data = fp.read()  
            fp.close()  
            f = open(self.save_path + "/" + filename, 'w+b') 
            f.write(data) 
            f.close() 
            if os.path.getsize(self.save_path + "/" + filename) <10000: #小于10k的图片会被删除
                os.remove( self.save_path + "/" + filename )
        except IOError:  
            print "download error!" + filename

def my_crawler():
    parser = argparse.ArgumentParser(description='一个简易的多线程图片爬虫')
    parser.add_argument("-v", "--version", action="store_true", help="当前版本号")
    parser.add_argument("-t","--thread",type=int, help="爬虫下载线程数，默认为2")
    parser.add_argument("-s","--save_path",help="下载图片保存位置，默认为当前目录" )
    parser.add_argument("-u","--url",help="爬取的目标网址，格式http://www.baidu.com")
    parser.add_argument("-d","--deep",help="爬虫搜索递归深度，太大将造成扫描时间过长，默认为2")
    parser.add_argument("-o","--timeout",help="网络连接超时设置，默认为10")
    url = "http://www.22mm.cc"
    save_path = './'
    threadNum = 3
    deep = 1
    timeout = 20
    args = parser.parse_args()
    if args.version:
        print "当前版本号: "+version
    elif args.save_path:
        save_path = args.outputPath
    elif args.thread:
        threadNum =args.thread
    elif args.url:
        url =args.url
    elif args.deep:
        deep =args.deep
    elif args.timeout:
        timeout =args.timeout

    if not os.path.exists(save_path):
        os.mkdir(save_path)

    test = URLLister(url,timeout,deep)
    test.start()
    threads = []
    
    for i in range(threadNum):  
            thread = DownloadCrawler(i, save_path)
            thread.setDaemon(True) 
            thread.start() 
            threads.append(thread)
            
    for thread in threads:
        thread.join()
    img_queue.join() 

if __name__=="__main__":
    my_crawler()
    print "end"

