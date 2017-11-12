# python-webapp-sample
A Python Webapp Sample

## Dependencies
* jinja2
* mysql-connector-python
* watchdog

## Deployment

1. 部署方式

   WSGI服务器选择[gunicorn](http://gunicorn.org/)，它用类似Nginx的Master-Worker模式，同时可以提供gevent支持，不用修改代码即可获得极高的性能

   Web服务器选择Nginx，可以处理静态资源，同时作为反向代理把动态请求交给gunicorn处理，gunicorn负责调用Python代码

2. 服务端部署目录结构

   ```
   +--srv/
      +--pws/          <--WebApp根目录
         +--log/       <--存放log
         +--www/       <--存放Python源码
            +--static  <--存放静态资源文件
   ```
   考虑部署时版本更新与回退可能比较频繁，把www作为一个软链接，它指向哪个目录，哪个目录就是当前运行的版本，而Nginx和gunicorn的配置文件只需要指向www目录即可

3. Nginx可以作为服务进程直接启动，但gunicorn还不行，可以使用[Supervisor](http://supervisord.org/)。Supervisor是一个管理进程的工具，可以随系统启动而启动服务，还可以时刻监控服务进程，如果服务进程意外退出，Supervisor可以自动重启服务

4. 安装相关服务

   * Nginx：高性能Web服务器+负责反向代理
   * gunicorn：高性能WSGI服务器
   * gevent：把Python同步代码变成异步协程的库
   * Supervisor：监控服务进程的工具
   * MySQL：数据库服务

   以下安装命令均在CentOS 7.3 x64上执行

   ```bash
   # 安装相关服务和依赖
   yum install nginx
   yum install python-gevent
   yum install supervisor
   yum install python-gunicorn
   # 如果当前系统的yum源中没有MySQL，则需要添加repo源
   #wget http://repo.mysql.com/mysql-community-release-el7-5.noarch.rpm
   #rpm -ivh mysql-community-release-el7-5.noarch.rpm
   yum install mysql-server
   yum install python-jinja2
   yum install mysql-connector-python

   # 创建服务端部署目录
   mkdir /srv/pws
   useradd www-data
   passwd www-data
   chown www-data:www-data pws

   # 初始化数据库，如果root用户没有密码可以不用加-p参数
   systemctl start mysql
   mysql -u root -p < schema.sql

   # 启动supervisor
   systemctl start supervisord
   # 启动nginx
   systemctl start nginx
   ```

5. 配置部署

   使用工具配合脚本完成自动化部署，[Fabric](http://www.fabfile.org/)是一个自动化部署工具，是用Python开发的，所以部署脚本也是用Python来编写

   要在开发机（不是服务器）上安装Fabric
   ```
   pip install fabric
   ```

6. 使用supervisor启停服务

   ```bash
   supervisorctl stop pws
   supervisorctl start pws
   supervisorctl status
   systemctl restart nginx
   ```

7. 配置nginx支持https访问

   这里使用[Let’s Encrypt](https://letsencrypt.org/)配置https

   * 访问[Certbot](https://certbot.eff.org/)，按照首页提示，选择Server和操作系统版本，会显示相应的操作步骤
   * 例如Nginx+CentOS7：https://certbot.eff.org/#centosrhel7-nginx

