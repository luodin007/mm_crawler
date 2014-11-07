mm_crawler
==========

A simple image crawler of 22mm.cc

设计思路（2014/11/08更新）：

本爬虫被拆分为可用链接扫描、图片扫描、图片下载三个模块，每个模块支持多线程并相对独立，之间依靠两个队列联系。因为模块的处理流程有很多相似的地方，所以准备创建处理基类和管理基类，用继承提高代码复用。

链接扫描模块负责扫描当前链接页面下所有可以打开的页面链接，模块维持一个公共的保存已扫描页面URL的集合，每个线程扫描完成一个页面即将其URL加入集合，python的集合可以保证其成员唯一性，之后可以将其转为数据库保存。扫描后将获得的未扫描页面加入队列中，供图片扫描模块线程取用。

图片扫描模块负责获取当前链接页面下所有可以下载的图片的链接，模块维持一个公共的保存已扫描图片的URl集合，每个线程扫描完成一个页面的图片后即将其URL加入集合，后将其加入队列，供图片下载模块线程取用。

图片下载模块负责下载从队列中取出图片链接，通过打开链接图片保存内容到本地的方式下载。下载之后对文件大小进行判断，小于一定数值（默认为10k）即视为无关图像予以删除。之后对非无关图像进行感知哈希计算，得到一串8位十六进制的字符串，将该字符串与集合中之前下载的图片哈希做对比，相同即对比两张图片的大小，保留相对较大的图片。如果不存在相同哈希即保存新的图片，并将其加入集合。

为了扩展和分布式和负载均衡功能的考虑，之后会为每个模块加入独立的管理模块，每个管理模块为单独线程。负责管理各自负责模块的线程运行状况，对卡死进程进行重置。随时监控队列中的任务数和系统负载，如果超过一定数量则挂起部分线程（即线程停止获取队列中链接，如果是链接扫描模块则暂停扫描），减少对带宽的过度占用，提高下载效率。

为了最终多机分布式运行，每个管理模块模块负责维护自己的数据库，每个扫描或下载线程只是单纯的从管理模块取得任务进行处理（暂时设计为一次取出一个任务，不排除之后加入取出任务链表），完成后将结果返回给相应的管理模块，由管理模块负责传给下游的管理模块继续处理（即会取消公共队列，转为管理模块内部任务和结果队列）。每个线程（暂时为模拟多机，之后会转为多进程）通过UDP算送包含自己当前机器负载（CPU、内存、网络占用率）数据，使管理模块能够了解其运行状况，以便安排负载。管理和处理模块之间使用TCP进行传输。各管理模块使用TCP进行传输结果列表。在顶层设置总管理模块，用于启动和管理三个管理模块，监视其运行状况，收集各个模块的日志文件进行汇总。



-------------------------------------------------------------------------------------------------------------------
version:0.2

update time: 2014/11/06

  之前的爬虫算是练习，今天重新把爬虫的架构梳理了一遍，对整个代码重新写了一遍，让其满足多线程工作，为之后的分布式爬虫架构的实现做准备。注释还没有加上，而且因为时间紧急没有写继承，导致代码重复严重。这个会在下一个版本中得到改正。本版本为了测试功能，之前的命令行输入功能暂时取消。


功能：

1.理论上能够对任何标准结构网站进行图片的爬取

2.排除无关的图片

3.使用感知哈希算法去处有极小差异的图片，做到了对重复图像的分辨和剔除

4.更改爬虫架构。链接扫描模块，图片链接获取模块，图片下载模块分离，并且各自做到多线程，极大提高效率

5.每个线程相互独立，为之后分布式架构做准备

6.使用gzip压缩页面，降低对网速的占用

7.放弃了使用递归扫描的方式

缺陷：

1.多线程扫描速度没有得到控制，导致22mmcc网站的安全狗防火墙阻拦爬虫继续访问

2.使用python的集合进行储存爬取链接和图片，没有使用数据库导致内存占用严重（总共300线程时约350M内存占用）

3.对图像的分辨和删除是在图片下载之后进行，浪费了带宽

4.爬虫在初期爬取速度不错，但是后期速度递减严重，应该与没有使用数据库有关

5.对链接的识别简单粗暴，很多短链接识别失败。


将来改进：

1.加入对数据库的支持，暂定为MySQL

2.解决扫描速度过快被网站防火墙拦截的情况

3.整理代码，做到模块分离

4.添加命令行输入功能

5.加入负载均衡功能，在任务过多情况下停止扫描

6.准备尝试将爬虫改为多机分布式爬虫


环境依赖：

1.系统：Ubuntu14.04 x64

2.python版本：2.7

3.python库（非默认库，需要单独安装）：BeautifulSoup、PIL 

-------------------------------------------------------------------------------------------------------------------
version:0.1  

  经过一下午加一晚上的研究，完成一个简单的多线程图片爬虫。第一次接触爬虫，参考了许多现有程序，现研究的html，感觉学到很多。
html解析使用的是BeautifulSoup，命令行输入使用argparse，网络连接使用urllib2。运行系统Ubuntu14.04

功能：

1.可以使用命令行输入目标网址、图片保存位置、下载线程数、递归深度、超时设置；

2.理论上对任何标准的图片网站都能实现爬取；

3.通过将扫描程序将爬取的图片存入队列使得多个线程同时下载；

4.可以排除无关的图像。


缺陷：

1.扫描图片没有做到多线程，导致扫描速度过慢；

2.逻辑没有思考清楚，在扫描完成一个页面后才会添加到队列，导致初期或深度为1时等待时间过长；

3.没有做到对不同位置爬得的图像分类存储；

4.扫描完后程序无法退出，目测是线程没正常退出导致；

5.排除无关图像使用的是删除10k以下图像，浪费资源；

6.无法做到对重复图像的分辨和剔除。


将来改进：

1.现在无法做到对图像去重，准备使用感知哈希算法生成字符串存入数据库。使用专门线程进行扫描2.和删除；

3.改变扫描逻辑，增加多线程扫描，提高扫描速度；

4.整理模块，保证划分清晰。

-------------------------------------------------------------------------------------------------------------------
