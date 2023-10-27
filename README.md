# Sistema de controle e integração VETTI com Amazon Alexa

A motivação deste projeto é a criação de um servidor capaz de receber as requisições da Amazon Alexa e interagir com a central de alarme VETTI

## Entendendo a comunicação

O Primeiro passo deste processo foi entender como seria possível interagir com a central de alarme.

A central VETTI detém um painel controlador que nada mais é do que um tablet com um APP Android que se comunica via Wifi com a central. Desta forma realizei a engenharia reversa deste APK e entendi a comunicação com o mesmo.

De forma simplificada e para atender o objetivo deste projeto foi entendido o seguinte comportamento:

1. A comunicação com a central de alarme se dá através do protocolo UDP na porta 5000
2. A comunicação é toda em texto claro com textos simples estruturados

Toda a captura da comunicação entre o painel do teclado e minha central está salva no arquivo [vetti_alarme.pcap](samples/vetti_alarme.pcap). Para abrir este arquivo é necessário o software [Wireshark](https://www.wireshark.org/).

### Autenticação com a central

```
# Auth central
[T128 TEC Idx=401 Cmd=3 Par=1234]

# Resposta
[R128 TEC Idx=401 Cmd=3 Par=1234]
```

**Nota:** O parametro `1234` é a senha de admin da central

### Comandos

Em todos os comandos abaixo notaremos a presença do parâmetro `User=` seguido de um número, onde o mesmo detém a seguinte definição.

Supondo que está sendo passado `User=01020304`

- 01: é o índice do usuário na central
- 020304: é a senha do usuário 01 na central

#### Arme todos os setores

```
# Arme Full
[T142 CMDX Id=21 User=01020304 Part=100000]

# Resposta
[R142 CMDX Id=21 User=01 PART=100000 Err=000000 Stat=AANNNN]
```

#### Desarme todos os setores
```
# Desarme
[T146 CMDX Id=22 User=01020304 Part=100000]

# Resposta
[R146 CMDX Id=22 User=01 PART=100000 Err=000000 Stat=-ANNNN]
```

#### Arme stay todos os setores
```
# Arme Stay
[T134 CMDX Id=25 User=01020304 Part=100000]

# Resposta
[R134 CMDX Id=25 User=01 PART=100000 Err=000000 Stat=SANNNN]
```

#### Resgata a data e hora da central
```
# Data e hora da central
[T136 CMD 27]

# Resposta
[R136 CMD 27 "2023/01/27 12:10:02"]
```

#### Status da conexão de rede da central
```
# Status da conexão
[T129 STAT 5]

# Resposta
[R129 STAT 5 CID=ethernet GSM=NI Time="2023/01/27 12:10:02" Serv1="empresa.seguranca.com.br" Serv2=""]
```

#### Status do alarme
```
# Status do alarme
[T137 CMD 2]

# Resposta
[R137 CMD 2 (p:SANNNN)]
```

#### Interpretando os status

**Nota:** Veja que nos comandos de armar, desarmar e status apresentam um campo com um texto similar ao `SANNNN`, que pela minha análise o primeiro campo indica o status das zonas, onde a primeira letra indica a primeira zona tendo os seguintes possíveis status:

- `A`: Acionado Full
- `S`: Acionado Stay
- `-`: Desligado

## Preparação do servidor

### Atualize a maquina

```bash
apt update && apt -y upgrade
```

## Instalando os softwares base

### Nginx

```bash
echo deb http://nginx.org/packages/mainline/ubuntu/ `lsb_release --codename --short` nginx > /etc/apt/sources.list.d/nginx.list
curl -s http://nginx.org/keys/nginx_signing.key | apt-key add -
```

### Instalando todos 
```bash
apt update && apt -y upgrade
apt install -y nginx python3.10 python3-pip python3.10-dev default-libmysqlclient-dev build-essential libssl-dev libffi-dev python3-setuptools python3.10-venv ntp ntpdate sqlite3 certbot fail2ban p7zip-full ansible unzip
apt install -y nginx-extras
```

### Log de erro multipathd

Dependendo da infra você verá constantemente no syslog o erro abaixo

```
Apr 12 19:03:41 webdev multipathd[736]: sda: add missing path
Apr 12 19:03:41 webdev multipathd[736]: sda: failed to get udev uid: Invalid argument
Apr 12 19:03:41 webdev multipathd[736]: sda: failed to get sysfs uid: Invalid argument
Apr 12 19:03:41 webdev multipathd[736]: sda: failed to get sgio uid: No such file or directory
```

Caso isso esteja ocorrendo edite o arquivo `/etc/multipath.conf` adicionando as seguintes linhas

```
defaults {
    user_friendly_names yes
}
blacklist {
    devnode "^(ram|raw|loop|fd|md|dm-|sr|scd|st|sda)[0-9]*"
}
```

Posteriormente reinicie o serviço

```bash
/etc/init.d/multipath-tools restart
```


### Locales

Para que o python possa funcionar em outros locales é necessário instalar

```
locale-gen en_US
locale-gen en_US.utf8
locale-gen pt_BR
locale-gen pt_BR.UTF-8
locale-gen pt_BR.ISO-8859-1
echo 'LANG="en_US.UTF-8"' > /etc/default/locale
echo 'LANGUAGE="en_US:en"' >> /etc/default/locale
echo 'LC_ALL="en_US.UTF-8"' >> /etc/default/locale
```

### Gestão de logs

Um item interessante pata otimizar e gerir os logs é o processo de logrotate, para isso faremos algumas configurações

Edite o arquivo **/etc/logrotate.conf** e adicione a linha abaixo

```
dateext
```

Edite os arquivos abaixo mantendo a seguinte configuração para todos eles:

```
rotate 365
daily
missingok
notifempty
delaycompress
compress
dateext
```

Arquivos a serem ajustados
- /etc/logrotate.d/rsyslog
- /etc/logrotate.d/nginx

### Sincronização de data/hora

Etapa 1: lista de fusos horários disponíveis
    
```
timedatectl list-timezones
```

Etapa 2: definir o fuso horário desejado
  
```
timedatectl set-timezone America/Sao_Paulo
```

Sincronize o relógio do sistema com o servidor a.ntp.br manualmente (use este comando apenas uma vez, ou conforme necessário):
  
```
service ntp stop
ntpdate a.ntp.br
service ntp start
```

Para iniciar, parar, reiniciar o servidor NTP use os comandos abaixo:
  
```bash
service ntp start
service ntp stop
service ntp restart
```

### Verifique usuário do Nginx

Dependendo do ambiente o Nginx é instalado usando o usuário `nginx` ou `www-data`, sendo assim é necessário descobrir qual o usuário atual para poder trabalhar em toda a config

Execute o comando abaixo para salvar esse usuário em uma variável e depois mostrar em tela

```bash
nginx_user=$(cat /etc/nginx/nginx.conf | grep -E '\buser\b' | sed 's/user//g;s/\;//g' | tr -d ' ')
echo "Nginx User: $nginx_user"
```

**Nota:** No momento da criação deste how-to o usuário foi o `www-data`, sendo assim ele será usado em todo o ambiente

## Crie usuário para o site

Como o Nginx necessitará acessar os arquivos do nosso site, vamos inserir o novo usuário com grupo padrão sendo o mesmo grupo do usuário no Nginx

```bash
adduser --disabled-password --ingroup $nginx_user --gecos "" vettiusr
```

## Configurando o NGINX

Edite o arquivo **/etc/nginx/nginx.conf** conforme abaixo:

Lembre de verificar o parâmetro **user**

```
load_module modules/ngx_http_headers_more_filter_module.so;

user  www-data;
worker_processes  1;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    ##
    # Basic Settings
    ##

    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;
    # server_tokens off;

    # server_names_hash_bucket_size 64;
    # server_name_in_redirect off;

    ##
    # SSL Settings
    ##

    ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3; # Dropping SSLv3, ref: POODLE
    ssl_prefer_server_ciphers on;

    limit_conn_zone $binary_remote_addr zone=addr:10m;
    server_names_hash_bucket_size  256;

    client_max_body_size 10m;

    ##
    # Logging Settings
    ##
    log_format log_standard '$remote_addr, $http_x_forwarded_for - $remote_user [$time_local] "$request_method $scheme://$host$request_uri $server_protocol" $status $body_bytes_sent "$http_referer" "$http_user_agent" to: $upstream_addr';

    access_log /var/log/nginx/access.log log_standard;
    error_log /var/log/nginx/error.log;

    more_set_headers 'Server: VettiAlexa';
    
    keepalive_timeout  65;

    #gzip  on;

    include /etc/nginx/conf.d/*.conf;
}
```

Crie o arquivo **/etc/nginx/conf.d/vetti.conf** conforme abaixo

```
server {
    listen        80;
    server_name _;

    #ssl_certificate      /etc/nginx/certs/cert.cer;
    #ssl_certificate_key  /etc/nginx/certs/cert.key;

    root /dev/null;
    index index.html index.htm;
    try_files $uri $uri/ $uri/404 =404;

    location / {

        uwsgi_param   Host                 $host;
        uwsgi_param   X-Real-IP            $remote_addr;
        uwsgi_param   X-Forwarded-For      $remote_addr;
        uwsgi_param   X-Forwarded-Proto    $scheme;

        client_max_body_size 5M;

        proxy_read_timeout 600;
        proxy_connect_timeout 1d;
        proxy_max_temp_file_size 5024m;
        proxy_send_timeout 600;
        uwsgi_read_timeout 600;
        uwsgi_send_timeout 600;
        include uwsgi_params;
        uwsgi_pass unix:/home/vettiusr/prod/site.sock;

    }
    
    location /static/ {
        rewrite ^/static/(.*)$ /staticfiles/$1 last;
    }
    
    location /staticfiles/ {
        root /home/vettiusr/prod/;
        try_files $uri $uri/ =404;
        error_page  404 /404.json;
        expires 1d;
        add_header Pragma public;
        add_header Cache-Control "public";
    }


}

```

Remova o arquivo padrão

```
rm -rf /etc/nginx/conf.d/default.conf
```

Habilite o serviço do nginx

```
systemctl enable nginx
systemctl start nginx
```

Recarrege a configuração do Nginx

```
nginx -s reload
```


## Serviço do site

Neste servidor iremos criar um sistema de deploy automatizado utilizando o GIT. De forma simples iremos criar uma estrutura de GIT Server neste servidor e ao ser realizado um Git push para este servidor na brach master o sistema irá automaticamente provisionar o site e reiniciar o serviço do uWSGI


### Criando o ambiente so site

Estes comandos abaixo precisam ser executados com o usuário `vettiusr`

#### Criando GIT Server
```
# su - vettiusr
$ git init --bare ~/vetti.git
```

Crie o arquivo `/home/vettiusr/vetti.git/hooks/post-receive` com o seguinte conteúdo

```
#!/bin/bash
USER=$(whoami)
BKP_DIR="/home/$USER"
TARGET="/home/$USER/prod"
GIT_DIR="/home/$USER/vetti.git"
BRANCH="master"
DATE=$(date '+%Y%m%d%H%M%S')
GRP=$(cat /etc/nginx/nginx.conf | grep -E '\buser\b' | sed 's/user//g;s/\;//g' | tr -d ' ')

while read oldrev newrev ref
do
    # only checking out the master (or whatever branch you would like to deploy)
    if [ "$ref" = "refs/heads/$BRANCH" ];
    then

        echo "Ref $ref received. Deploying ${BRANCH} branch (rev $newrev) to production..."
       
        git --work-tree=$TARGET --git-dir=$GIT_DIR checkout -f $BRANCH

        echo "Adjustting permissions"
        chown -R $USER:$GRP $TARGET

        echo "Changing DEBUG to False"
        sed -i 's/DEBUG = True/DEBUG = False/g' $TARGET/vetti_alexa/settings.py
        sed -i 's/DEBUG=True/DEBUG = False/g' $TARGET/vetti_alexa/settings.py

        cd $TARGET
        echo "Checking new dependencies"
        source bin/activate
        pip install -U pip
        pip install -r requirements.txt

        #echo "Creatting migrations"
        python manage.py makemigrations

        echo "Applying migrations"
        python manage.py migrate

        echo "Creatting static files"
        rm -rf $TARGET/staticfiles/
        python manage.py collectstatic --no-input
                
        echo "Applying Cron Jobs"
        python manage.py crontab add

        deactivate

        echo "Touching settings.py file"
        touch $TARGET/vetti_alexa/settings.py

    else
        echo "Ref $ref received. Doing nothing: only the ${BRANCH} branch may be deployed on this server."
    fi
done
```

Ajuste a permissão deste arquivo

```
chmod +x /home/vettiusr/vetti.git/hooks/post-receive
```

**Nota:** Este arquivo será o responsável por toda a automação do processo de deploy sempre que for recebido um `git push`

#### Criando ambiente virtual Python

Crie o ambiente virtual Python. Este ambiente nos permite um isolamento dos componentes python, versões e segurança.

Note que depois do comando `source` é executado um `pip install`, como o ambiente virtual foi criado usando o python 3, dentro do ambiente virtual (depois que digitamos source) o python padrão é o 3, desta forma basta executar o comando pip ao invés de pip3.

```
# su - vettiusr
$ cd ~
$ mkdir prod
$ python3.10 -m venv prod
$ source prod/bin/activate
$ pip install -U pip
$ pip install wheel uWSGI
$ deactivate
$ exit
```

Caso deseje verificar se tudo está ok, basta verificar a existência do arquivo do servidor uWSGI em `/home/vettiusr/prod/bin/uwsgi`

### Criando arquivo de configuração

Como no arquivo de configuração contém senhas, o mesmo não é colocado diretamente no código do site, mas sim em um arquivo de configuração .ini a parte.

Crie o arquivo **/home/vettiusr/prod/config.ini** com o seguinte conteúdo

Lembrando de que o arquivo precisa ter leitura para o usuário vettiusr

```
[VETTI]
auto_search=true
config_password=0000
user_password=01020304

[TELEGRAM]
chat_id=0000
bot_id=botxxx

[ALEXA]
interfaces=ens192
```

### Criando serviço do site

Para o site iremos utilizar o uWSGI como servidor

Crie o arquivo **/etc/systemd/system/vetti.service** com o conteúdo abaixo

```
[Unit]
Description=Vetti x Alexa Service
After=network.target

[Service]
User = vettiusr
Group = www-data
WorkingDirectory=/home/vettiusr/prod/
Environment="PATH=/home/vettiusr/prod/bin"
ExecStart=/home/vettiusr/prod/bin/uwsgi --socket /home/vettiusr/prod/site.sock --chmod-socket=660 --module vetti_alexa.wsgi --env DJANGO_SETTINGS_MODULE=vetti_alexa.settings --processes=2  --threads=10 --reload-mercy=1 --worker-reload-mercy=1 --req-logger file:/dev/nul --touch-reload /home/vettiusr/prod/vetti_alexa/settings.py

[Install]
WantedBy=multi-user.target
```

#### Inicie os serviços
```
# systemctl daemon-reload
# systemctl enable vetti
# systemctl start vetti
# systemctl status vetti
```

Neste momento é possível acessar via HTTP/HTTPS, porém não estará funcional pois não enviamos os arquivos do site para o servidor.

## Deploy do site

Deste momento em diante o procedimento abaixo é o mesmo a ser realizado para o deploy inicial ou qualquer atualizaçao do site.

### Adição da chave SSH

Para que possamos realizar um SSH (seja terminal, seja para o git push) se faz necessário a adição da chave SSH no arquivo **/home/vettiusr/.ssh/authorized_keys**

```
# su - vettiusr
$ mkdir -p ~/.ssh
echo "chave_ssh" >> ~/.ssh/authorized_keys
```

### Deploy

Por fim podemos realizar o deploy.

No ambiente de cliente (na sua maquina) realize o download da estrutura mais atualizada do site

```
git clone https://gitlab.com/helvio_junior/vetti_alexa.git
```

Adicione o servidor de produção como servidor remoto

```
git remote add production vettiusr@xxx.xxx.xxx.xxx:/home/vettiusr/vetti.git
```

Realize o deploy

Note que o comando acima não define a porta customizada do SSH, sendo assim necessitaremos coloca-la abaixo.

```
git push production master
```

Se tudo estiver correto, sem nenhuma interação necessária no servidor ao acessar a URL o site estará funcionando


### Criando usuário administrativo

Após o seu primeiro deploy será necessário criar o usuário administrativo no Django

```bash
# su - vettiusr
$ cd ~/prod
$ source bin/activate
$ python manage.py createsuperuser
$ deactivate
$ exit
```

### Limpando GIT no servidor.

Caso precise limpar o GIT server no servidor remoto basta executar os comandos abaixo

```bash
# su - vettiusr
$ cd ~/vetti.git
$ git branch -D master
```

## Conectando o sistema na Amazon Alexa

1. Abra o aplicativo da Alexa no Celular
2. Vá em `Devices` 
3. Vá em `Add Device`
3. Selecione a opção `Other`
4. Selecione a opção `Wi-Fi`
5. Clique em `Discover Devices`

Depois deste procedimento o seu novo dispositivo deverá aparecer na listagem de novos dispositivos da Alexa.