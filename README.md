**What is ushare?**

Ushare is a rather old UPnP server that is no longer maintained. I installed it 10 years ago on a raspberry pi and it still functions quite well, but it is no longer available on newer OS'es. It is simple directory based and has no database like functions: you can not sort or search its results but that is no problem if you have a neat directory structure for your music files.


**What advantages has Ushare over other UPnP servers?**

Apart from being simple and lightweight it has one advantage that made this project for me worthwhile: it supports radio stations (as part of playlist files). Many UPnP servers look for mp3's in a playlist file and thus refuse to play an url radio station. Other UPnP servers can serve playlist files with radio stations but can only show these playlist files in one directory or combined in one long playlist file. Another advantage of my implementation of ushare in Python is that you can modify/adapt the software to borderline compliant UPnP implementations of clients. See below.


**How did I implement my ushare like UPnP server?**

From the beginning I choose Python as my implementation language. Originally Ushare was written in C and I tried to recompile it on a more modern environment (Debian 12). Because Ushare uses upnp and dlna libraries that have changed over time and because my experience with C is very limited, I choose to implement it in Python with commonly available libraries. I did not use any code from Ushare.


**Limitations**

I origionally made my Ushare for the most common filetypes for music. Later I added video and subtitles but I think UPnP is less suitable for video. It does not do transcoding. and there are no search and sort facilities, you must have a reasonable directory structure for your music.


**installation**

Installation is quite easy. I use two special modules normally not standard installed: aiohttp (for asynchrone network IO) and mutagen (for id3 tags). It is wise to install these two modules in a virtual environment with pip. The whole program consists off one python file. 

```
git clone https://github.com/rocus/ushare.git
cd ushare

sudo apt install python3 python3-venv python3-pip

python3 -m venv venv
source venv/bin/activate

pip install aiohttp mutagen
```


**Calling the program ushare-server**

```
python3 ushare-server.py \
    --port 49152 \
    --name Music \
    --host 192.168.1.100 \
    --root /media/music \
    --ttl  1800
    --uuid ec66a7c5-1d45-4526-a91d-d76d5112c80f \   
    --log  WARNING
    
python3 ushare-server.py --help
```

Everytime you start the program you get the given uuid so clients may cache your server data. Your server gets a random uuid if you don't use the uuid option. 


**Start as a service**

Make a systemd service file and put it in /etc/systemd/system/:

```
# /etc/systemd/system/ushare-music.service
[Unit]
Description=uShare UPnP Media Music Server
After=network-online.target local-fs.target
Wants=network-online.target

[Service]
Type=simple
User=rocus
Group=users
SyslogIdentifier=ushare-music

WorkingDirectory=/opt/ushare-server

ExecStart=/opt/ushare-server/venv/bin/python /opt/ushare-server/ushare-server.py -p 49155 -n Music -r /media/music -o 10.0.2.100 -t 64000 -d WARNING

Restart=on-failure
RestartSec=5

Environment=PYTHONUNBUFFERED=1

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then on the command line:

```
sudo systemctl daemon-reload
sudo systemctl enable ushare
sudo systemctl start  ushare
sudo systemctl status ushare
```


**Your own icon**

The icon of my ushare-server is embedded in the python program. You can modify this icon in the following way. Make a small python program:

```
import base64

with open("your_icon.png", "rb") as f:
      print(base64.b64encode(f.read()).decode())
```

The text you get can be pasted in the program near the ICON HANDLER function.


**Implementation quirks.**

I used ushare mainly for the serving of radio stations to my Philips SLA5520 upnp clients. These devices (end-of-live long ago) work good with any UPnP music (mp3) streamer but use a Philips backend database (on a Philips fileserver) for radiostations (very akward to save radiostations). Now two instances of my Ushare like implementation (on my raspberry pi 4 NAS) serve music and radio. My radio tree on my Nas is thus quickly and easily available. My sla5520 has a 4 line screen: internet radio , favorites and two lines for your own UPnP servers in my case Music and Radio. (the two instances of my ushare server). The video streaming (with the most used subtitles) are experimental and depends very much on your video renderer.

In the beginning of the development of this program there seemed something wrong with the description.xml file. The services available (3) were not correctly called and as remedy I made a routine catch_all to catch all calls to the server and direct them to the appropriate software routines. Later this problem solved itself (reason unknown) but I kept this catch_all function but it is hardly ever called. It was called once because some client called a flavico.ico although that is not the name of my icon as mentioned in the description.xml file.  

I implemented a CDS_EVENT routine complete with subscription, timeout and unsubscribe facilities. This CDS_EVENT does not do anything: most clients don't use events.

The Philips sla5520 has maybe a bug that removes servers after some time from it's screen. That does not happen on all sla5520's in my network but it happens quite often and mostly after an hour or so. The root cause may also be strange behavour of wifi routers. I found a solution for this problem in the form of a SSDP timeout constant. Normally you would set that for example to 1800 seconds but I set that to 64000 seconds (Completely legal according to UPnP rules). So the servers (in my case my ushare music and radio servers/lines) disappear after almost one day. A reboot is then necessary. It is quite common that UPnP clients find servers only during boot (and not later).
