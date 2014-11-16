#mm_crawler
********
A simple image crawler of [http://www.22mm.cc](http://www.22mm.cc)


<br /> 
##设计思路（2014/11/08更新）：
***

本爬虫被拆分为可用链接扫描、图片扫描、图片下载三个模块，每个模块支持多线程并相对独立，之间依靠两个队列联系。因为模块的处理流程有很多相似的地方，所以准备创建处理基类和管理基类，用继承提高代码复用。

链接扫描模块负责扫描当前链接页面下所有可以打开的页面链接，从未处理URL队列中取出URL，每个线程扫描完成一个页面即将其URL加入数据库中。扫描后将获得的未处理页面加入未处理URL队列供链接扫描，当前已处理的链接加入已处理URL队列中供图片扫描模块线程取用。

图片扫描模块负责获取当前链接页面下所有可以下载的图片的链接，从已处理URL队列中取出URL，每个线程扫描完成一个页面的图片后即将其URL加入数据库中，后将其加入图片URL队列，供图片下载模块线程取用。

图片下载模块负责下载从图片URL队列中取出图片链接，通过打开链接图片保存内容到本地的方式下载。下载之后对文件大小进行判断，小于一定数值（默认为10k）即视为无关图像予以删除。之后对非无关图像进行感知哈希计算，得到一串8位十六进制的字符串，将该字符串与集合中之前下载的图片哈希做对比，相同即对比两张图片的大小，保留相对较大的图片。如果不存在相同哈希即保存新的图片，并将其加入集合。

下载数目控制线程负责在一定时间频率下扫描保存文件夹中文件数目，超过规定的数目时终止所有处理扫描线程的工作。因为是间隔扫描，所以会有超出限制下载数目的情况，超出数目与下载速度有关。

为了扩展和分布式和负载均衡功能的考虑，之后会为每个模块加入独立的管理模块，每个管理模块为单独线程。负责管理各自负责模块的线程运行状况，对卡死进程进行重置。随时监控队列中的任务数和系统负载，如果超过一定数量则挂起部分线程（即线程停止获取队列中链接，如果是链接扫描模块则暂停扫描），减少对带宽的过度占用，提高下载效率。

为了最终多机分布式运行，每个管理模块模块负责维护自己的数据库，每个扫描或下载线程只是单纯的从管理模块取得任务进行处理（暂时设计为一次取出一个任务，不排除之后加入取出任务链表），完成后将结果返回给相应的管理模块，由管理模块负责传给下游的管理模块继续处理（即会取消公共队列，转为管理模块内部任务和结果队列）。每个线程（暂时为模拟多机，之后会转为多进程）通过UDP算送包含自己当前机器负载（CPU、内存、网络占用率）数据，使管理模块能够了解其运行状况，以便安排负载。管理和处理模块之间使用TCP进行传输。各管理模块使用TCP进行传输结果列表。在顶层设置总管理模块，用于启动和管理三个管理模块，监视其运行状况，收集各个模块的日志文件进行汇总。

<br /> 
##环境依赖：

* 系统：Ubuntu14.04 x64

* python版本：2.7

* python库（非默认库，需要单独安装）：BeautifulSoup、PIL、pyMongo

* 数据库：Mongodb 
<br /> 
***
##version:0.3

update time: 2014/11/09

###更新：

* 修改之前相对地址组合问题，减少错误链接的出现

* 修改之前相同图片保存之前小图的问题，改为比较大小，保留较大的文件

* 添加命令行输入功能

* 修改部分逻辑bug

* 添加对Mongodb数据库的支持

* 对相似功能和代码重构，对模块进行拆分

* 加入对下载图片数量进行限制，可以通过命令行调整，默认为无限制
<br /> 
***

##version:0.2

update time: 2014/11/06

  之前的爬虫算是练习，今天重新把爬虫的架构梳理了一遍，对整个代码重新写了一遍，让其满足多线程工作，为之后的分布式爬虫架构的实现做准备。注释还没有加上，而且因为时间紧急没有写继承，导致代码重复严重。这个会在下一个版本中得到改正。本版本为了测试功能，之前的命令行输入功能暂时取消。


###功能：

* 理论上能够对任何标准结构网站进行图片的爬取

* 排除无关的图片

* 使用感知哈希算法去处有极小差异的图片，做到了对重复图像的分辨和剔除

* 更改爬虫架构。链接扫描模块，图片链接获取模块，图片下载模块分离，并且各自做到多线程，极大提高效率

* 每个线程相互独立，为之后分布式架构做准备

* 使用gzip压缩页面，降低对网速的占用

* 放弃了使用递归扫描的方式

###缺陷：

* 多线程扫描速度没有得到控制，导致22mmcc网站的安全狗防火墙阻拦爬虫继续访问

* 使用python的集合进行储存爬取链接和图片，没有使用数据库导致内存占用严重（总共300线程时约350M内存占用）

* 对图像的分辨和删除是在图片下载之后进行，浪费了带宽

* 爬虫在初期爬取速度不错，但是后期速度递减严重，应该与没有使用数据库有关

* 对链接的识别简单粗暴，很多短链接识别失败。


###将来改进：

* 加入对数据库的支持，暂定为Mongodb      √  

* 解决扫描速度过快被网站防火墙拦截的情况

* 整理代码，做到模块分离   √  

* 添加命令行输入功能   √  

* 加入负载均衡功能，在任务过多情况下停止扫描

* 准备尝试将爬虫改为多机分布式爬虫   √  

<br /> 
***

##version:0.1  

  经过一下午加一晚上的研究，完成一个简单的多线程图片爬虫。第一次接触爬虫，参考了许多现有程序，现研究的html，感觉学到很多。
html解析使用的是BeautifulSoup，命令行输入使用argparse，网络连接使用urllib2。运行系统Ubuntu14.04

###功能：

* 可以使用命令行输入目标网址、图片保存位置、下载线程数、递归深度、超时设置；

* 理论上对任何标准的图片网站都能实现爬取；

* 通过将扫描程序将爬取的图片存入队列使得多个线程同时下载；

* 可以排除无关的图像。


###缺陷：

* 扫描图片没有做到多线程，导致扫描速度过慢；

* 逻辑没有思考清楚，在扫描完成一个页面后才会添加到队列，导致初期或深度为1时等待时间过长；

* 没有做到对不同位置爬得的图像分类存储；

* 扫描完后程序无法退出，目测是线程没正常退出导致；

* 排除无关图像使用的是删除10k以下图像，浪费资源；

* 无法做到对重复图像的分辨和剔除。


###将来改进：

* 现在无法做到对图像去重，准备使用感知哈希算法生成字符串存入数据库。使用专门线程进行扫描和删除；  √  

* 改变扫描逻辑，增加多线程扫描，提高扫描速度；  √  

* 整理模块，保证划分清晰。  √  

-------------------------------------------------------------------------------------------------------------------
