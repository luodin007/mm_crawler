# -*- coding:utf-8 -*-  
#author: luoding
#blog:www.nwber.com
#E-mail: luoding@nwber.com
import urllib 
import urllib2 
import StringIO
import gzip
from threading import Thread
from crawlerMongo import PyConnect

class BaseCrawler(Thread):
    def __init__(self, threadID,timeout):
        Thread.__init__(self)
        self.threadID = threadID
        self.timeout = timeout
        self.connect = PyConnect('localhost', 27017)
        self.connect.use('test_for_new')
        self.connect.setCollection('collection1')
    
    def is_exit(self, table, pre_url):
        if self.connect.find({ table :pre_url }).count():
            return True
        else:
            self.connect.insert({ table :pre_url })
            return False
    
    def get_html_doc(self,pre_url):
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
                
            return html_doc
        
        except:
            print 'get_html_doc_error'
    
    
        
class BaseManager:
    def __init__(self, thread_num):
        self.thread_num = thread_num
        self.threads = []
        
    def create_thread(self):
        for threadID in range(self.thread_num):
            thread = self.crawler_class(threadID)
            thread.start()
            self.threads.append(thread)
            
        