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

8. 服务器常见配置

   * NAT网络环境下SSH无法连接远程服务器。原因是本地NAT环境和目标Linux相关内核参数不匹配。可以尝试通过修改Linux服务器内核参数来解决该问题
     ```bash
     # 查看当前配置
     cat /proc/sys/net/ipv4/tcp_tw_recycle
     cat /proc/sys/net/ipv4/tcp_timestamps
     # 确认上述两个配置值是否为0，如果为1的话，修改如下文件
     vi /etc/sysctl.conf
     # 添加如下内容
     net.ipv4.tcp_tw_recycle=0
     net.ipv4.tcp_timestamps=0
     # 使配置生效
     sysctl -p
     ```

   * 修改SSH服务配置禁用弱加密算法，参考[Cipherli.st](https://cipherli.st/)的OpenSSH Server配置

     ```bash
     # OpenSSH Server /etc/ssh/sshd_config
     Protocol 2
     HostKey /etc/ssh/ssh_host_ed25519_key
     HostKey /etc/ssh/ssh_host_rsa_key
     KexAlgorithms curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256
     Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
     MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-512,hmac-sha2-256,umac-128@openssh.com
     ```

     ```bash
     # OpenSSH Client /etc/ssh/ssh_config
     HashKnownHosts yes
     Host github.com
       MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512
     Host *
       ConnectTimeout 30
       KexAlgorithms curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256
       MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-512,hmac-sha2-256,umac-128@openssh.com
       Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
       ServerAliveInterval 10
       ControlMaster auto
       ControlPersist yes
       ControlPath ~/.ssh/socket-%r@%h:%p
     ```

   * 修改Nginx的SSL配置，禁用弱加密算法

     ```nginx
     ssl_session_cache shared:SSL:10m;
     ssl_session_timeout 10m;

     ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
     ssl_prefer_server_ciphers on;

     ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA256:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4:!ADH:!AECDH:!DSS";

     # 'always' requires nginx >= 1.7.5, see http://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header
     add_header Strict-Transport-Security "max-age=63072000; includeSubdomains; preload" always;
     add_header X-Frame-Options DENY always;
     add_header X-Content-Type-Options nosniff always;
     ssl_session_tickets off;
     ssl_stapling on; # Requires nginx >= 1.3.7
     ssl_stapling_verify on; # Requires nginx >= 1.3.7
     ```

     其他参考：
     * [Strong SSL Security on nginx](https://raymii.org/s/tutorials/Strong_SSL_Security_On_nginx.html)
     * [加强Nginx的SSL安全](http://www.oschina.net/translate/strong_ssl_security_on_nginx)
     * [HTTPS安全最佳实践（一）之SSL/TLS部署](https://blog.myssl.com/ssl-and-tls-deployment-best-practices/)
     * [HTTPS安全最佳实践（二）之安全加固](https://blog.myssl.com/https-security-best-practices/)
     * [HTTPS安全最佳实践（三）之服务器软件](https://blog.myssl.com/https-security-best-practices-2/)
     * [Cipherli.st](https://cipherli.st/ "Strong Ciphers for Apache, nginx and Lighttpd")
     * [Mozilla's Server Side TLS Guidelines](https://wiki.mozilla.org/Security/Server_Side_TLS)
     * [Mozilla’s SSL/TLS Configuration Generator](https://mozilla.github.io/server-side-tls/ssl-config-generator/)
     * [SSL Server Test](https://www.ssllabs.com/ssltest/analyze.html)

