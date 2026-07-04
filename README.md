**What is ushare?**

Ushare is a rather old UPnP server that is no longer maintained. I installed it 15 years ago on a raspberry pi and it still functions quite well, but it is no longer available on newer OS'es. It is simple directory based and has no database like functions: you can not sort or search its results but that is no problem if you have a neat directory structure for your music files.

**What advantages has Ushare over other UPnP servers?**

Apart from being simple and lightweight it has one advantage that makes this project for me worthwhile: it supports radio stations (as part of playlist files). Many UPnP servers look for mp3's in a playlist file and thus refuse to play an url radio station. Other UPnP servers can play playlist files with radio stations but can only show these playlist files in one directory or combined in one long playlist file. Another advantage of my implementation of ushare in Python is that you can modify/adapt the software to borderline complyent UPnP implementations of clients.

**How did I implement my ushare like UPnP server?**

From the beginning I choose Python as my implementation language. Originally Ushare was written in C and I tried to recompile it on a more modern environment (Debian 12). Because ushare used upnp and dlna libraries that have changed over time and because my experience with C is very limited, I choose to implement it in Python with common libraries. I did not use any code from ushare.

**Limitations.**

I made my ushare for the most common filetypes for music. It is quite easy to add other filetypes like video but I think UPnP is less suitable for video. Like I said above, there are no search and sort facilities, you must have a reasonable directory structure for your music.

**Implementation quirks.**

I used ushare mainly for the serving of radio stations to my Philips SLA5520 upnp clients. These devices (end-of-live long ago) work good with any UPnP music (mp3) streamer but use a Philips backend database (on a Philips fileserver) for radiostations (very akward to save radiostations). Now two instances of my ushare like imp-lementation (on my raspberry pi 4 NAS) serve music and radio. My radio tree on my Nas is thus quickly and easily available. My sla5520 has a 4 line screen: internet radio , favorites and two lines for your own UPnP servers in my case Music and Radio. (the two instances of my ushare server.

I use two special modules normally not standard installed: aiohttp (for asynchrone network IO) and mutagen (for id3 tags). It is wise to install these two modules in a virtual environment with pip. The whole program consists off one python file. 

With parameters on the command line you can adapt the ushare program:

python3 ushare.py -p 49153 -o 10.0.0.120 -n Music -r /media/music -d WARNING

Everytime you start the program you get a new random uuid but you can also give an uuid on the command line.

python3 ushare.py -h shows a short help.

In the beginning of the development of this program there seemed something wrong with the description.xml file. The services available (3) were not correctly called and as remedy I made a routine catch_all to catch all calls to the server and direct them to the appropriate software routines. Later this problem solved itself (the reason is unknown) but I kept this catch_all function but it is hardly ever called. Once because some client called a flavico.ico although that is not my implemented icon.  

I implemented a CDS_EVENT routine complete with subscription, timeout and unsubscribe facilities. This cds_event is not used: most clients don't use it.

The Philips sla5520 has a bug that removes servers after some time from it's screen. Strangely that does not happen on all sla5520's that I use but it happens quite often and mostly after an hour or so. I found a solution for this bug in the form of a SSDP timeout constant. Normally you would set that for example to 1800 seconds but I set that to 64000 seconds (Completely legal according to UPnP rules). So the servers (in my case my ushare music and radio servers/lines) disappear after one day. A reboot is then necessary. It is quite common that UPnP clients find servers only immediately after boot (and not later).

I gave myserver an icon in software. You can change the software for your icon. You can do that in python:

import base64
with open("icon.png", "rb") as f:
    print(base64.b64encode(f.read()).decode())

The text you get can be pasted in the program near the ICON HANDLER. Your description.xml must match the icon_handler call mechanism.
